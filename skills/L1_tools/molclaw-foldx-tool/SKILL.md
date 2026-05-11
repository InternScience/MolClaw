---
name: molclaw-foldx-tool
description: >
  FoldX protein stability and mutation analysis tool. Supports 8 modes: structure
  repair (RepairPDB), stability calculation (Stability), mutation ΔΔG (BuildModel),
  complex interface energy (AnalyseComplex), alanine scanning (AlaScan), position
  scanning (PositionScan), PSSM generation (Pssm), and per-residue energy
  decomposition (SequenceDetail). Covers fast empirical force-field evaluation
  between geometric analysis (interaction-visualizer) and full MD simulation (MMPBSA).
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L1-Tool
    methodology-ref: >
      L3 Principle 2 (Tiered Screening — FoldX as Tier 3 extension for protein
      engineering between docking/rescoring and MD/MMPBSA),
      L3 Principle 9 (Never trust single tool — cross-validate FoldX ΔΔG with
      MMPBSA or Boltz-2),
      L3 Principle 13 (Computation-first — ΔΔG values must come from FoldX tool
      calls, never from LLM training knowledge),
      L3 Principle 17 (Residue numbering — positions/mutant_file use PDB numbering,
      translate from task numbering scheme before calling)
---

# FoldX Protein Stability & Mutation Analysis

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Critical Prerequisite

> **MANDATORY: Run `mode=repairpdb` on every PDB before any other FoldX mode.**
> FoldX optimizes side-chain rotamers against its own empirical energy function;
> unrepaired structures produce unreliable energy values. This is independent of
> `molclaw-pdbfixer` — even pdbfixer-repaired structures need FoldX RepairPDB.
> The output `*_Repair.pdb` is the ONLY acceptable input for subsequent FoldX modes.

- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before FoldX RepairPDB.

## When To Use This Skill

| Scenario | Use FoldX | Use other tool instead |
|----------|:---------:|----------------------|
| Evaluate protein intrinsic stability (ΔG) | ✅ `stability` | — |
| Predict effect of known mutations (ΔΔG) | ✅ `buildmodel` | — |
| Protein–protein interface energy (fast, minutes) | ✅ `analysecomplex` | MMPBSA (precise, hours) |
| Identify interface hotspot residues | ✅ `alascan` with `chains` | MMPBSA per-residue decomposition (precise) |
| Saturating mutagenesis scan at specific sites | ✅ `positionscan` | — |
| Affinity maturation on complex interface | ✅ `pssm` | — |
| Per-residue energy decomposition | ✅ `sequencedetail` | interaction-visualizer (geometry level) |
| Small-molecule binding free energy | ❌ | Boltz-2, MMPBSA |
| MD trajectory dynamics | ❌ | GROMACS, OpenMM |
| Batch docking pose evaluation | ❌ | EquiScore, ProLIF |

## Unified Tool Interface

All 8 modes are accessed through a single tool `foldx_tool` with a `mode` parameter. The full parameter set is:

```tex
Run FoldX energy evaluation and mutation-scanning workflows for protein stability
or complex-interface screening.
Args:
    mode (str): FoldX command mode, REQUIRED. One of: repairpdb, stability,
        buildmodel, analysecomplex, alascan, positionscan, pssm, sequencedetail.
    pdb_path (str): Input PDB file path, REQUIRED for all modes.
    chains (str|None): Complex chain definition, e.g. 'A,B' or 'HL,A'.
        REQUIRED for analysecomplex and pssm.
        OPTIONAL for alascan (enables complex-mode interface scanning).
        Ignored by other modes. Default: None.
    positions (str|None): Comma-separated mutation position tokens.
        Format: OrigAA(1-letter) + ChainID + ResNum + TargetAA.
        REQUIRED for positionscan and pssm. Default: None.
    mutant_file (str|None): Path to FoldX-format mutation list file.
        REQUIRED for buildmodel. Default: None.
    number_of_runs (int): Independent repeats for buildmodel (1-100). Default: 5.
    water (str): Water handling: CRYSTAL|PREDICT|NONE|COMPARE. Default: CRYSTAL.
    pdb_hydrogens (bool): Read hydrogens from PDB. Default: False.
    dry_run (bool): Return planned command without execution. Default: False.
    timeout (int): Maximum execution time in seconds. Default: 7200.
Return:
    status (str): success | error | partial_success
    msg (str): Execution summary or error message
    mode (str): Normalized FoldX command mode
    output_dir (str|None): Run directory path
    foldx_command (str|None): Executed or planned command line
    pdb_file (str|None): Input PDB filename in output_dir
    key_files (dict): Key output files relative to output_dir
    metrics (dict): return_code, generated_file_count, and mode-specific values
        (total_energy, mean_ddg, ddg_values, interaction_energy, hotspot_count)
    stderr_tail (str, only on error): Last portion of FoldX stderr for diagnostics
```

## Parameter–Mode Matrix

| Parameter | repairpdb | stability | buildmodel | analysecomplex | alascan | positionscan | pssm | sequencedetail |
|-----------|:---------:|:---------:|:----------:|:--------------:|:-------:|:------------:|:----:|:--------------:|
| `pdb_path` | **REQUIRED** | **REQUIRED** | **REQUIRED** | **REQUIRED** | **REQUIRED** | **REQUIRED** | **REQUIRED** | **REQUIRED** |
| `chains` | — | — | — | **REQUIRED** | optional | — | **REQUIRED** | — |
| `positions` | — | — | — | — | — | **REQUIRED** | **REQUIRED** | — |
| `mutant_file` | — | — | **REQUIRED** | — | — | — | — | — |
| `number_of_runs` | — | — | used (default 5) | — | — | — | — | — |
| `water` | used | used | used | used | used | used | used | used |
| `pdb_hydrogens` | used | used | used | used | used | used | used | used |

## Mode 1: repairpdb — Structure Repair for FoldX

Optimizes side-chain rotamers and removes bad contacts against the FoldX energy function.

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "repairpdb",
    "pdb_path": prepared_pdb_path
})
result = client.parse_result(response)
repaired_pdb = result["output_dir"] + "/" + [k for k in result["key_files"] if k.endswith("_Repair.pdb")][0]
```

Key outputs: `{stem}_Repair.pdb` (repaired structure), `{stem}_Repair.fxout` (energy log).

## Mode 2: stability — Protein Free Energy (ΔG)

Computes total free energy of the protein structure. Lower (more negative) ΔG = more stable.

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "stability",
    "pdb_path": foldx_repaired_pdb_path
})
result = client.parse_result(response)
total_energy = result["metrics"]["total_energy"]  # ΔG in kcal/mol
```

Key outputs: `{stem}_0_ST.fxout`. Key metric: `metrics.total_energy`.

## Mode 3: buildmodel — Mutation ΔΔG Calculation

Models specified mutations and computes ΔΔG (free energy change upon mutation).

### Mutant file format

Each line contains one mutation or combination, terminated by semicolon. Format per mutation: `OrigAA(1-letter) + ChainID + ResidueNumber + NewAA(1-letter)`.

```
LA42G;
VA68D;
LA42G,VA68D;
```

Line 1: chain A position 42 Leu→Gly. Line 3: simultaneous double mutation.

Common format errors:
- ❌ `Leu42Gly;` — must use single-letter amino acid codes
- ❌ `L42G;` — must include chain ID between amino acid code and residue number
- ❌ `LA42G` — must end with semicolon

**Residue numbering (L3 Principle 17):** Use the PDB file's numbering, not UniProt or literature numbering. Translate before writing the mutant file.

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "buildmodel",
    "pdb_path": foldx_repaired_pdb_path,
    "mutant_file": "/path/to/mutations.txt",
    "number_of_runs": 5
})
result = client.parse_result(response)
mean_ddg = result["metrics"]["mean_ddg"]       # average ΔΔG in kcal/mol
ddg_values = result["metrics"]["ddg_values"]   # per-mutation ΔΔG list
```

Key outputs: `Dif_{stem}.fxout` (core ΔΔG), `Average_{stem}.fxout`, `Raw_{stem}.fxout`. Key metrics: `metrics.mean_ddg`, `metrics.ddg_values`.

## Mode 4: analysecomplex — Protein–Protein Interface Energy

Computes interaction energy between two sides of a protein complex.

### Determining the chains parameter

**Before calling analysecomplex, you MUST check actual chain IDs in the PDB file.** Do not assume chains are A and B. Use `calculate_pdb_basic_info` or inspect the PDB to identify chain IDs, then decide which chains form each side of the complex:
- Antibody H+L vs antigen A → `chains="HL,A"`
- Receptor A vs ligand B → `chains="A,B"`
- Trimer AB vs C → `chains="AB,C"`

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "analysecomplex",
    "pdb_path": foldx_repaired_complex_path,
    "chains": "A,B"   # MUST match actual PDB chain IDs
})
result = client.parse_result(response)
interaction_energy = result["metrics"]["interaction_energy"]  # kcal/mol
```

Key outputs: `Interaction_{stem}_AC.fxout`, `Interface_Residues_{stem}_AC.fxout`, `Summary_{stem}_AC.fxout`, `Indiv_energies_{stem}_AC.fxout`. Key metric: `metrics.interaction_energy`.

## Mode 5: alascan — Alanine Scanning

Mutates each residue to alanine and computes ΔΔG. Two sub-modes:

**Monomer mode (no chains):** Computes effect on protein folding stability only.

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "alascan",
    "pdb_path": foldx_repaired_pdb_path
})
```

**Complex mode (with chains):** Computes effect on interface interaction energy. **This is the correct mode for interface hotspot identification.**

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "alascan",
    "pdb_path": foldx_repaired_complex_path,
    "chains": "A,B"   # MUST match actual PDB chain IDs
})
result = client.parse_result(response)
hotspot_count = result["metrics"]["hotspot_count"]  # residues with ΔΔG > 1.0
```

Key output: `{stem}_AS.fxout`. Key metric: `metrics.hotspot_count`.

> **⚠ Common mistake:** Running AlaScan without `chains` on a complex PDB gives ΔΔG for monomer stability, NOT interface binding contribution. If your goal is to find interface hotspots, you MUST provide `chains`.

## Mode 6: positionscan — Saturating Mutagenesis

Scans specified positions through all 20 amino acid substitutions (or a specified target).

### Positions format

Each token: `OrigAA(1-letter) + ChainID + ResidueNumber + Target`. Use lowercase `a` to scan all 20 amino acids.

- `RA32a` → Arg at chain A position 32, scan all 20 AAs
- `KA45G` → Lys at chain A position 45, mutate only to Gly
- `RA32a,KA45a` → scan both positions

Common format errors:
- ❌ `ArgA32a` — must use single-letter AA code (R, not Arg)
- ❌ `R32a` — must include chain ID (RA32a)
- ❌ `R:A:32:a` — no separators within a token

**Residue numbering (L3 Principle 17):** positions use the PDB file's numbering. Translate from task numbering before calling.

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "positionscan",
    "pdb_path": foldx_repaired_pdb_path,
    "positions": "RA32a,KA45a"
})
result = client.parse_result(response)
```

Key output: `PS_{stem}_scanning_output.txt`.

## Mode 7: pssm — Position-Specific Scoring Matrix on Complex

Combines position scanning with complex analysis. For each position, evaluates all 20 substitutions considering BOTH protein stability AND interface binding energy. **Requires both `chains` and `positions`.**

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "pssm",
    "pdb_path": foldx_repaired_complex_path,
    "chains": "A,B",
    "positions": "RA32a,KA45a"
})
result = client.parse_result(response)
```

Key outputs: `PSSM_{stem}.txt` (scoring matrix), `PSSM_Clash_{stem}.txt` (steric clashes).

## Mode 8: sequencedetail — Per-Residue Energy Decomposition

Reports energy contribution of each residue broken down by van der Waals, hydrogen bonds, solvation, electrostatics, etc.

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "sequencedetail",
    "pdb_path": foldx_repaired_pdb_path
})
result = client.parse_result(response)
```

Key output: `SD_{stem}.fxout`.

## Typical Workflow Combinations

**Flow A — Protein stability assessment:**
`repairpdb` → `stability` (wild-type ΔG) → `buildmodel` (mutant ΔΔG)

**Flow B — Interface hotspot identification:**
`repairpdb` → `analysecomplex` (total interface energy) → `alascan` with chains (per-residue hotspots)

**Flow C — Affinity maturation:**
`repairpdb` → `analysecomplex` → `pssm` (systematic interface scanning for optimal substitutions)

**Flow D — Mutation site discovery:**
`repairpdb` → `positionscan` (saturating scan) → select ΔΔG < −0.5 → `buildmodel` (validate combinations)

## Scoring Interpretation

**ΔΔG sign convention:** Positive = destabilizing (harmful mutation). Negative = stabilizing (beneficial mutation). Unit: kcal/mol.

**Confidence thresholds:**
- |ΔΔG| < 0.5 kcal/mol → within FoldX noise range, not actionable
- ΔΔG > 1.0 kcal/mol → likely destabilizing
- ΔΔG < −0.5 kcal/mol → potentially stabilizing
- ΔΔG < −1.0 kcal/mol → significantly stabilizing (strong candidate)

**AlaScan hotspot:** ΔΔG(Ala) > 1.0 kcal/mol → interface hotspot residue.

**AnalyseComplex interaction energy:** More negative = stronger binding. Near zero or positive = no significant complex formation.

**Do NOT treat FoldX energies as exact binding free energies.** FoldX uses an empirical force field with systematic errors of ±0.5–1.0 kcal/mol. Use for ranking and trend identification, not absolute affinity prediction. For high-accuracy ΔG, use MMPBSA (Skill 6).

## Common Failures & Recovery

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| `"FoldX executable not found"` | foldx binary not in PATH | Check `foldx_bin` parameter; verify FoldX installation |
| `"chains is required for mode=analysecomplex"` | Forgot to specify chains | Check PDB chain IDs with `calculate_pdb_basic_info`, then set chains |
| `"invalid position token: 'Arg-A-32'"` | positions format incorrect | Use format `RA32a` (1-letter AA + chain + number + target) |
| `"invalid chains format: 'A B'"` | Chains not comma-separated | Use `"A,B"` not `"A B"` |
| FoldX exit code ≠ 0 + stderr "not found in PDB" | Chain ID in `chains` parameter doesn't exist in PDB | Re-check PDB chain IDs |
| FoldX timeout | Large protein + many-site scan | Reduce positions count or increase timeout |
| `partial_success` with empty key_files | FoldX ran but output filenames don't match expected patterns | Manually check output_dir contents |
| BuildModel ΔΔG all near 0 | Input structure not FoldX-repaired | Run mode=repairpdb first, then retry |
| AlaScan finds no hotspots (all ΔΔG < 1.0) | Ran without chains (monomer mode instead of complex mode) | Add `chains` parameter to enable complex-mode scanning |
| `"mutant_file is required"` | Forgot mutant_file for buildmodel | Create mutation list file in FoldX format (see Mode 3) |

## Relationship to Other Tools

- **vs `molclaw-pdbfixer` (fix_pdb):** PDBFixer does topology repair (missing atoms, non-standard residues). FoldX RepairPDB does energy-based side-chain optimization. For FoldX workflows, apply BOTH: pdbfixer first, then FoldX repairpdb.
- **vs `molclaw-protein-ligand-mmpbsa` / `molclaw-protein-protein-mmpbsa`:** MMPBSA uses MD simulation for precise ΔG (Tier 4, hours). FoldX provides fast empirical ΔG/ΔΔG (Tier 3, minutes). Use FoldX for screening/ranking, MMPBSA for final validation of top candidates.
- **vs `molclaw-interaction-visualizer`:** interaction-visualizer analyzes geometric interactions (H-bonds, hydrophobic contacts, etc.). FoldX provides energy quantification. They are complementary — use interaction-visualizer for visual/geometric analysis, FoldX for energy-based ranking.
- **vs `proteinmpnn_tool`:** ProteinMPNN designs sequences from structure (generative). FoldX evaluates mutations on existing sequences (evaluative). Use ProteinMPNN for design, FoldX BuildModel/PositionScan for evaluation and cross-validation.

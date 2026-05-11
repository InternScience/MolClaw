---
name: molclaw-binding-free-energy-calculation
description: >
  Binding free energy calculation using MD simulation and MM-PBSA/GBSA methods. Supports
  protein-ligand and protein-protein complexes. Includes trajectory analysis and per-residue
  energy decomposition.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 2 (Tier 4 validation), Principle 9 (Do not conflate physical quantities),
      L3 Principle 14 (Mandatory structure file collection — download ALL MD output files),
      L3 Principle 15 (Mandatory image file collection — download energy decomposition plots),
      L3 Principle 17 (Residue numbering reconciliation — map per-residue decomposition to task scheme)
---

# Binding Free Energy Calculation Workflow

## Applicability

**Use this skill when:** Final-stage validation of top candidates (≤ 5 molecules) is needed; comparing binding strength of different molecules or mutants; obtaining per-residue energy decomposition for optimization guidance.

**Do NOT use this skill when:** The task is early-stage screening of many molecules (use Skill 2); the molecule has not been docked yet (dock first with Skill 2); or docking itself failed for this molecule.

**This is L3 Tier 4 — the most expensive validation.** Apply only to a small number of final candidates, typically ≤ 5.

**Fast alternative for protein-protein interface energy (FoldX):** If the goal is rapid ranking of protein-protein interface binding strength (minutes vs hours for MMPBSA), consider using `foldx_tool mode=analysecomplex` as a Tier 3 pre-screening step before committing to full MMPBSA. Use FoldX AnalyseComplex to rank candidates, then apply MMPBSA only to the top 3–5. See L1 skill `molclaw-foldx-tool` for details and scoring interpretation. Note: FoldX uses an empirical force field and is NOT a substitute for MMPBSA when quantitative ΔG is required — it is a fast ranking tool.

**Alternative hotspot identification with FoldX AlaScan:** For faster hotspot residue identification without MD simulation, run `foldx_tool mode=alascan` with `chains` on the complex. Residues with ΔΔG(Ala) > 1.0 kcal/mol are interface hotspots. Cross-validate with MMPBSA per-residue decomposition when both are available.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Prepared protein PDB | Skill 1 `prepared_pdb` | Yes |
| Ligand in binding pose | Skill 2 docking output (PDBQT/SDF) | Yes (Scene A) |
| Second protein chain | Skill 1 (for the partner protein) | Yes (Scene B) |
| Numbering scheme info | Skill 1 `numbering_scheme` | Recommended (for per-residue analysis) |

**Critical:** The ligand MUST come from a docking result (already positioned in the binding pocket). Do NOT generate a 3D structure from SMILES for MM-PBSA.

## Scene Classification

**Scene A: Protein-ligand binding free energy.** Tool chain: `molclaw-protein-ligand-mmpbsa`.

**Scene B: Protein-protein binding free energy.** Tool chain: `molclaw-protein-protein-mmpbsa`.

## Core Workflow

### Step 1: Structure Repair (`fix_pdb`)

Clean the receptor. **Data handoff contract:** The `output_file` from `fix_pdb` is the ONLY acceptable input for Step 2.

**Post-repair download (L3 Principle 14):** Download the repaired PDB to local workspace.

### Step 2: Complex Preparation and MD Simulation (`prepare_complex`)

This step builds the simulation system, runs energy minimization, equilibration (NVT → NPT), and production MD.

**Recommended simulation parameters:**

| Parameter | Quick evaluation | Standard evaluation | Publication quality |
|-----------|-----------------|--------------------|--------------------| 
| Equilibration (NVT + NPT) | 100 ps each | 200 ps each | 500 ps each |
| Production MD | 1–2 ns | 5–10 ns | 20–50 ns |
| Time step | 2 fs | 2 fs | 2 fs |
| Save interval | 10 ps | 10 ps | 5 ps |
| Use case | Rapid ranking of 3–5 molecules | Standard validation | When comparing to experimental ΔG |

**Default recommendation:** Standard evaluation (5 ns production MD) unless the user specifies otherwise.

**Post-simulation check:** Verify that the `output_dir` contains the required GROMACS files: `em.gro`, `md.xtc`, `md.tpr`, `topol.top`. If any are missing, the simulation failed.

### Mandatory MD Output File Download (L3 Principle 14 — CRITICAL)

**After MD simulation completes, download ALL structure and trajectory files from `output_dir`:**

| File | Description | Category |
|------|-------------|----------|
| `em.gro` | Energy-minimized structure | **A — MUST download** |
| `md.xtc` | Production MD trajectory | **A — MUST download** |
| `md.tpr` | Run input (topology + parameters) | **A — MUST download** |
| `topol.top` | System topology | **A — MUST download** |
| `md.gro` / `md_final.gro` | Final frame structure | **A — MUST download** |
| `npt.gro` | NPT equilibrated structure | B — SHOULD download |
| `md.log` | Simulation log | B — SHOULD download |
| `md.edr` | Energy data | B — SHOULD download |

```python
# Download ALL files from MD output directory
import os, base64
for filename in os.listdir(output_dir):
    filepath = os.path.join(output_dir, filename)
    response = await client.session.call_tool(
        "server_file_to_base64",
        arguments={"file_path": filepath}
    )
    dl = client.parse_result(response)
    local_path = f"step{N}_md_{filename}"
    with open(local_path, "wb") as f:
        f.write(base64.b64decode(dl["base64_string"]))
    assert os.path.getsize(local_path) > 0, f"Download failed: {local_path}"
```

**⚠ The MD simulation step is NOT considered complete until ALL output files have been downloaded and verified.**

### Step 3: MM-PBSA/GBSA Calculation (`run_mmpbsa`)

**Method selection:**

| Method | Speed | Accuracy | When to use |
|--------|-------|----------|-------------|
| `gb` | Fast | Lower | Quick comparison of multiple molecules |
| `pb` | Slow | Higher | When accuracy matters more than speed |
| `both` | Slowest | Both available | **Recommended default** — allows cross-validation |

**When GB and PB disagree (L3 Principle 3):** Report both rankings, note the disagreement, and discuss possible causes.

### Post-MMPBSA File Download (L3 Principle 14)

Download ALL MMPBSA output files:
- Energy summary files (FINAL_RESULTS_MMPBSA.dat or equivalent)
- Per-residue decomposition files
- Any intermediate structure files generated during the calculation

### Step 4: Analysis and Visualization (`analyze_mmpbsa`, optional)

Generate visualization reports and per-residue decomposition plots.

### Post-Analysis Image Download (L3 Principle 15 — MANDATORY)

Download ALL visualization outputs:
- Per-residue energy contribution bar charts/heatmaps (PNG)
- Energy decomposition pie charts (PNG)
- RMSD/convergence plots if generated (PNG)
- Any other images in the analysis output directory

```python
# List and download all image files from analysis output
for img_file in analysis_output_images:  # PNG, SVG, PDF, TIFF, JPG
    # ... download via server_file_to_base64, save locally
```

<!-- NEW: Optional LR experimental binding energy retrieval -->
### Optional: Experimental Binding Energy Retrieval (if LR tools are available)

After MMPBSA computation, search PubMed for experimental binding affinity data to cross-validate computational predictions:

1. PubMed search: `"[target name] binding affinity Kd Ki ITC SPR"` (retmax=10)
2. If experimental Kd/Ki values are found, convert to ΔG for comparison: ΔG = RT·ln(Kd) where R = 1.987 cal/(mol·K), T = 298 K.
3. Report computational ΔG (MMPBSA) vs experimental ΔG side-by-side in `result.md`:
   - Agreement (within ~2 kcal/mol): increases confidence in computational prediction
   - Large discrepancy: may indicate force field limitations, insufficient sampling, or different experimental conditions — discuss in Limitations
4. Record: `[LR] Experimental ΔG cross-validation: [compound] Kd=[value] (PMID:[id]) → ΔG_exp=[value] vs ΔG_MMPBSA=[value]`
5. All experimental values are Category 3 (⚠️ LITERATURE VALUE) per Principle 10.

This directly supports L3 Principle 9 (cross-validation with independent evidence). **If LR tools are not available**, skip this step.

## Result Interpretation

### Per-Residue Decomposition with Numbering Mapping (L3 Principle 17)

**MAPPING GATE — Execute BEFORE interpreting per-residue energy decomposition:**

Per-residue decomposition reports residue contributions using the numbering scheme of the input PDB. If the task references specific residues in a different scheme (e.g., UniProt numbering), build the mapping table BEFORE drawing conclusions about which residues are energy hotspots.

CORRECT: "Residue 50 (GROMACS internal numbering = Leu718 UniProt = Leu694 PDB 1M17) contributes −2.3 kcal/mol to binding."
WRONG: "Leu50 contributes −2.3 kcal/mol" (ambiguous — which Leu50?).

**Hotspot residue cross-validation:** Residues with |contribution| > 1.0 kcal/mol are "hotspot residues." Cross-validate against interaction-visualizer data (or ProLIF fingerprints) from Skill 2/8 — hotspot residues should correspond to residues forming strong interactions in `top_residues` from `summary_*.json`. **Use the same numbering mapping (--resid_offset) for both analyses.**

**Total binding free energy (ΔG_bind, kcal/mol):** More negative = stronger binding.

**Energy decomposition:**
- ΔE_vdw (van der Waals): dominant for hydrophobic binding
- ΔE_elec (electrostatic): dominant for charged/polar interactions
- ΔG_polar (polar solvation): desolvation penalty, usually positive
- ΔG_nonpolar (nonpolar solvation): burial of hydrophobic surface, usually negative

**Plausibility ranges (Checkpoint A):**
- Protein-ligand ΔG: typically −5 to −30 kcal/mol. Values outside this range warrant scrutiny.
- Protein-protein ΔG: typically −10 to −60 kcal/mol.
- Positive ΔG: ligand may have left the binding pocket during MD — diagnose.

**Critical warnings (L3 Principle 9):**
- MM-PBSA absolute ΔG values have systematic bias. **Relative ranking** is far more reliable than absolute values.
- **NEVER** use MM-PBSA ΔG to calculate Kd via ΔG = RT·ln(Kd).
- If computed values deviate from known experimental data by more than one order of magnitude, explicitly state this discrepancy.

## Iteration Protocol

If MM-PBSA results contradict docking-based rankings:

1. **Diagnose:** Check if the docking pose was stable during MD. Check if the MD simulation equilibrated (RMSD trajectory stable?).
2. **Re-run if needed:** If the ligand left the pocket, re-dock with tighter constraints or try DiffDock, then re-run MM-PBSA.
3. **Accept disagreement:** If re-running confirms the result, report the disagreement. This is valuable information.

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| `prepare_complex` fails at topology generation | Ligand parameterization error | Check if ligand SMILES is valid; try re-converting the ligand format |
| MD simulation crashes mid-run | System instability; bad initial geometry | Re-run energy minimization with more steps; increase equilibration time |
| ΔG is positive (repulsive) | Ligand not in a favorable pose | Re-examine the docking pose; try alternative from DiffDock |
| GB and PB give opposite rankings | Strong electrostatic effects | Report both; favor PB for charged systems; note uncertainty |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after Step 2 (MD simulation):**
- [ ] All MD output files (em.gro, md.xtc, md.tpr, topol.top) downloaded and verified non-empty
- [ ] Final frame structure downloaded

**CHECKPOINT after Step 3 (MMPBSA):**
- [ ] ΔG values are within plausible ranges
- [ ] Energy decomposition files downloaded
- [ ] If task references specific residues, numbering mapping table built

**CHECKPOINT after Step 4 (analysis):**
- [ ] All visualization images downloaded
- [ ] Per-residue hotspot residues mapped to task reference numbering scheme
- [ ] GB and PB rankings compared (if `both` was used)
- [ ] No ΔG-to-Kd conversion attempted
- [ ] Structure source (experimental vs. predicted) noted in report

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| ΔG values (GB and/or PB) | Per-molecule: ΔG_total, components | Report | **A — MUST download** |
| Per-residue decomposition | CSV: residue_id, contribution, mapped_uniprot_id | Skill 5 | **A — MUST download** |
| Ranking table | CSV: SMILES, ΔG_GB, ΔG_PB, docking_score, consensus_rank | Report | **A — MUST download** |
| MD trajectory files | XTC/GRO/TPR in output_dir | Archive | **A — MUST download** |
| Energy decomposition plots | PNG | Report | **A — MUST download** |
| Residue mapping table | CSV (if built) | Report | **A — MUST download** |

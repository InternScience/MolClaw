---
name: molclaw-molecular-docking-screening
description: >
  Molecular docking virtual screening workflow: from protein preparation and pocket detection
  through docking execution, rescoring, and interaction analysis. Supports libraries of any size
  with automatic tiered strategy selection.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 2 (Tiered screening — verify counts at every tier boundary),
      L3 Principle 3 (More than one method),
      L3 Principle 9 (Never trust single output),
      L3 Principles 4-5 (Iteration),
      L3 Principle 11 (Count-Before-Report — verify every number against source files),
      L3 Principle 14 (Mandatory structure file collection — download all docking poses),
      L3 Principle 15 (Mandatory image file collection — download interaction analysis images),
      L3 Principle 17 (Residue numbering reconciliation — use --resid_offset for interaction-visualizer),
      L3 Principle 18 (Docking parameter safeguards — minimum 25 Å box, progressive enlargement)
---

# Molecular Docking Virtual Screening Workflow

## Applicability

**Use this skill when:** The user provides a target protein (any form) and small molecules (SMILES/names/files), and requests molecular docking, virtual screening, binding assessment, or ranking molecules by predicted binding affinity.

**Do NOT use this skill when:** The user only needs property filtering without docking (use Skill 3); the task is peptide-protein or protein-protein docking (use Skill 9 or Skill 11); or the user already has docking results and only wants post-hoc evaluation (use Skill 8).

**Boundary with Skill 8:** This skill handles the full pipeline from raw inputs to ranked results. If you already have docking output files (PDBQT poses, SDF complexes) and need only rescoring/consensus/SAR analysis, use Skill 8 instead.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Prepared protein PDB | Skill 1 `prepared_pdb` | Yes |
| Quality summary | Skill 1 `quality_summary` | Recommended (for reporting) |
| Numbering scheme info | Skill 1 `numbering_scheme` | Recommended (for residue-specific analysis) |
| Molecule SMILES list | User input or upstream generation | Yes |

## Phase 1: Scale Assessment and Strategy Selection

**This is the most critical decision point.** Before any computation, count the molecules and select the screening strategy using the following decision tree:

| Library size | Strategy | Tiers | Rationale |
|-------------|----------|-------|-----------|
| **≤ 10 molecules** | Full evaluation | Direct docking + EquiScore + interaction analysis for all | Small enough for exhaustive analysis |
| **11–100 molecules** | Two-tier screening | Tier 1: property pre-filter → Tier 2: dock survivors | Balance efficiency and coverage |
| **101–500 molecules** | Three-tier screening | Tier 1: property filter → Tier 2: docking → Tier 3: EquiScore + interaction analysis for Top 15–20 | Standard virtual screening |
| **501–2000 molecules** | Four-tier screening | Tier 1: strict property filter → Tier 2: Boltz-2 rapid binding probability → Tier 3: dock Top 100 → Tier 4: EquiScore + interaction analysis for Top 15 | Large-scale campaign |
| **> 2000 molecules** | Recommend KarmaDock or stricter pre-filter | Advise user to use KarmaDock for initial screening or provide stricter filtering criteria to reduce the library | QuickVina's per-molecule MCP calls would be too slow |

Record the chosen strategy and rationale in `run_log.md`.

## Phase 2: Small Molecule Acquisition and Preparation

**Step 1 — Obtain SMILES.** Compound names → `retrieve_smiles_by_compoundname`; direct SMILES → use directly; mixed input → validate with `is_valid_smiles` to classify.

**Step 2 — Validate.** Call `is_valid_smiles` for every molecule. Remove invalid entries; record them in the screening funnel log.

**⚠ COUNT GATE (L3 Principle 11 — MANDATORY):** After validation, programmatically count valid molecules:
```python
# Example: count valid SMILES in the list
valid_count = sum(1 for s in smiles_list if is_valid)
```
Record: "Input: X molecules → Valid: Y molecules → Invalid: Z molecules (reasons: ...)". The count Y must come from the actual validation results, not from memory or expectation.

**Step 3 — Property pre-filter (if strategy requires it).** Call `calculate_mol_drug_chemistry` for QED and Lipinski violations. Apply the following default thresholds (adjust if user specifies otherwise):

| Criterion | Default threshold | When to relax |
|-----------|------------------|---------------|
| Lipinski violations | ≤ 2 | Natural products, PROTACs, macrocycles: skip this filter |
| QED | ≥ 0.2 | Fragment screening: lower to 0.1 |
| MW | 150–900 Da | Peptide-like molecules: raise upper bound |

**⚠ COUNT GATE after filtering:** Programmatically count how many molecules passed. Record: "Pre-filter input: Y molecules → Passed: P molecules → Eliminated: Y-P molecules (Lipinski>2: A; QED<0.2: B; MW out of range: C)".

**Step 4 — Format conversion.** Call `convert_smiles_to_format` (SMILES → PDBQT for QuickVina). Record conversion failures.

**⚠ COUNT GATE after conversion:** Count successful conversions. Record: "Conversion input: P molecules → Successful: Q molecules → Failed: P-Q molecules".

## Phase 3: Pocket Detection

**Decision: Is detection needed?**
- User provided pocket center coordinates → use directly.
- User specified active site residues → still run detection, select the pocket closest to the specified residues.
- **Co-crystal ligand available in the PDB** → extract ligand centroid as box center (see below).
- No pocket information → detection is mandatory.

### Co-Crystal Ligand Centroid Extraction (when applicable)

**When the original PDB contains a co-crystal ligand** (e.g., AQ4 in 1M17, ligand residue name visible in HETATM records) **and the task specifies using the native ligand position as the docking box center**, extract the ligand centroid **BEFORE running fix_pdb** (which removes heterogens and would delete the ligand):

```python
# Step 1: Parse HETATM records for the co-crystal ligand BEFORE fix_pdb
import re
ligand_coords = []
with open("raw_protein.pdb") as f:
    for line in f:
        if line.startswith("HETATM"):
            resname = line[17:20].strip()
            element = line[76:78].strip() if len(line) > 76 else ""
            if resname == "AQ4" and element != "H":  # Replace AQ4 with actual ligand name
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                ligand_coords.append((x, y, z))

# Step 2: Compute centroid
center_x = sum(c[0] for c in ligand_coords) / len(ligand_coords)
center_y = sum(c[1] for c in ligand_coords) / len(ligand_coords)
center_z = sum(c[2] for c in ligand_coords) / len(ligand_coords)

# Step 3: Record these BEFORE fix_pdb removes the ligand
# These become the locked docking box center for all subsequent rounds
```

**⚠ Order of operations is critical:** Extract ligand centroid → THEN run fix_pdb (remove heterogens) → THEN proceed with docking. If fix_pdb is run first, the ligand coordinates are lost.

### Docking Parameter Locking (for iterative tasks)

**When the task involves iterative docking across multiple rounds with consistent parameters:**
After the baseline docking, record the EXACT parameters used in `run_log.md`:

```
## Locked Docking Parameters
- center_x: [value]
- center_y: [value]
- center_z: [value]
- size_x: [value]
- size_y: [value]
- size_z: [value]
- Established in: Step (a) baseline docking
- Rule: Use these EXACT parameters in ALL subsequent rounds. Do NOT re-detect pocket.
```

In all subsequent rounds, retrieve and reuse these locked parameters. **Do NOT re-run pocket detection** — the pocket does not change between rounds; only the ligand changes.

**Dual-tool detection (L3 Principle 3, when no co-crystal ligand is available).** Run both `fpocket_toolkit` and `pred_pocket_prank` on `prepared_pdb`.

**Consensus logic:**

| Condition | Action |
|-----------|--------|
| Top-1 pockets within 5 Å of each other | High confidence. Use fpocket coordinates. |
| 5–10 Å apart | Moderate confidence. Use the midpoint. |
| ≥ 10 Å apart | **Divergence.** Report both pockets. Use the one with the higher druggability score by default, but note the alternative in the report. |

### Docking Box Size (L3 Principle 18 — HARD CONSTRAINT)

**Minimum docking box size: 25.0 Å per dimension.** This is a non-negotiable floor.

| Scenario | Box size rule |
|----------|--------------|
| Pocket detection returns dimensions ≥ 25 Å | Use detected dimensions |
| Pocket detection returns any dimension < 25 Å | **Override to 25.0 Å** on that dimension |
| Large molecules (MW > 600) or shallow pockets | Increase to 30–35 Å |
| User specifies custom box size < 25 Å | **Override to 25.0 Å** and note in log |

**⚠ NEVER set size_x, size_y, or size_z below 25.0 Å.** A box that is too small will miss valid binding poses, clip the ligand search space, or cause the docking engine to return errors/positive scores.

**Pocket center sanity check:** If pocket center coordinates are (0, 0, 0) or appear to be default/unset values, suspect pocket detection failure — rerun detection or use the co-crystal ligand centroid as the pocket center.

## Phase 4: Receptor Format Conversion

Call `convert_pdb_to_pdbqt_dock` on `prepared_pdb`. If it fails, re-run `fix_pdb` with `replace_nonstandard=True` and retry once.

### Post-Conversion Download (L3 Principle 14)

Download the receptor PDBQT file to local workspace. This is a Category B file (diagnostic/reproducibility value).

<!-- NEW: Optional LR known binder retrieval -->
### Optional: Known Binder Retrieval (if LR tools are available)

Before docking execution, search for experimentally validated binders of the target to use as positive controls:

1. PubMed search: `"[target name] inhibitor IC50"` or `"[target name] crystal structure ligand"` (retmax=10)
2. If known binders are found with published binding data:
   - Retrieve their SMILES via `compound_retrieve` (by compound name) and include them in the docking run alongside the task's candidate molecules.
   - Their docking scores serve as **internal validation benchmarks** — if a known nanomolar binder docks with a poor score (positive or near zero), the docking setup (box position, receptor conformation) may need troubleshooting.
   - Record in `run_log.md`: `[LR] Known binder controls: [compound names with PMID]. Purpose: docking validation (Principle 9).`
3. This directly supports L3 Principle 9 (cross-validation) and Principle 13 Level 4 (proper literature citation).

**If LR tools are not available**, skip this step. Proceed to Phase 5.

## Phase 5: Docking Execution

**Primary method — QuickVina2.** For each ligand, call `molecule_docking_quickvina_fullprocess`. Collect `docking_affinity_value` (kcal/mol, more negative = better) and `docking_file`.

### Checkpoint A — Immediate Sanity Check After Each Docking (L3 Principle 12)

After EACH individual docking call, verify:

| Check | Condition | Action on failure |
|-------|-----------|-------------------|
| Score sign | `docking_affinity_value` < 0 | If positive → **docking failure**. Do NOT silently accept. Execute progressive box enlargement (see below). |
| Score magnitude | `docking_affinity_value` > −15.0 for standard drug-like molecules | Flag as "anomalous — possible oversized ligand or box error" |
| Output file | `docking_file` exists and is non-empty | If missing → docking crashed, retry with larger box |

### Progressive Box Enlargement on Failure (L3 Principle 18)

If any docking returns an error, a positive score, or no valid pose:

| Retry # | Box size (each dimension) | Action |
|---------|--------------------------|--------|
| 0 (initial) | max(25, detected_size) | Standard attempt |
| 1 | 30 Å | If initial fails |
| 2 | 40 Å | If retry 1 fails |
| 3 | 50 Å | If retry 2 fails |
| 4 (fallback) | — | Switch to DiffDock or KarmaDock |

Log every retry attempt and its outcome in `run_log.md`. If ALL molecules in a batch fail docking, the problem is likely in receptor preparation — check receptor format and box definition.

### Mandatory Pose Download (L3 Principle 14 — CRITICAL)

**After EACH successful docking, download the docking pose file:**

```python
# Download docking pose PDBQT for each molecule
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": result["docking_file"]}
)
dl = client.parse_result(response)
local_path = f"step{N}_mol{i:02d}_docking_pose.pdbqt"
with open(local_path, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))
# Verify: os.path.getsize(local_path) > 0
```

**A docking step is NOT considered complete until the pose file has been downloaded and verified.** These pose files are Category A (user-critical) outputs — they are essential for downstream analysis, user verification, and visualization.

**Supplementary methods (when to use):**
- **DiffDock:** Use when the pocket is uncertain (blind docking needed), or for Top 5 validation. **WARNING: DiffDock's confidence score is valid ONLY for comparing poses of the SAME molecule. NEVER use it to rank different molecules against each other.**
- **Boltz-2 rapid screen:** Use when a fast "can it bind?" filter is needed before expensive docking (Tier 2 in the four-tier strategy). Returns binding probability and predicted log₁₀(IC₅₀). **Download the complex CIF file** from Boltz-2 output (`complex_cif_file` field).

## Phase 6: Result Ranking and Evaluation

### COUNT GATE Before Ranking (L3 Principle 11 — MANDATORY)

Before constructing any ranking table, programmatically count:
- Total molecules that entered docking: `count_entered`
- Molecules that docked successfully (negative score): `count_success`
- Molecules that failed docking (positive/missing score): `count_failed`

```python
# Verify counts match actual data files
import json
scores = json.load(open("docking_results.json"))  # or however stored
count_success = sum(1 for s in scores.values() if s < 0)
count_failed = len(scores) - count_success
```

Record verified counts in `run_log.md`: "Docking: Q molecules attempted → S docked successfully → F failed (reasons: ...)".

**⚠ The ranking table must contain exactly `count_success` entries. If you find yourself writing a different number, STOP and re-verify.**

**Basic ranking:** Sort by affinity ascending (more negative = better).

**EquiScore rescoring (for Top candidates, up to 20 molecules).** Call `equiscore_pocket` → `equiscore_screen`. EquiScore scores are higher = better (opposite to Vina). Use rank fusion, not raw score addition.

**Post-EquiScore download:** Download any SDF files generated during EquiScore pocket extraction (`single_sdf_dir`). These are Category A files needed for interaction analysis.

**Interaction analysis (for final candidates, up to 10 molecules).** Run `molclaw-interaction-visualizer` on each top candidate's docking pose. For batch fingerprint comparison across all candidates simultaneously, optionally supplement with `prolif_docking`.

```bash
# Per-candidate deep analysis (PRIMARY — run for each top candidate)
python molclaw_interaction_visualizer.py \
    --receptor prepared.pdb --ligand candidate_pose.sdf \
    --mode ligand --out_dir viz_candidate_N \
    --resid_offset <offset> --score <vina_score> \
    --residue_roles_json roles.json --title "Target–Candidate_N"
```

Identify anchor interactions (from `summary_*.json` → `top_residues`) and modification candidates (from `*_partner_site.csv`).

### Residue Numbering (L3 Principle 17 — MANDATORY when task references specific residues)

**For interaction-visualizer:** Use `--resid_offset N` (N = UniProt − PDB). All CSV outputs automatically include `rec_resid_mapped` column.

**MAPPING GATE — Execute BEFORE interpreting results if the task references specific residues:**

1. Retrieve the numbering scheme info from Skill 1 output.
2. Compute the offset: `offset = UniProt_number − PDB_number`. Use `residue_mapper.py` if needed.
3. When reporting results, ALWAYS specify the numbering scheme:
   - CORRECT: "Interaction visualizer detected HBond at ALA145 (rec_resid_pdb=145, rec_resid_mapped=719 with offset +574 = Ala719 PDB 1M17 = Ala743 UniProt P00533)"
   - WRONG: "Interaction visualizer detected HBond at ALA145" (ambiguous — which numbering?)
4. When verifying task-specified residues (e.g., "confirm Met793 interaction"), check the `rec_resid_mapped` column directly.

### Post-Analysis Image Download (L3 Principle 15 — MANDATORY)

Download ALL interaction-visualizer output images for each candidate:
- `diagram2d_*.png` — Schrödinger-style 2D interaction diagram
- `residue_bar_*.png` — residue stacked bar chart
- `pymol_*_{front,side,top}.png` — 3D renderings (if PyMOL available)
- `summary_*.json` — decision-ready JSON

### Screening Funnel Summary (MANDATORY — all counts file-verified)

| Tier | Input count (verified) | Output count (verified) | Eliminated | Elimination reasons | Verified by |
|------|----------------------|------------------------|------------|--------------------|----|
| Validation | N₀ | N₁ | N₀−N₁ | invalid SMILES: Z | `is_valid_smiles` count |
| Property filter | N₁ | N₂ | N₁−N₂ | Lipinski>2: X; QED<0.2: Y | `wc -l filtered_list` |
| Format conversion | N₂ | N₃ | N₂−N₃ | Conversion failure: W | Count successful conversions |
| Docking | N₃ | N₄ | N₃−N₄ | Docking failure: X; score > 0: Y | Count negative scores in output |
| EquiScore | N₄ | N₅ | N₄−N₅ | Low EquiScore (<0.4): X | Count filtered EquiScore results |

**Every count in this table must be programmatically verified against actual files, not recalled from memory (L3 Principle 11).**

## Phase 7: Iteration Protocol (L3 Principles 4–5)

If the first round of screening yields no satisfactory candidates (e.g., all docking scores above −6.0 kcal/mol, or no candidates pass both Vina and EquiScore thresholds), do NOT simply report failure. Execute the following diagnostic-and-retry loop:

**Before each retry round, explicitly answer three questions (L3 Principle 5):**

1. **What went wrong?** Diagnose using data: Was the pocket wrong (check if known actives for this target also score poorly)? Is the library chemically mismatched for this target (e.g., all hydrophilic molecules for a hydrophobic pocket)? Were filtering thresholds too strict? Was the docking box too small (check if progressive enlargement was tried)?

2. **What will change this round?** Specify the concrete modification: Try alternative pocket (if dual detection found two); relax property filters and re-run; generate new molecules with REINVENT (invoke Skill 4) targeting the identified pocket properties; **increase docking box size if not already at 50 Å**; switch docking method to DiffDock/KarmaDock.

3. **How will success be measured?** Define the criterion: at least 3 molecules with Vina < −7.0 kcal/mol; or at least 1 molecule with EquiScore > 0.6.

**Maximum retry rounds:** 2 additional rounds beyond the initial screen. If still unsatisfactory after 3 total rounds, report the best available results with honest analysis of why screening was challenging.

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| All docking scores positive | Wrong pocket; receptor PDBQT corrupt; box too small | Re-detect pocket; re-convert receptor; **try progressive box enlargement 25→30→40→50 Å** |
| `convert_smiles_to_format` fails for many molecules | Complex stereochemistry or charged species | Try alternative representation; generate 3D with RDKit first |
| EquiScore and Vina rankings completely disagree | Different binding modes scored; possible incorrect pose | Re-dock top EquiScore hits; inspect poses visually via interaction-visualizer 2D diagram |
| Multiple molecules return identical scores (e.g., all 0.0) | Systematic setup error | Check receptor format, box definition, and ligand preparation |
| Interaction residue IDs don't match task-specified residues | Numbering scheme mismatch (`--resid_offset` wrong or not set) | Recompute offset; check `rec_resid_mapped` column; **execute residue mapping protocol (L3 Principle 17)** before concluding interaction is absent |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after Phase 2 (molecule preparation):**
- [ ] All molecule counts are file-verified (input → valid → filtered → converted)
- [ ] Screening funnel started with verified numbers

**CHECKPOINT after Phase 3 (pocket detection):**
- [ ] Box dimensions are all ≥ 25.0 Å
- [ ] Pocket center is not (0,0,0) or default values

**CHECKPOINT after Phase 5 (docking — per molecule):**
- [ ] Docking score is negative (positive = failure → retry with larger box)
- [ ] Docking pose file downloaded and verified non-empty
- [ ] If score < −15.0, flagged as anomalous

**CHECKPOINT after Phase 6 (ranking):**
- [ ] Success/failure counts match actual data
- [ ] EquiScore and Vina agree on at least 60% of Top 10 molecules
- [ ] Interaction-visualizer shows Top candidates forming reasonable interactions with pocket residues
- [ ] `rec_resid_mapped` verified against task reference scheme (if task specifies residues)
- [ ] All interaction analysis images downloaded (interaction-visualizer PNGs; ProLIF heatmaps if batch run)
- [ ] Screening funnel has complete tier-by-tier verified statistics
- [ ] Structure source annotation from Skill 1 is included in the report

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Ranked molecule list | CSV: SMILES, Vina score, EquiScore, rank | Skills 5, 6, 8 | **A — MUST download** |
| Top docking poses | PDBQT files per molecule | Skills 6, 8 | **A — MUST download** |
| Pocket coordinates | (x, y, z, box_size) | Skills 8, 11 | B — record in log |
| Screening funnel stats | Markdown table (verified counts) | Report | B — record in log |
| Interaction-visualizer CSV + JSON | Per-molecule interaction data, summary JSON | Skills 5, 8 | **A — MUST download** |
| Interaction-visualizer images | PNG (diagram2d, residue_bar, pymol) per candidate | Report | **A — MUST download** |
| ProLIF interaction data (if batch run) | Per-molecule fingerprint CSV | Skills 5, 8 | **A — MUST download** (if used) |
| Residue mapping table | CSV (if built) | Skills 8, 11 | **A — MUST download** |

### Post-Execution Learning Check

After completing the screening workflow, if the agent encountered any of the following, evaluate crystallization triggers per L3 Principle 25.5:
- A novel tool composition not standard in this workflow (e.g., combining conformational ensemble with per-conformation docking)
- A failure-recovery pattern not in the failure table above
- A parameter configuration that significantly improved hit rates over default settings

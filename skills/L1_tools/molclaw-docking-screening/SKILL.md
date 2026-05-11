---
name: molclaw-docking-screening
description: High-level large-scale virtual screening workflow (10+ ligands) combining property filtering, QuickVina docking, EquiScore rescoring, and consensus ranking for target prioritization.
license: MIT license
metadata:
    skill-author: PJLab
---

# Large-Scale Docking Screening Skill

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Name
molclaw-docking-screening

## Description
This skill performs autonomous, large-scale virtual screening for a protein target using a soft pipeline:
1. Drug-likeness filtering (QED and Lipinski)
2. QuickVina2
3. EquiScore
4. Consensus ranking via rank aggregation

It is designed for 10+ molecules and should adapt strategy to input size, target quality, and tool outcomes.

Use this skill when:
- The task is virtual screening for 10+ ligands.
- The user asks for ranking, prioritization, or top-hit selection.
- You need balanced use of physics-based docking and ML rescoring.

## Workflow Steps

### Stage 0. Input Validation and Setup
- Validate SMILES list is non-empty and count >= 10 for this skill. If <10, still run but skip aggressive prefiltering.
- Determine run mode from task objective:
  - complete-ranking mode: user asks for all molecules ranked (common in MolBench-vs).
  - top-n mode: user asks for best N only.
- Resolve target structure:
  - If receptor_pdb_path exists, use it.
  - Else resolve target_chembl_id/uniprot_id and retrieve PDB.
- Optional chain extraction if chain is specified.
- Repair receptor with `molclaw-pdbfixer` (add hydrogens, remove waters/heterogens, normalize structure).
- Record all chosen settings in an execution summary for reproducibility.

### Stage 1. Property Filtering (Adaptive)
- Compute QED and Lipinski violations for all candidates.
- Default filter: QED >= 0.2 and Lipinski violations <= 2.
- Soft adaptation by library size:
  - 10-50 molecules: keep default thresholds.
  - 51-200 molecules: consider stricter QED (e.g., 0.25-0.30) only if enough survivors remain.
  - >200 molecules: apply stronger triage and keep a broad but manageable subset for docking.
  - If survivors < max(top_n, 5), relax thresholds once and continue.

### Stage 2. Pocket Identification
- If pocket_mode="provided", use given center and box.
- If pocket_mode="auto", predict pockets (P2Rank/fpocket) and choose the best-confidence pocket.
- Record selected pocket metadata (center, confidence, box dimensions).

### Stage 3. QuickVina Docking
- Use skill `molclaw-quickvina-docking` workflow directly to obtain QuickVina ranking for the current candidate set.
- Do not re-implement its internal conversion/docking steps in this skill.
- Keep molecule ID/SMILES mapping for downstream consensus.
- Ensure the QuickVina workflow outputs a docked SDF file (or list of per-molecule SDF/PDBQT converted to SDF) that preserves receptor-relative 3D coordinates, so it can be directly passed to molclaw-equiscore-docking as docking_result_sdf_path.

### Stage 4. EquiScore Rescoring
- Use skill `molclaw-equiscore-docking` workflow directly to obtain EquiScore ranking for the same candidate set.
- Do not re-implement its internal docking-input construction or conversion details in this skill.
- Prefer full-set rescoring in complete-ranking mode; keep output aligned by molecule ID/SMILES.
- If EquiScore tool returns `prediction_count > 0` (and/or summary stats like max/min/mean/median), treat rescoring as successful; if `predictions_path` is not directly readable, fetch it via `molclaw-file-transfer` (`server_file_to_base64`) and continue.

### Stage 5. Consensus Ranking
Do not directly add raw QuickVina and EquiScore scores.

1. Rank all successfully docked molecules by Vina affinity ascending (more negative is better): rank_vina.
2. Rank all available EquiScore predictions descending (larger is better): rank_equiscore.
3. For molecules with missing EquiScore, assign worst EquiScore rank plus penalty.
4. Compute fused rank sum:
  - fused_rank = w1 * rank_vina + w2 * rank_equiscore
5. Sort fused_rank ascending (smaller is better).

Recommended default weights:
- w1 = 1.0
- w2 = 1.0


## Notes 
- Follow question-specific output requirements first.
- Keep score direction consistent: QuickVina lower is better, EquiScore higher is better.
- Use rank aggregation or z-score fusion; avoid directly summing raw scores.
- Some of steps depend on other skills, Please refer carefully.
- Save all intermediate scripts, and save the results (the complete Claude Code reasoning process and output for this question) as result.md.

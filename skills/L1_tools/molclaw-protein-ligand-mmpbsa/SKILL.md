---
name: molclaw-protein-ligand-mmpbsa
description: Execution-ready protein-ligand MM/GB(PB)SA workflow with explicit MCP handoffs and optional analysis.
license: MIT license
metadata:
    skill-author: PJLab
---
 
# Protein-Ligand MM/PBSA Workflow (Execution-Ready)
 
## Canonical Toolchain
1. `fix_pdb` → cleans the receptor and returns `output_file`.
2. `prepare_complex` → consumes the repaired protein plus ligand to build the MD workspace and writes `output_dir`.
3. `run_mmpbsa` → consumes `work_dir` to execute GB/PB calculations and emits CSV summaries.
4. `analyze_mmpbsa` (optional) → consumes `run_mmpbsa.output_dir` to derive plots/reports from the MM/PBSA results.
 
## MCP Tool Names (must use)
- `fix_pdb`
- `prepare_complex`
- `run_mmpbsa`
- `analyze_mmpbsa`
 
## Tool References
- `fix_pdb`: [reference_fix_pdb.md](reference_fix_pdb.md)
- `prepare_complex`: [reference_prepare_complex.md](reference_prepare_complex.md)
- `run_mmpbsa`: [reference_run_mmpbsa.md](reference_run_mmpbsa.md)
- `analyze_mmpbsa`: [reference_analyze_mmpbsa.md](reference_analyze_mmpbsa.md)
 
## Data Handover Contract
1. `fix_pdb.output_file` → `prepare_complex.protein` (never substitute with manual paths).
2. `prepare_complex.output_dir` → `run_mmpbsa.work_dir` (required to contain em.gro, md.xtc, md.tpr, topol.top, ligand files).
3. `run_mmpbsa.output_dir` → `analyze_mmpbsa.work_dir` when analysis is enabled.
 
## Step Details
### Step 1: `fix_pdb`
- **Pre-flight checks**: ensure `input_path` exists and is a readable PDB; `dry_run` defaults to `False` so the file is written unless explicitly skipping.
- **Inputs**: `input_path`, `add_hydrogens`, `remove_water`, `replace_nonstandard`, `add_missing_residues`, `dry_run`.
- **Optional stage**: set `keep_chains` to restrict the repair when a subset of chains is needed.
- **Success criteria**: `status == "success"`, `output_file` is populated, atom/residue counts report >0.
- **Fallback hints**: replay the `msg`, mention which residue/chain failed, or rerun with `dry_run=True` to diagnose before writing.
 
### Step 2: `prepare_complex`
- **Pre-flight checks**: confirm `protein` equals `fix_pdb.output_file`, `ligand` path exists, and any `pose` index is valid within the ligand file.
- **Inputs**: `protein`, `ligand`, `pose`, `gpu_ids`, `full_md`, `nvt_time`, `npt_time`, `md_time`, `ph`.
- **Optional stage**: short circuits such as `full_md=False` for quick workspace generation, but then downstream steps must adjust expectations.
- **Success criteria**: `status == "success"`, `output_dir` is non-empty, `files` contains `em.gro`/`md.xtc`/`topol.top`.
- **Fallback hints**: if GPU resources are oversubscribed, rerun with `gpu_ids` trimmed or `full_md=False`; if ligand conversion fails, switch to `.mol2` or `.pdb` input.
 
### Step 3: `run_mmpbsa`
- **Pre-flight checks**: `work_dir` exists and matches `prepare_complex.output_dir`; verify expected `em.gro`, `md.xtc`, and `topol.top` exist before invoking.
- **Inputs**: `work_dir`, `method` (gb/pb/both), `nproc`, `interval`, `startframe`, `endframe`, `generate_input`, `dry_run`.
- **Optional stage**: `method` controls whether GB, PB, or both runs execute; `dry_run=True` tests configuration without executing heavy compute.
- **Success criteria**: `status == "success"`, `gb_dir` or `pb_dir` is created, `results` dictionary contains energy estimates, required CSVs (`FINAL_RESULTS.csv`) exist.
- **Fallback hints**: on missing CSVs, check `nproc` limits or re-run with `generate_input=True`; if `dry_run` was left `True`, rerun with the actual run.
 
### Step 4: `analyze_mmpbsa` (optional)
- **Pre-flight checks**: `enable_analysis` flag `True` and `work_dir` equals `run_mmpbsa.output_dir`; confirm the CSV outputs are present.
- **Inputs**: `work_dir`.
- **Optional stage**: no extra per-file overrides are required in normal workflow usage.
- **Success criteria**: `status == "success"`, `output_dir` exists, `reports` dictionary lists generated PNG/CSV/MD artifacts.
- **Fallback hints**: treat analyzer failures as soft; log the `msg` and keep the `run_mmpbsa` results as the primary output.
 
## Agent Flow
1. **Protein repair → complex build**: `fix_pdb.output_file` feeds `prepare_complex.protein`, guaranteeing the complex uses the cleaned receptor.
2. **Workspace build → free-energy run**: `prepare_complex.output_dir` becomes `run_mmpbsa.work_dir`, producing both `mmgbsa/FINAL_RESULTS.csv` and `mmpbsa/FINAL_RESULTS.csv` depending on `method`.
3. **Optional analysis**: when enabled, the analyzer consumes `run_mmpbsa.output_dir` (`work_dir`) to assemble summary plots, which are then surfaced through `analyze_mmpbsa.output_dir` and `reports`.
4. **Normalized insights**: every branch funnels into the same `work_dir` CSV artifacts so downstream agents can compare GB, PB, and analyzer outputs uniformly.
 
## Normalized Outputs (per workflow)
- `fix_pdb`: `output_file` (cleaned receptor).
- `prepare_complex`: `output_dir`/`files` (workspace containing GROMACS artifacts).
- `run_mmpbsa`: `work_dir`, `gb_dir`, `pb_dir`, `results`, `command`.
- `analyze_mmpbsa`: `output_dir`, `reports`, `detected_mode`, `missing_files` (optional insights).
 
## Safety Checklist
- Never pass manual MD files instead of `prepare_complex.output_dir`.
- Treat any missing `output_file`/`output_dir` as a hard failure and stop before the next tool.
- Validate GPU/CPU resources before running long `run_mmpbsa` jobs (`nproc`, `gpu_ids`).
- If `method="both"`, ensure both PB and GB CSVs are created; otherwise, rerun with `method="pb"` or `"gb"` only.
- Surface actionable diagnostics (`missing file`, `invalid pose`, `transport error`) in the `msg` field.


---

## ⚠ Mandatory Download of ALL MD and MMPBSA Output Files (L3 Principles 14-15)

**After EACH step in the MMPBSA pipeline, download ALL output files:**

| Step | Files to download | Category |
|------|------------------|----------|
| `fix_pdb` | Repaired PDB (`output_file`) | A — MUST |
| `prepare_complex` | em.gro, md.xtc, md.tpr, topol.top, md.gro/md_final.gro, npt.gro | A — MUST |
| `run_mmpbsa` | FINAL_RESULTS.csv, per-residue decomposition files, energy files | A — MUST |
| `analyze_mmpbsa` | ALL PNG plots (energy bars, decomposition charts), CSV reports | A — MUST |

Use `server_file_to_base64` for each file. Verify size > 0 after download. A pipeline step is NOT considered complete until all its output files are downloaded.

**For `prepare_complex` output directory:** List ALL files in `output_dir` and download every one with a recognized extension (gro, xtc, tpr, top, edr, log, pdb, csv).

## ⚠ Residue Numbering for Per-Residue Decomposition (L3 Principle 17)

Per-residue energy decomposition uses the numbering of the input PDB. If the task references specific residues in a different scheme (e.g., UniProt), build a mapping table using `molclaw-residue-mapper` BEFORE interpreting which residues are energy hotspots.

## ⚠ Result Plausibility (L3 Principle 9)

- Protein-ligand ΔG: typically −5 to −30 kcal/mol. Positive values suggest the ligand left the pocket during MD.
- **NEVER** convert MM-PBSA ΔG to Kd via ΔG = RT·ln(Kd). MM-PBSA is an approximation; only relative ranking is reliable.
- If GB and PB give opposite rankings, report BOTH and note the disagreement.


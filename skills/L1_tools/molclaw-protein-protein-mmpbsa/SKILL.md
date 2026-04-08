---
name: molclaw-protein-protein-mmpbsa
description: Execution-ready protein-protein MM/GB(PB)SA workflow with MCP-exposed tool names, strict file validation, and failure guards.
license: MIT license
metadata:
    skill-author: PJLab
---

# Protein-Protein MM/PBSA Workflow (Execution-Ready)

This skill guides agents through the protein-protein MM/GB(PB)SA pipeline with enforced MCP handoffs, file validation, and optional analysis.

## Canonical Toolchain & References

1. Step 1 — `fix_pdb` ([reference_fix_pdb.md](reference_fix_pdb.md)): repair the protein-protein complex and emit a cleaned PDB.
2. Step 2 — `prepare_protein_md` ([reference_prepare_protein_md.md](reference_prepare_protein_md.md)): build the protein-only MD workspace with the requested MD duration.
3. Step 3 — `gmx_mmpbsa_propro` ([reference_gmx_mmpbsa_propro.md](reference_gmx_mmpbsa_propro.md)): compute GB/PB binding energies inside the prepared workspace.
4. Optional Step 4 — `analyze_mmpbsa` ([reference_analyze_mmpbsa.md](reference_analyze_mmpbsa.md)): aggregate the CSV/plot outputs into a final report.

## MCP Tool Names (must use)

- `fix_pdb`
- `prepare_protein_md`
- `gmx_mmpbsa_propro`
- `analyze_mmpbsa` (optional)

## Entry / Data Handover

### Pre-flight checks

- Confirm the raw protein-protein complex PDB and associated restraints are accessible before calling `fix_pdb`.
- Decide whether `enable_analysis` will turn on Step 4 ahead of `gmx_mmpbsa_propro`.
- Keep `dry_run=False` for any production-grade binding energy request; use dry run only during validation loops.
- Prefer a validated quick profile first (`md_time=20`, `nvt_time=1`, `npt_time=1`) to avoid long blocking runs, then scale up only if needed.

### Data Handover Contract

1. `fix_pdb.output_file` → `prepare_protein_md.protein_pdb`
2. `prepare_protein_md.run_dir` → `gmx_mmpbsa_propro.work_dir`
3. Optional analysis consumes the MM/GBSA result workspace: `gmx_mmpbsa_propro.output_dir` → `analyze_mmpbsa.work_dir`
4. `gmx_mmpbsa_propro.output_files` (e.g., `gb_result_csv`, `pb_result_csv`) are the canonical GB/PB summaries for downstream reporting.

Never request users to provide intermediate GROMACS artifacts (`em.gro`, `md.xtc`, `md.tpr`, `topol.top`); those files are generated inside the MCP-managed workspace.

## Common MCP Client

```python
import json
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

class DrugSDAClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.session = None

    async def connect(self):
        self.transport = streamablehttp_client(url=self.server_url)
        self.read, self.write, self.get_session_id = await self.transport.__aenter__()
        self.session_ctx = ClientSession(self.read, self.write)
        self.session = await self.session_ctx.__aenter__()
        await self.session.initialize()

    async def disconnect(self):
        if self.session:
            await self.session_ctx.__aexit__(None, None, None)
        if hasattr(self, "transport"):
            await self.transport.__aexit__(None, None, None)

    @staticmethod
    def parse_result(result):
        if hasattr(result, "content") and result.content and hasattr(result.content[0], "text"):
            return json.loads(result.content[0].text)
        return result
```

## Step-by-step Execution Details

### Step 1: `fix_pdb`

- Entry checks
  - Verify the complex PDB and supporting files are reachable and correspond to the intended chains.
  - Disable `dry_run` when producing deliverable energies, toggle `add_hydrogens` per structural requirements.
- Success criteria
  - `status == "success"` and `output_file` contains a non-empty path.
  - `atom_count`, `residue_count`, and `chain_count` provide diagnostics for downstream validation.
  - On failure, return `msg` and abort before Step 2.

### Step 2: `prepare_protein_md`

- Entry checks
  - Accept `protein_pdb = fix_pdb.output_file` as input.
  - `full_md=True` is enforced for this workflow, and `temperature`, `nvt_time`, and `npt_time` must align with resource limits.
- Success criteria
  - `status == "success"` and `run_dir` contains the expected MD workspace.
  - Ensure the required files (`em.gro`, `md.xtc`, `md.tpr`, `topol.top`) exist inside `run_dir` before Step 3.
  - `files` lists the produced artifacts for troubleshooting.

### Step 3: `gmx_mmpbsa_propro`

- Entry checks
  - `work_dir` is the validated `prepare_protein_md.run_dir` and still contains the MD artifacts.
  - Default to `method="gb"` for quick runs or `method="both"` when PB outputs are also desired.
  - Keep `skip_mmpbsa=False` unless agents explicitly plan to build indexes only.
- Success criteria
  - `status` is `"success"` or `"partial_success"`; keep the latter when one method fails.
  - `output_files.gb_result_csv` and/or `output_files.pb_result_csv` capture the FINAL_RESULTS.* summary.
  - `metrics` aggregates the binding energies parsed from GB/PB outputs.

### Step 4: `analyze_mmpbsa` (optional)

- Entry checks
  - `enable_analysis` must be true and `work_dir` must point to a `gmx_mmpbsa_propro.output_dir` that houses the `mmgbsa`/`mmpbsa` directories.
  - Use `work_dir = gmx_mmpbsa_propro.output_dir` instead of the MD preparation directory.
- Success criteria
  - `status == "success"` and `reports` lists CSV/PNG/MD artifacts produced under `output_dir`.
  - `detected_mode` clarifies whether dual, PB-only, or GB-only data were compiled.
- Fallback behavior
  - If analysis fails, keep Step 3 outputs as the workflow deliverable, log the analyzer `msg`, and report `missing_files` in the summary.
  - Retry `gmx_mmpbsa_propro` with the missing method before rerunning the analyzer if a branch is absent.

## Agent Flow

- `fix_pdb.output_file` feeds `prepare_protein_md.protein_pdb`.
- `prepare_protein_md.run_dir` is the canonical `gmx_mmpbsa_propro.work_dir`.
- `gmx_mmpbsa_propro.output_dir` is the canonical `analyze_mmpbsa.work_dir`.
- `gmx_mmpbsa_propro.output_files.gb_result_csv`/`pb_result_csv` are the verified binding energy CSVs; both should be reported when `method="both"`.
- Optional `analyze_mmpbsa.output_dir` contains the final plots/tables enumerated in `reports`/`files`, and `detected_mode`/`missing_files` explain data coverage.

## Recommended Sequential Calling

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()

# Step 1: fix_pdb
r1 = client.parse_result(await client.session.call_tool(
    "fix_pdb",
    arguments={
        "input_path": "protein_protein_complex.pdb",
        "add_hydrogens": True,
        "ph": 7.0,
        "remove_heterogens": False,
        "remove_water": False,
        "replace_nonstandard": False,
        "add_missing_residues": False,
        "dry_run": False,
    },
))
fixed_pdb = r1["output_file"]

# Step 2: prepare_protein_md
r2 = client.parse_result(await client.session.call_tool(
    "prepare_protein_md",
    arguments={
        "protein_pdb": fixed_pdb,
        "full_md": True,
        "md_time": 20.0,
        "temperature": 300.0,
        "nvt_time": 1.0,
        "npt_time": 1.0,
    },
))
md_work_dir = r2["run_dir"]

# Validate required files before MM/PBSA
required_files = ["em.gro", "md.xtc", "md.tpr", "topol.top"]
# Agents should verify these exist under md_work_dir and return an error if missing

# Step 3: gmx_mmpbsa_propro
r3 = client.parse_result(await client.session.call_tool(
    "gmx_mmpbsa_propro",
    arguments={
        "work_dir": md_work_dir,
        "method": "gb",
        "nproc": 64,
        "skip_mmpbsa": False,
        "dry_run": False,
    },
))

# Step 4: analyze_mmpbsa (optional)
if enable_analysis:
    r4 = client.parse_result(await client.session.call_tool(
        "analyze_mmpbsa",
        arguments={
            "work_dir": r3["output_dir"],
        },
    ))

await client.disconnect()
```

## Practical Parameter Sets

1. **GB-only production run** (mirrors the CLI validation command)
   - `fix_pdb`: `{"input_path": "protein_protein_complex.pdb", "add_hydrogens": True, "dry_run": False}`
  - `prepare_protein_md`: `{"protein_pdb": "protein_protein_complex_fixed.pdb", "full_md": True, "md_time": 20.0, "temperature": 300.0, "nvt_time": 1.0, "npt_time": 1.0}`
  - `gmx_mmpbsa_propro`: `{"work_dir": "Protein_MD_01", "method": "gb", "nproc": 64, "skip_mmpbsa": False}`
  - Optional `analyze_mmpbsa`: `{"work_dir": "gmx_mmpbsa_propro_result_dir"}`

2. **Dual-method variant** (driven by the dual-mode CLI command)
   - `fix_pdb`: same as above
  - `prepare_protein_md`: `{"protein_pdb": "protein_protein_complex_fixed.pdb", "full_md": True, "md_time": 50.0, "temperature": 300.0, "nvt_time": 1.0, "npt_time": 1.0}`
   - `gmx_mmpbsa_propro`: `{"work_dir": "Protein_MD_02", "method": "both", "nproc": 64, "skip_mmpbsa": False}`
  - Optional `analyze_mmpbsa`: `{"work_dir": "gmx_mmpbsa_propro_result_dir"}`

## Agent Safety Checklist

1. Enforce `full_md=True` and realistic MD times before invoking the MM/PBSA stage.
2. Confirm `em.gro`, `md.xtc`, `md.tpr`, and `topol.top` exist under the `run_dir`; abort with missing-file names if any are absent.
3. Surface `partial_success` explicitly when `method="both"` runs complete only one branch.
4. Do not propagate `dry_run=True` outputs to end users.
5. If the optional analyzer fails, keep `gmx_mmpbsa_propro` results as the canonical output and append the analyzer `msg`/`missing_files` to the summary.
6. Do not wait indefinitely for long MD stages: report progress between steps and offer a quick-profile rerun when runtime exceeds expected limits.
7. Avoid repeated filesystem polling loops; if required files are missing after one check, fail fast and surface missing filenames.


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


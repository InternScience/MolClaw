---
name: molclaw-diffdock-auto
description: Run automated DiffDock protein-ligand docking and return confidence-based result summaries.
license: MIT license
metadata:
    skill-author: PJLab
---

# DiffDock Automated Protein-Ligand Docking

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.


## Usage

### 1. MCP Server
This skill relies on the MCP environment. If it is not installed, please run `pip install mcp`.

The **initialization** and **shutdown** of the MCP server are shown below:

```python
## When start, connect the MCP server
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
if not await client.connect():
    print("connection failed")
    return

## When finish, disconnect the MCP server
await client.disconnect() 
```

### 2. DiffDock Auto Docking

The description of tool *diffdock_auto*.

```tex
Automate DiffDock protein–ligand docking for single or batch inputs, run inference (unless `dry_run`), and return per-complex confidence summaries and produced files for prioritization.
Args:
    protein_path (str|None): Protein PDB file path for single docking.
    ligand (str|None): SMILES string or ligand file path (.sdf/.mol/.mol2/.pdb) for single docking.
    protein_sequence (str|None): Protein sequence to trigger ESMFold when no PDB is available.
    protein_ligand_csv (str|None): CSV path with `protein_path` and `ligand` columns for batch runs.
    complex_name (str|None): Optional complex identifier for a single docking task.
    inference_steps (int): Number of diffusion steps. Default: 20.
    samples_per_complex (int): Number of generated samples per complex. Default: 40.
    batch_size (int): Batch size for DiffDock inference. Default: 10.
    device (str): Compute device, 'cuda' or 'cpu'. Default: 'cuda'.
    dry_run (bool): If True, only validate inputs and skip DiffDock execution.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    output_dir (str|None): Path to the run-specific output directory under tool_result/diffdoc_result.
    summary_metrics (dict|None): Global metrics such as num_complexes, best_confidence, average_confidence, median_confidence.
    quality_distribution (dict|None): Counts grouped by quality labels (Excellent/Good/Medium/Low).
    complex_results (dict|None): Sanitized per-complex analysis dictionaries.
    summary_csv (str|None): Path to docking_summary.csv when exported.
    files (List[str]|None): Sorted file list produced in output_dir.
```

How to use tool *diffdock_auto* :

```python
response = await client.session.call_tool(
    "diffdock_auto",
    arguments={
        "protein_path": "/abs/path/outputok.pdb",
        "ligand": "CC(C)Cc1ccc(C)cc1",
        "inference_steps": 20,
        "samples_per_complex": 40,
        "batch_size": 10,
        "device": "cuda",
        "dry_run": False
    }
)
result = client.parse_result(response)
summary_metrics = result["summary_metrics"]

```

#### Example parameter sets

```python
# 1) Main mode: single protein-ligand docking (from readme usage/test)
{
    "protein_path": "/abs/path/outputok.pdb",
    "ligand": "CC(C)Cc1ccc(C)cc1",
    "dry_run": False
}

# 2) Variant mode: batch docking with CSV input (from diffdock_auto_main usage)
{
    "protein_ligand_csv": "/abs/path/batch_input.csv",
    "inference_steps": 20,
    "samples_per_complex": 60,
    "batch_size": 15,
    "dry_run": False
}

# 3) Variant mode: input validation only (dry run)
{``
    "protein_path": "/abs/path/outputok.pdb",
    "ligand": "CC(C)Cc1ccc(C)cc1",
    "device": "cpu",
    "dry_run": True
}
```


---

## ⚠ Mandatory Output File Download (L3 Principle 14)

**After calling this tool, you MUST download all output structure files** from the MCP server to the local workspace using `server_file_to_base64`. A tool call is NOT considered complete until its output files have been downloaded and verified locally (`ls -la <file>` — size must be > 0).

```python
import base64, os
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": result["output_file"]}  # or relevant output field
)
dl = client.parse_result(response)
local_path = "stepNN_descriptive_name.ext"
with open(local_path, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))
assert os.path.getsize(local_path) > 0, f"Download failed: {local_path}"
```

**Download policy:** All structure output files are **Category A (user-critical)** — essential for user verification, downstream analysis, and reproducibility. When in doubt, download. Over-collection is always preferred over under-collection.


## ⚠ CRITICAL: Cross-Molecule Ranking Prohibition

**DiffDock's confidence score is ONLY valid for comparing poses of the SAME molecule.** NEVER use DiffDock confidence to rank DIFFERENT molecules against each other. For cross-molecule ranking, use QuickVina docking scores, EquiScore, or Boltz-2 binding probability instead.

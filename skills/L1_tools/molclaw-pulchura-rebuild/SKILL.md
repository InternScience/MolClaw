---
name: molclaw-pulchura-rebuild
description: Rebuilds incomplete protein PDB structures with PULCHRA for downstream docking and simulation preparation.
license: MIT license
metadata:
    skill-author: PJLab
---

# PULCHRA Protein Structure Rebuild

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.

## Usage


### 2. Protein PDB Rebuild with PULCHRA
The description of tool *pulchura_rebuild*.

```tex
Rebuilds incomplete protein PDB structures with PULCHRA for structure preparation workflows before docking or simulation.
Args:
    input_pdbs (str | List[str]): One input PDB path or a list of input PDB paths.
    mode (str): Rebuild mode in {'full','backbone','sidechain','hydrogen'}, default 'full'.
    optimize_hbond (bool): Enable hydrogen-bond optimization (-q), default False.
    detect_cis_pro (bool): Enable cis-proline detection (-p), default False.
    verbose (bool): Print verbose PULCHRA logs (-v), default False.
    preserve_coords (bool): Preserve original coordinates (-f), default False.
    dry_run (bool): Validate inputs and create run directory without executing rebuild, default False.
Return:
    status (str): 'success', 'partial_success', or 'error'.
    msg (str): Human-readable execution summary.
    output_dir (str): Run-specific directory under tool_result/pulchura_rebuild_result.
    mode (str): Effective rebuild mode used for this run.
    requested_input_count (int): Number of input files requested by caller.
    succeeded_count (int): Number of inputs rebuilt successfully.
    failed_count (int): Number of inputs that failed validation or rebuild.
    rebuilt_pdb_files (List[str]): Paths to rebuilt PDB files.
    failed_inputs (List[Dict[str, str]]): Per-input failure details with input_pdb and error.
```

How to use tool *pulchura_rebuild* :

```python
response = await client.session.call_tool(
    "pulchura_rebuild",
    arguments={
        "input_pdbs": "/path/to/input.pdb",
        "mode": "full",
        "optimize_hbond": False,
        "detect_cis_pro": False,
        "verbose": False,
        "preserve_coords": False,
        "dry_run": False
    }
)
result = client.parse_result(response)
rebuilt_pdb_files = result["rebuilt_pdb_files"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "input_pdbs": "/path/to/input.pdb",
    "mode": "full",
    "optimize_hbond": True,
    "detect_cis_pro": False,
    "verbose": False,
    "preserve_coords": False,
    "dry_run": False
}

# 2) Variant mode
{
    "input_pdbs": "relative/path/to/frame_0.pdb",
    "mode": "backbone",
    "optimize_hbond": False,
    "detect_cis_pro": False,
    "verbose": False,
    "preserve_coords": False,
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


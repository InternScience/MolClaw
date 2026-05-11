---
name: molclaw-pulchura-rebuild
description: Rebuilds incomplete protein PDB structures with PULCHRA for downstream docking and simulation preparation.
license: MIT license
metadata:
    skill-author: PJLab
---

# PULCHRA Protein Structure Rebuild

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Usage

### 1. Protein PDB Rebuild with PULCHRA
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

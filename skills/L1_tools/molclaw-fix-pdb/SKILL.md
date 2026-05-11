---
name: molclaw-fix-pdb
description: Repair and clean PDB files with PDBFixer, returning repaired file path and topology counts.
license: MIT license
metadata:
    skill-author: PJLab
---

# PDBFixer Repair

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Usage

### 1. PDB Repair

The description of tool *fix_pdb*.

```tex
Repair a PDB file using PDBFixer, optionally clean or model missing parts, write the repaired PDB (unless `dry_run`), and return topology counts.
Args:
    input_path (str): Path to the source PDB file to repair.
    output_path (str|None): Optional output file path for the repaired PDB. If omitted the tool writes to a run-specific folder.
    add_hydrogens (bool): Add missing hydrogens after filling atoms (default: False).
    ph (float): pH value used when adding hydrogens (default: 7.0).
    remove_heterogens (bool): Remove heterogens/ligands (keeps waters unless `remove_water` True).
    remove_water (bool): Remove water molecules (default: False).
    replace_nonstandard (bool): Replace nonstandard residues with standard counterparts (default: False).
    keep_chains (List[str]|None): If provided, retain only these chain IDs.
    add_missing_residues (bool): Attempt to model missing residues before filling atoms (default: False).
    dry_run (bool): Validate operations without writing the repaired file (default: False).
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    output_dir (str|None): Run-specific directory under tool_result/pdbfixer_result.
    output_file (str|None): Path to the repaired PDB file (None for dry runs or on error).
    atom_count (int|None): Total atoms in the repaired topology when available.
    residue_count (int|None): Total residues in the repaired topology when available.
    chain_count (int|None): Total chains in the repaired topology when available.
```

How to use tool *fix_pdb* :

```python
response = await client.session.call_tool(
    "fix_pdb",
    arguments={
        "input_path": "/path/to/input.pdb",
        "output_path": None,
        "add_hydrogens": True,
        "ph": 7.0,
        "remove_heterogens": False,
        "remove_water": False,
        "replace_nonstandard": False,
        "keep_chains": None,
        "add_missing_residues": False,
        "dry_run": True,
    }
)
result = client.parse_result(response)
output_file = result.get("output_file")

```

#### Example parameter sets

```python
# 1) Main mode: basic repair with hydrogens added (dry-run for validation)
{
    "input_path": "/path/to/input.pdb",
    "add_hydrogens": True,
    "dry_run": True
}

# 2) Variant mode: keep specific chains and remove waters, write output
{
    "input_path": "/path/to/input.pdb",
    "keep_chains": ["A", "B"],
    "remove_water": True,
    "dry_run": False
}
```

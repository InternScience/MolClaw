---
name: molclaw-fix-pdb
description: Repair and clean PDB files with PDBFixer, returning repaired file path and topology counts.
license: MIT license
metadata:
    skill-author: PJLab
---

# PDBFixer Repair

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 

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

### 2. PDB Repair

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


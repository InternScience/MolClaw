---
name: molclaw-pdbfixer
description: Repair a protein PDB file with PDBFixer: fix missing atoms/residues, add hydrogens, remove heterogens, etc. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Repair Protein Structure File

Use tool *fix_pdb* to repair the protein structure file (pdb format) as below:

Tool description:

```tex
Repair a PDB file with PDBFixer: fix missing atoms/residues, add hydrogens, remove heterogens, etc.
Args:
    input_path (str): Path to the source PDB file to repair (required)
    add_hydrogens (bool): Add missing hydrogens after atom completion (default: False)
    ph (float): pH value used when adding hydrogens (default: 7.0)
    remove_heterogens (bool): Remove heterogens/ligands; keeps waters if remove_water is False (default: False)
    remove_water (bool): Remove water molecules even if heterogens are retained (default: False)
    replace_nonstandard (bool): Replace nonstandard residues with standard counterparts (default: False)
    keep_chains (List[str] | None): If provided, only retain the listed chain IDs (default: None)
    add_missing_residues (bool): Attempt to model missing residues before filling atoms (default: False)
    dry_run (bool): Validate and simulate repairs without writing output file (default: False)
Return:
    status (str): 'success' or 'error'
    msg (str): Human-readable summary of the result
    output_dir (str | None): Run-specific folder under tool_result/pdbfixer_result
    output_file (str | None): Path to the repaired PDB file (None during dry_run or on error)
    atom_count (int | None): Total atoms in the repaired topology
    residue_count (int | None): Total residues in the repaired topology
    chain_count (int | None): Total chains in the repaired topology
```

Tool usage:

```python
response = await client.session.call_tool(
    "fix_pdb",
    arguments={
        "input_path": pdb_path,
        "add_hydrogens": add_hydrogens,
        "ph": ph,	
        "remove_water": remove_water,
        "replace_nonstandard": replace_nonstandard,
        "remove_heterogens": remove_heterogens,
        "add_missing_residues": add_missing_residues
    }
)
result = client.parse_result(response)
fixed_pdb_path = result["output_file"]
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


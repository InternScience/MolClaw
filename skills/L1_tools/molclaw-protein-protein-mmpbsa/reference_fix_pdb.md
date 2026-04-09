---
name: reference_fix_pdb
description: Tool reference for the MCP `fix_pdb` call used by the protein-protein MM/PBSA workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# fix_pdb Reference

## Usage


### 2. Scenario Description

Repair a PDB file using PDBFixer, optionally adding hydrogens or modeling missing residues, and return the cleaned structure plus topology counts.

Args:
- `input_path` (str): Source PDB file to repair (required).
- `output_path` (str | None): Optional override path to write the repaired PDB; defaults to the MCP-managed run directory.
- `add_hydrogens` (bool): Whether to add missing hydrogens after residue repair (default: False).
- `ph` (float): pH used when adding hydrogens (default: 7.0).
- `remove_heterogens` (bool): Drop heterogens and keep waters unless `remove_water` is True.
- `remove_water` (bool): Remove water molecules (default: False).
- `replace_nonstandard` (bool): Replace nonstandard residues with their standard equivalents (default: False).
- `keep_chains` (List[str] | None): Restrict the repair to a subset of chains.
- `add_missing_residues` (bool): Attempt to model missing residues before filling atoms (default: False).
- `dry_run` (bool): Validate operations without writing the repaired PDB (default: False).

Return:
- `status` (str): `'success'` or `'error'`.
- `msg` (str): Human-readable summary or error message.
- `output_dir` (str | None): Run-specific directory under `tool_result/pdbfixer_result`.
- `output_file` (str | None): Path to the repaired PDB file (None on dry run or failure).
- `atom_count` (int | None): Atom count of the repaired topology, when available.
- `residue_count` (int | None): Residue count when available.
- `chain_count` (int | None): Number of chains detected.

### 3. How to use tool `fix_pdb`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "fix_pdb",
    arguments={
        "input_path": "protein_protein_complex.pdb",
        "add_hydrogens": True,
        "ph": 7.0,
        "remove_heterogens": False,
        "remove_water": False,
        "replace_nonstandard": True,
        "keep_chains": ["A", "B"],
        "add_missing_residues": False,
        "dry_run": False,
    },
)
result = DrugSDAClient.parse_result(response)
fixed_pdb = result.get("output_file")
await client.disconnect()
```

#### Example parameter sets

1. **Validation (dry run)**

```python
{
    "input_path": "protein_protein_complex.pdb",
    "add_hydrogens": True,
    "dry_run": True,
}
```

2. **Full repair for selected chains**

```python
{
    "input_path": "protein_complex.pdb",
    "keep_chains": ["A", "B"],
    "remove_water": True,
    "replace_nonstandard": True,
    "dry_run": False,
}
```

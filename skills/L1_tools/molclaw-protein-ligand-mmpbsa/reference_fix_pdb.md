---
name: reference_fix_pdb
description: Reference doc for the MCP `fix_pdb` call used by the Protein-Ligand MM/PBSA workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# fix_pdb Reference

## Usage


### 2. Scenario Description

Cleans a receptor PDB (adding hydrogens, modeling missing atoms) so that `prepare_complex` can receive a validated `protein` path.

Args:
- `input_path` (str): Source PDB file (required).
- `output_path` (str | None): Optional override for the repaired file; defaults to the MCP sandbox.
- `add_hydrogens` (bool): Add hydrogens after repairs.
- `ph` (float): pH for protonation (default: 7.0).
- `remove_heterogens` (bool): Drop heterogens if requested.
- `remove_water` (bool): Exclude water molecules.
- `replace_nonstandard` (bool): Map non-standard residues.
- `keep_chains` (List[str] | None): Restrict repairs to listed chain IDs.
- `add_missing_residues` (bool): Model missing residues before filling coordinates.
- `dry_run` (bool): Validate without writing output (default: False).

Returns:
- `status` (str): `'success'` or `'error'`.
- `msg` (str): Human summary or failure reason.
- `output_dir` (str | None): MCP run directory under `tool_result/pdbfixer_result`.
- `output_file` (str | None): Repaired receptor path.
- `atom_count`, `residue_count`, `chain_count` (int | None): Topology counts when available.

### 3. How to use tool `fix_pdb`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "fix_pdb",
    arguments={
        "input_path": "protein.pdb",
        "add_hydrogens": True,
        "ph": 7.0,
        "keep_chains": None,
        "dry_run": False,
    },
)
result = DrugSDAClient.parse_result(response)
fixed_protein = result.get("output_file")
await client.disconnect()
```

#### Example parameter sets
1. **Main mode (clean receptor for MM/PBSA)**

```python
{
    "input_path": "protein.pdb",
    "add_hydrogens": True,
    "dry_run": False,
}
```

2. **Variant: chain-specific water removal**

```python
{
    "input_path": "protein.pdb",
    "keep_chains": ["A", "B"],
    "remove_water": True,
    "dry_run": False,
}
```

Key outputs for the workflow: `output_file` feeds `prepare_complex.protein`, `atom_count`/`residue_count` provide validation.

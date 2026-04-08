---
name: molclaw-equiscore-docking
description: End-to-end docking-score ranking using EquiScore for candidate molecules against a target protein.
license: MIT license
metadata:
    skill-author: PJLab
---

# 1. EquiScore Docking Ranking Skill

step 1. Retrieve target protein structure (skip if user already provides PDB).
- Use skill `molclaw-protein-structure-retrieve`.

step 2. Optional chain extraction (only if specific chains are required).

```python
response = await client.session.call_tool(
    "extract_and_save_chains",
    arguments={"pdb_file_path": pdb_path, "chain_ids": chain_ids}
)
result = client.parse_result(response)
pdb_path = result["out_file"]
```

step 3. Fix receptor structure with PDBFixer.

```python
response = await client.session.call_tool(
    "fix_pdb",
    arguments={
        "input_path": pdb_path,
        "add_hydrogens": True,
        "ph": 7.0,
        "remove_heterogens": True,
        "remove_water": True,
        "replace_nonstandard": True
    }
)
result = client.parse_result(response)
fixed_pdb_path = result["output_file"]
```

## 2. EquiScore-based Ranking Flow

step 4. Drug-likeness filtering.
- Keep molecules satisfying: `QED >= 0.2` and `lipinski_rule_of_5_violations <= 2`.
- Always compute from returned `result["metrics"]`; do not use manually copied values.
- Assert `len(metrics) == len(candidate_smiles_list)` before filtering.

```python
response = await client.session.call_tool(
    "calculate_mol_drug_chemistry",
    arguments={"smiles_list": candidate_smiles_list}
)
result = client.parse_result(response)

metrics = result["metrics"]

filtered_smiles = [
    m["smiles"] for m in metrics
    if m["qed"] >= 0.2 and m["lipinski_rule_of_5_violations"] <= 2
]
```

step 5. Build EquiScore docking input.

Important:
- EquiScore needs a docking-result SDF (ligand poses relative to receptor).
- Raw SDF converted directly from SMILES is not sufficient for `equiscore_pocket`.

Two valid modes:
- Mode A: user already provides `docking_result_sdf_path` -> use directly.

- Mode B: only SMILES provided -> first generate docking poses (docked SDF) using the established quick-vina / molecule_docking_quickvina workflow (as shown in the golden pipeline CCR6 case: convert_smiles_to_format → molecule_docking_quickvina with pocket box → output docked SDF), then set docking_result_sdf_path to the resulting docked file before continuing to step6. This ensures receptor-relative poses.

When converting formats, use this tool:

```python
response = await client.session.call_tool(
    "convert_smiles_to_format",
    arguments={"inputs": filtered_smiles, "target_format": "sdf"}
)
result = client.parse_result(response)
convert_results = result["convert_results"]
```

Tool contract:

```text
convert_smiles_to_format(inputs: List[str], target_format: str)
Args:
  inputs: list of SMILES strings or .smi file paths
  target_format: sdf/mol/mol2/pdb/pdbqt/xyz/cif/inchi
Return:
  status, msg, convert_results[{input, output_file}]
```

step 6. Run EquiScore pocket extraction first.
- Use `molclaw-equiscore-tool` -> `equiscore_pocket`.
- Before first call, verify tool argument names from schema (`list_tools` + `inputSchema`) if uncertain.

```python
response = await client.session.call_tool(
    "equiscore_pocket",
    arguments={
        "docking_result": docking_result_sdf_path,
        "receptor_pdb": fixed_pdb_path,
        "pocket_cutoff": None,
        "dry_run": False
    }
)
pocket_res = client.parse_result(response)
pocket_dir = pocket_res["pocket_dir"]
```

If `split_sdf_count == 0` or `pocket_item_count == 0`, fix docking input first and rerun this step.

step 7. Run EquiScore screening.
- Use `molclaw-equiscore-tool` -> `equiscore_screen`.

```python
response = await client.session.call_tool(
    "equiscore_screen",
    arguments={
        "pocket_dir": pocket_dir,
        "ngpu": 1,
        "batch_size": 128,
        "num_workers": 8,
        "multi_pose": False,
        "pose_num": 1,
        "debug": False,
        "dry_run": False
    }
)
screen_res = client.parse_result(response)
predictions_path = screen_res["predictions_path"]
score_field = screen_res.get("score_field")
```

step 8. Rank and return.
- Prefer direct CSV read from `predictions_path`.
- If direct read fails, use `molclaw-file-transfer` (`server_file_to_base64`) to fetch CSV and parse locally.
- Preserve `ligand_to_smiles_map`; do not assume CSV always has a `smiles` column.


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


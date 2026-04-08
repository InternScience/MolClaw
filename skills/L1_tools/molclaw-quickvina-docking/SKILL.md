---
name: molclaw-quickvina-docking
description: Perform molecular docking using QuickVina2-GPU between target protein structure and small molecules. 
license: MIT license
metadata:
    skill-author: PJLab
---

# QuickVina2 Molecular Docking

step 1. Use skill **molclaw-protein-structure-retrieve** to get the target protein structure file. If the target protein structure file has been provided, skip this step.

step 2. If the user specifies a target chain or several chains, or if the agent autonomously identifies single-chain or multi-chain structures requiring extraction, invoke the tool *extract_and_save_chains* to generate and save the corresponding structure as a new PDB file. Otherwise, skip this step.

```python
response = await tool_client.session.call_tool(
    "extract_and_save_chains",
    arguments={
        "pdb_file_path": pdb_path,
        "chain_ids": chain_ids		##Chain IDs (e.g., ["A", "C"]) 		
    }
)
result = tool_client.parse_result(response)
pdb_path = result["out_file"]
```

step 3. Use skill **molclaw-pdbfixer** to repair the protein structure file using the settings as below.  

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

step 4. Use skill **molclaw-fpocket** to detect binding sites on the protein structure and return pocket information of the best one.

step 5. Use tool *convert_pdb_to_pdbqt_dock* to convert the fixed protein structure file from PDB to PDBQT format.

```python
response = await client.session.call_tool(
    "convert_pdb_to_pdbqt_dock",
    arguments={
        "pdb_file_path": fixed_pdb_path
    }
)
result = client.parse_result(response)
receptor_path = result["output_file"]
```

step 6. Use tool *convert_smiles_to_format* to covert the input SMILES strings of small molecules to PDBQT format.

```python
response = await client.session.call_tool(
    "convert_smiles_to_format",
    arguments={
        "inputs": smiles_list,		##A list of input SMILES strings, List[str]
        "target_format": "pdbqt"
    }
)
result = client.parse_result(response)
ligand_paths = [x["output_file"] for x in result["convert_results"]]
```

step 7. Finally, use tool *molecule_docking_quickvina* to perform molecular docking between protein (receptor) and small molecules (ligands).

 Tool description:

```tex
Perform molecular docking using QuickVina2-GPU (Accelerated version of AutoDock Vina).
Args:
    receptor_path (str): Path to the protein receptor file (format .pdbqt)
    ligand_path (str): Path tp the compound ligand file (format .pdbqt)
    center_x (float): X-coordinate of the docking pocket center
    center_y (float): Y-coordinate of the docking pocket center
    center_z (float): Z-coordinate of the docking pocket center
    size_x (float): Size of the docking pocket along the X-axis (default 25.0)
    size_y (float): Size of the docking pocket along the Y-axis (default 25.0)
    size_z (float): Size of the docking pocket along the Z-axis (default 25.0)
Return:
    status (str): success/partial_success/error
    msg (str): message
    affinity_value (float): Docking affinity value, unit kcal/mol
    docking_res_file (str): A PDBQT file contains docking poses, atom types, and charges for analyzing binding results.
```

Tool Usage:

```python
for ligand_path in ligand_paths:
    result = await client.session.call_tool(
        "molecule_docking_quickvina",
        arguments={
            "receptor_path": receptor_path,
            "ligand_path": ligand_path,
            "center_x": best_pocket["center_x"],
            "center_y": best_pocket["center_y"],
            "center_z": best_pocket["center_z"],
            "size_x": best_pocket["size_x"],
            "size_y": best_pocket["size_y"],
            "size_z": best_pocket["size_z"]
        }
    )
    result_data = client.parse_result(result)
    docking_affinity_value = result_data['affinity_value']
```

QuickVina outputs a predicted binding affinity in units of kcal/mol. Similar to AutoDock Vina, the scores are negative values, where a more negative value indicates stronger binding. The scoring function comprehensively accounts for steric complementarity (Gaussian attraction plus quadratic repulsion), hydrogen bonding, hydrophobic interactions, and an entropy penalty for rotatable bonds.

**Screening Thresholds:** There is no universal absolute threshold for QuickVina or Vina, as binding pockets vary significantly across different targets in terms of size, hydrophobicity, and other properties. However, general empirical guidelines suggest that for drug-like small molecules (MW 300–500):

- A score of **≤ -7 kcal/mol** is typically considered a starting point indicating potential binding activity.
- A score of **≤ -9 kcal/mol** is generally regarded as indicative of strong binding.

In practice, rather than relying on a fixed threshold, it is more common to rank all compounds for a specific target by their scores and select the **top n** for further validation.



**Note**: This skill workflow consists of seven steps, some of which depend on other skills. Please refer carefully to the Markdown documentation of the dependent skills to ensure correct usage.
---

## ⚠ Docking Box Minimum Size (L3 Principle 18 — HARD CONSTRAINT)

**NEVER set `size_x`, `size_y`, or `size_z` below 25.0 Å.** If the pocket detection tool returns dimensions smaller than 25 Å on any axis, override that axis to 25.0 Å. A box that is too small will miss valid binding poses or cause docking to return errors/positive scores.

```python
# Enforce minimum 25 Å per dimension
size_x = max(25.0, best_pocket["size_x"])
size_y = max(25.0, best_pocket["size_y"])
size_z = max(25.0, best_pocket["size_z"])
```

## ⚠ Score Validation Checkpoint (L3 Principle 12 Checkpoint A)

**After EACH docking call, immediately verify:**
- **Score must be negative (kcal/mol).** A positive `affinity_value` indicates docking failure — do NOT silently accept it, do NOT include it in rankings.
- **Score should be > −15.0 kcal/mol for standard drug-like molecules.** Scores below −15 are suspicious (oversized ligand or box error).
- **If score is positive or docking fails:** Execute progressive box enlargement before giving up:

| Retry | Box size per dimension | Action |
|-------|----------------------|--------|
| 0 (initial) | max(25, detected) | Standard |
| 1 | 30 Å | First retry |
| 2 | 40 Å | Second retry |
| 3 | 50 Å | Third retry |
| 4 | — | Switch to DiffDock/KarmaDock |

Log every retry attempt in `run_log.md`.

**If multiple molecules all return identical scores (especially 0.0):** This indicates a systematic setup error — check receptor format, box definition, and ligand preparation.

## ⚠ Mandatory Pose File Download (L3 Principle 14)

**After EACH successful docking, download the `docking_res_file` (PDBQT with poses) from the MCP server.** This is a Category A file — essential for downstream EquiScore rescoring, ProLIF analysis, MM-PBSA, and user verification.

```python
import base64, os
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": result_data["docking_res_file"]}
)
dl = client.parse_result(response)
local_path = f"step{N}_mol{i:02d}_docking_pose.pdbqt"
with open(local_path, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))
assert os.path.getsize(local_path) > 0, f"Pose download failed: {local_path}"
```

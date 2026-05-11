---
name: molclaw-quickvina-docking
description: Perform molecular docking using QuickVina2-GPU between target protein structure and small molecules. 
license: MIT license
metadata:
    skill-author: PJLab
---

# QuickVina2 Molecular Docking

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

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

step 4. Use skill **molclaw-fpocket** or **molclaw-p2rank** to detect binding sites on the protein structure and return pocket information of the best one. If the pocket center and box size are already known (e.g., from a co-crystal ligand), skip this step and use the known values directly.

step 5. Use tool *molecule_docking_quickvina_fullprocess* to perform molecular docking. This is a **full-process tool** — it accepts a PDB file and SMILES string directly and handles all format conversions (PDB→PDBQT, SMILES→PDBQT) internally. **Do NOT manually convert to PDBQT before calling this tool.**

Tool description:

```tex
Perform molecular docking using QuickVina2-GPU (Accelerated version of AutoDock Vina).
Args:
    pdb_file_path (str): Path to the protein receptor file (format .pdb)
    smiles (str): Input molecule SMILES string
    pocket_center_x (float): X-coordinate of the docking pocket center
    pocket_center_y (float): Y-coordinate of the docking pocket center
    pocket_center_z (float): Z-coordinate of the docking pocket center
    pocket_size_x (float): Size of the docking pocket along the X-axis (default 25.0)
    pocket_size_y (float): Size of the docking pocket along the Y-axis (default 25.0)
    pocket_size_z (float): Size of the docking pocket along the Z-axis (default 25.0)
Return:
    status (str): success/error
    msg (str): message
    docking_affinity_value (float): Docking affinity value, unit kcal/mol
    docking_file (str): A PDBQT file contains docking poses, atom types, and charges for analyzing binding results.
```

Tool Usage:

```python
for smiles in smiles_list:
    response = await client.session.call_tool(
        "molecule_docking_quickvina_fullprocess",
        arguments={
            "pdb_file_path": fixed_pdb_path,
            "smiles": smiles,
            "pocket_center_x": best_pocket["center_x"],
            "pocket_center_y": best_pocket["center_y"],
            "pocket_center_z": best_pocket["center_z"],
            "pocket_size_x": max(25.0, best_pocket.get("size_x", 25.0)),
            "pocket_size_y": max(25.0, best_pocket.get("size_y", 25.0)),
            "pocket_size_z": max(25.0, best_pocket.get("size_z", 25.0))
        }
    )
    result_data = client.parse_result(response)
    docking_affinity = result_data['docking_affinity_value']
    docking_pose_file = result_data['docking_file']
```

QuickVina outputs a predicted binding affinity in units of kcal/mol. Similar to AutoDock Vina, the scores are negative values, where a more negative value indicates stronger binding. The scoring function comprehensively accounts for steric complementarity (Gaussian attraction plus quadratic repulsion), hydrogen bonding, hydrophobic interactions, and an entropy penalty for rotatable bonds.

**Docking Box Minimum Size:** Never set `pocket_size_x`, `pocket_size_y`, or `pocket_size_z` below 25.0 Å. If the pocket detection tool returns dimensions smaller than 25 Å on any axis, override that axis to 25.0 Å.

**Screening Thresholds:** There is no universal absolute threshold for QuickVina or Vina, as binding pockets vary significantly across different targets in terms of size, hydrophobicity, and other properties. However, general empirical guidelines suggest that for drug-like small molecules (MW 300–500):

- A score of **≤ -7 kcal/mol** is typically considered a starting point indicating potential binding activity.
- A score of **≤ -9 kcal/mol** is generally regarded as indicative of strong binding.

In practice, rather than relying on a fixed threshold, it is more common to rank all compounds for a specific target by their scores and select the **top n** for further validation.

**Score Validation:** After each docking call, verify that the score is negative (kcal/mol). A positive `docking_affinity_value` indicates docking failure — do not accept it. If docking fails, try progressive box enlargement (25→30→40→50 Å per dimension) before switching to alternative methods.

**Note**: This skill workflow consists of five steps, some of which depend on other skills. Please refer carefully to the Markdown documentation of the dependent skills to ensure correct usage.

## Multi-Target Docking Shortcut

When docking the SAME molecule against multiple ALREADY PREPARED targets (each with known pocket parameters from baseline establishment), skip steps 1–4 and call `molecule_docking_quickvina_fullprocess` directly for each target, using each target's locked pocket parameters. Do NOT re-run pocket detection per target per round — pocket parameters are locked at baseline (see Skill 5 Docking Parameter Locking).

```python
# Example: dock one molecule against two prepared targets
for target in [target1_info, target2_info]:
    response = await client.session.call_tool(
        "molecule_docking_quickvina_fullprocess",
        arguments={
            "pdb_file_path": target["prepared_pdb"],
            "smiles": candidate_smiles,
            "pocket_center_x": target["locked_center_x"],
            "pocket_center_y": target["locked_center_y"],
            "pocket_center_z": target["locked_center_z"],
            "pocket_size_x": target["locked_size_x"],
            "pocket_size_y": target["locked_size_y"],
            "pocket_size_z": target["locked_size_z"]
        }
    )
```

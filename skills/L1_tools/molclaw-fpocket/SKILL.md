---
name: molclaw-fpocket
description: Use fpocket to detect binding pockets and output their detailed properties for the input protein. This offers a more concise approach to pocket identification.  
license: MIT license
metadata:
    skill-author: PJLab
---

# Pocket Detection

The description of tool *fpocket_toolkit*.

```tex
Detect binding pockets in a protein structure using fpocket_toolkit.
Args:
    pdb_file (str): Input PDB/mmCIF file path to scan for pockets (required)
    top_n (int): Limit returned pockets to the top N by druggability score; 0 means return all (default: 0)
    min_druggability (float | None): Filter out pockets below this druggability threshold (0.0~1.0); None means no filter (default: None)
    verbose (bool): Request verbose descriptor parsing during the run for detailed logging (default: False)
Return:
    status (str): 'success' or 'error'
    msg (str): Human-readable narrative about the run
    run_dir (str): Absolute directory storing this run's results
    output_dir (str): Path where fpocket preserved its raw outputs
    pockets (List[Dict[str, Any]]): Parsed pocket descriptors, including scores, centers, and residue contacts
    pocket_count (int): Number of pockets returned after filtering
    output_files (Dict[str, str]): Preserved fpocket output files such as info, pymol scripts, etc.
    exported (Dict[str, str] | None): Export metadata when export_path is provided
    files (Dict[str, str]): All files created under the run_dir
```

How to use tool *fpocket_toolkit* :

```python
response = await client.session.call_tool(
    "fpocket_toolkit",
    arguments={
        "pdb_file": pdb_file,
        "top_n": top_n
    }
)
result = client.parse_result(response)
pred_pockets = result["pockets"]
```

Here is an example of a pocket from *pred_pockets*:

```tex
{
  "score": 0.377,
  "druggability_score": 0.058,
  "nb_alpha_spheres": 64,
  "total_sasa": 180.518,
  "polar_sasa": 91.153,
  "apolar_sasa": 89.364,
  "volume": 4.067,
  "mean_local_hyd_density": 14.167,
  "mean_alpha_sphere_radius": 3.909,
  "mean_asph_solvent_access": 0.598,
  "apolar_asph_proportion": 0.375,
  "hydrophobicity_score": 4.8,
  "polarity_score": 10.0,
  "charge_score": 1.0,
  "prop_polar_atoms": 40.816,
  "alpha_sphere_density": 7.167,
  "cent_mass_asph_max_dist": 22.004,
  "flexibility": 0.0,
  "pocket_id": 1,
  "center_x": 2.1842,
  "center_y": -59.6956,
  "center_z": -4.6317,
  "size_x": 20.0535,
  "size_y": 30.6513,
  "size_z": 22.1714,
  "n_pocket_atoms": 49,
  "chains": [
    "A"
  ],
  "n_residues": 15,
  "residues": [
    "ALA177:A",
    "ARG173:A",
    "ASN139:A",
    "ASN183:A",
    "GLN176:A",
    "GLN179:A",
    "GLU187:A",
    "ILE37:A",
    "LEU172:A",
    "LYS182:A",
    "PRO34:A",
    "PRO38:A",
    "SER41:A",
    "THR186:A",
    "TYR169:A"
  ]
}
```



After detecting the pockets, please comprehensively evaluate their various properties to **select the optimal binding site** for small-molecule ligands.



**Note**: The input protein structure file should be repaired before running fpocket.

---

## ⚠ Docking Box Size Enforcement (L3 Principle 18)

When fpocket pocket dimensions are used for downstream docking (QuickVina, etc.), **enforce a minimum of 25.0 Å per dimension.** If any pocket dimension returned by fpocket is less than 25 Å, override it to 25.0 Å before passing to the docking tool.

```python
# After fpocket pocket detection:
size_x = max(25.0, pocket["size_x"])
size_y = max(25.0, pocket["size_y"])
size_z = max(25.0, pocket["size_z"])
```


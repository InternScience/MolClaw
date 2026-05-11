---
name: molclaw-prolif-md
description: ProLIF MD trajectory analysis skill for protein-ligand interaction fingerprints with frame slicing and residue controls.
license: MIT license
metadata:
    skill-author: PJLab
---

# ProLIF MD Interaction Fingerprinting Skill

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

> [!NOTE]
> Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution.
> For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.

## Task Description
Analyze protein-ligand interaction fingerprints in molecular dynamics (MD) trajectories, with support for frame slicing and residue controls. Use this skill to evaluate whether binding patterns remain stable throughout simulation.

> **Routing note:** This tool is the **primary** choice for MD trajectory interaction dynamics (multi-frame analysis). For **single-structure** analysis (one frame, one complex), use `molclaw-interaction-visualizer` instead.

## Input Source Mapping
| Parameter | Source Guidance |
|-----------|-----------------|
| `topology_path` | Output topology file from MD workflow tools: e.g., `protein_openmm_md`, `prepare_complex`, `prepare_protein_md`, or `goca_pipeline` (`.psf`/`.pdb`/`.prmtop`) |
| `trajectory_path` | Output trajectory file from the same MD workflow tools (`.dcd`/`.nc`/`.xtc`) |
| `ligand_selection` | User-provided ligand selection string, for example `resname LIG` or `resid 100-101` |
| `protein_selection` | Defaults to `protein`; can be customized to narrow protein scope |

## Usage
### Tool: `prolif_md`

```text
Compute ProLIF fingerprints for an MD trajectory and return standardized summary metrics.
Args:
    topology_path (str): Path to the topology file (e.g., .psf, .pdb, .prmtop).
    trajectory_path (str): Path to the trajectory file to analyze.
    ligand_selection (str): Selection string identifying ligand atoms.
    protein_selection (str): Selection string for protein atoms. Default: 'protein'.
    interactions (List[str]|None): Optional interaction types to compute (e.g., Hydrophobic, HBDonor).
    count (bool): If True, compute interaction counts instead of fingerprints. Default: False.
    vicinity_cutoff (float|None): Optional distance cutoff for vicinity interactions.
    params_json (str|None): Optional JSON parameter file path for ProLIF interaction settings.
    start (int|None): Optional start frame index.
    stop (int|None): Optional stop frame index (exclusive).
    step (int|None): Optional frame stride.
    residues (List[str]|None): Optional explicit residue list to include.
    all_residues (bool): If True, include all residues in analysis. Default: False.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The executed command label ('md').
    output_dir (str|None): Run-specific directory under tool_result/prolif_result.
    output_file (str|None): Path to the generated CSV file.
    n_frames (int|None): Number of processed frames.
    n_interactions (int|None): Number of interaction columns in output.
    frequent_interactions (List[dict]|None): High-frequency interactions (>30%) with keys 'interaction' and 'frequency'.
    result_summary (dict|None): Full summary dictionary from the wrapper.
```

### How To Use `prolif_md`

```python
response = await client.session.call_tool(
    "prolif_md",
    arguments={
        "topology_path": "relative/path/to/system.prmtop",
        "trajectory_path": "relative/path/to/md_prod.nc",
        "ligand_selection": "resname LIG",
        "protein_selection": "protein",
        "interactions": ["Hydrophobic", "HBDonor"],
        "start": 0,
        "stop": 100,
        "step": 2
    }
)
result = client.parse_result(response)
key_output = result["output_file"]
```

### Example Parameter Sets

```python
# 1) Main mode
{
    "topology_path": "relative/path/to/system.prmtop",
    "trajectory_path": "relative/path/to/md_prod.nc",
    "ligand_selection": "resname LIG",
    "protein_selection": "protein",
    "interactions": ["Hydrophobic", "HBDonor", "HBAcceptor"],
    "start": 0,
    "stop": 100,
    "step": 2
}

# 2) Variant mode
{
    "topology_path": "relative/path/to/system.prmtop",
    "trajectory_path": "relative/path/to/md_prod.nc",
    "ligand_selection": "resname LIG",
    "count": True,
    "all_residues": True,
    "vicinity_cutoff": 4.5,
    "params_json": "relative/path/to/prolif_params.json"
}
```

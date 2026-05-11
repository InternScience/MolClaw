---
name: molclaw-prolif-protein-protein
description: ProLIF protein-protein trajectory analysis skill for interface interaction fingerprints and stability profiling.
license: MIT license
metadata:
    skill-author: PJLab
---

# ProLIF Protein-Protein Interface Fingerprinting Skill

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

> [!NOTE]
> Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution.
> For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.

## Task Description
Analyze protein-protein interaction trajectories and generate interface interaction fingerprints. Use this skill to evaluate interface stability and identify key residue contributions across simulation.

> **Routing note:** This tool is the **primary** choice for protein-protein trajectory interface profiling (multi-frame analysis). For **single-structure** protein-protein interface analysis, use `molclaw-interaction-visualizer` in protein mode instead — it produces interface heatmaps, network diagrams, and decision-ready JSON.

## Input Source Mapping
| Parameter | Source Guidance |
|-----------|-----------------|
| `topology_path` | System topology from MD tools: e.g., `protein_openmm_md`, `prepare_protein_md`, `goca_pipeline` |
| `trajectory_path` | Trajectory from the same MD tools, containing dynamic information for both protein chains |
| `selection_a` | User-defined selection string for protein chain A, for example `segid A` or `protein and chainid A` |
| `selection_b` | User-defined selection string for protein chain B, for example `segid B` or `protein and chainid B` |

## Usage
### Tool: `prolif_protein_protein`

```text
Analyze a protein-protein trajectory and return interaction fingerprints or counts with summary metrics.
Args:
    topology_path (str): Path to the system topology file.
    trajectory_path (str): Path to the trajectory file.
    selection_a (str): Selection string for partner A.
    selection_b (str): Selection string for partner B.
    interactions (List[str]|None): Optional interaction types to compute.
    count (bool): If True, compute interaction counts instead of fingerprints. Default: False.
    vicinity_cutoff (float|None): Optional distance cutoff for vicinity interactions.
    params_json (str|None): Optional JSON parameter file path for ProLIF interaction settings.
    start (int|None): Optional start frame index.
    stop (int|None): Optional stop frame index (exclusive).
    step (int|None): Optional frame stride.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The executed command label ('protein-protein').
    output_dir (str|None): Run-specific directory under tool_result/prolif_result.
    output_file (str|None): Path to the generated CSV file.
    n_frames (int|None): Number of processed frames.
    n_interactions (int|None): Number of interaction columns in output.
    frequent_interactions (List[dict]|None): High-frequency interactions (>30%) with keys 'interaction' and 'frequency'.
    result_summary (dict|None): Full summary dictionary from the wrapper.
```

### How To Use `prolif_protein_protein`

```python
response = await client.session.call_tool(
    "prolif_protein_protein",
    arguments={
        "topology_path": "relative/path/to/system.prmtop",
        "trajectory_path": "relative/path/to/md.nc",
        "selection_a": "segid A",
        "selection_b": "segid B",
        "start": 0,
        "step": 10
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
    "trajectory_path": "relative/path/to/md.nc",
    "selection_a": "segid A",
    "selection_b": "segid B",
    "start": 0,
    "step": 10
}

# 2) Variant mode
{
    "topology_path": "relative/path/to/system.prmtop",
    "trajectory_path": "relative/path/to/md.nc",
    "selection_a": "protein and chainid A",
    "selection_b": "protein and chainid B",
    "count": True,
    "vicinity_cutoff": 3.5,
    "stop": 200
}
```

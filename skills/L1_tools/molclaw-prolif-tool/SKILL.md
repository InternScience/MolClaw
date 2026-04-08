---
name: molclaw-prolif-tool
description: Unified ProLIF analysis skill covering MD trajectories, docking poses, single complex structures, and protein-protein interfaces.
license: MIT license
metadata:
    skill-author: PJLab
    tool-summary: |
        prolif_md: Compute interaction fingerprints from MD trajectories with frame slicing and residue controls.
        prolif_docking: Summarize docking pose sets into interaction fingerprints or counts.
        prolif_pdb: Analyze one static protein-ligand complex structure.
        prolif_protein_protein: Profile interface interactions across protein-protein trajectories.
---

# ProLIF Multi-Scenario Analysis Toolkit

> [!NOTE]
> Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution.
> For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.

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

### 2. MD Trajectory Fingerprinting
The description of tool *prolif_md*.

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

How to use tool *prolif_md* :

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

#### Example parameter sets

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

### 3. Docking Pose Fingerprinting
The description of tool *prolif_docking*.

```text
Summarize docking poses with ProLIF and return a CSV of interaction fingerprints plus summary metrics.
Args:
    protein_path (str): Path to the receptor protein structure.
    ligand_paths (List[str]): List of ligand pose files.
    ligand_format (str): Ligand format identifier (e.g., 'sdf', 'mol2', 'pdbqt').
    template_smiles (str|None): Optional template SMILES; required when ligand_format is 'pdbqt'.
    interactions (List[str]|None): Optional interaction types to compute.
    count (bool): If True, compute interaction counts instead of fingerprints. Default: False.
    vicinity_cutoff (float|None): Optional distance cutoff for vicinity interactions.
    params_json (str|None): Optional JSON parameter file path for ProLIF interaction settings.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The executed command label ('docking').
    output_dir (str|None): Run-specific directory under tool_result/prolif_result.
    output_file (str|None): Path to the produced CSV summary file.
    n_frames (int|None): Number of processed frames where applicable.
    n_interactions (int|None): Number of interaction columns in output.
    frequent_interactions (List[dict]|None): High-frequency interactions (>30%) with keys 'interaction' and 'frequency'.
    result_summary (dict|None): Full summary dictionary from the wrapper.
```

How to use tool *prolif_docking* :

```python
response = await client.session.call_tool(
    "prolif_docking",
    arguments={
        "protein_path": "relative/path/to/receptor.pdb",
        "ligand_paths": [
            "relative/path/to/pose1.sdf",
            "relative/path/to/pose2.sdf"
        ],
        "ligand_format": "sdf",
        "interactions": ["Hydrophobic", "HBDonor"]
    }
)
result = client.parse_result(response)
key_output = result["output_file"]
```

#### Example parameter sets

```python
# 1) Main mode
{
    "protein_path": "relative/path/to/receptor.pdb",
    "ligand_paths": [
        "relative/path/to/docking_poses.sdf"
    ],
    "ligand_format": "sdf"
}

# 2) Variant mode
{
    "protein_path": "relative/path/to/receptor.pdb",
    "ligand_paths": [
        "relative/path/to/pose1.pdbqt",
        "relative/path/to/pose2.pdbqt"
    ],
    "ligand_format": "pdbqt",
    "template_smiles": "CCO",
    "count": True,
    "vicinity_cutoff": 4.0
}
```

### 4. Single-Structure PDB Fingerprinting
The description of tool *prolif_pdb*.

```text
Analyze a single complex structure and return ProLIF interaction fingerprints or counts with summary metrics.
Args:
    structure_path (str): Path to the complex structure file (commonly PDB).
    ligand_selection (str): Selection string identifying ligand atoms.
    protein_selection (str): Selection string for protein atoms. Default: 'protein'.
    interactions (List[str]|None): Optional interaction types to compute.
    count (bool): If True, compute interaction counts instead of fingerprints. Default: False.
    vicinity_cutoff (float|None): Optional distance cutoff for vicinity interactions.
    params_json (str|None): Optional JSON parameter file path for ProLIF interaction settings.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The executed command label ('pdb').
    output_dir (str|None): Run-specific directory under tool_result/prolif_result.
    output_file (str|None): Path to the produced CSV file.
    n_frames (int|None): Number of processed frames (typically 1 for static structures).
    n_interactions (int|None): Number of interaction columns in output.
    frequent_interactions (List[dict]|None): High-frequency interactions (>30%) with keys 'interaction' and 'frequency'.
    result_summary (dict|None): Full summary dictionary from the wrapper.
```

How to use tool *prolif_pdb* :

```python
response = await client.session.call_tool(
    "prolif_pdb",
    arguments={
        "structure_path": "relative/path/to/complex.pdb",
        "ligand_selection": "resname LIG",
        "protein_selection": "protein",
        "interactions": ["Hydrophobic", "HBAcceptor"]
    }
)
result = client.parse_result(response)
key_output = result["output_file"]
```

#### Example parameter sets

```python
# 1) Main mode
{
    "structure_path": "relative/path/to/complex.pdb",
    "ligand_selection": "resname LIG",
    "protein_selection": "protein",
    "interactions": ["Hydrophobic", "HBDonor"]
}

# 2) Variant mode
{
    "structure_path": "relative/path/to/complex.pdb",
    "ligand_selection": "resname LIG",
    "count": True,
    "params_json": "relative/path/to/prolif_override.json"
}
```

### 5. Protein-Protein Interface Fingerprinting
The description of tool *prolif_protein_protein*.

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

How to use tool *prolif_protein_protein* :

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

#### Example parameter sets

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


---

## ⚠ Residue Numbering Warning (L3 Principle 17 — CRITICAL)

**ProLIF reports residue identifiers using the numbering of the input PDB file.** If the PDB was generated by a prediction tool (ESMFold, Boltz-2, Chai-1), these numbers are tool-internal sequential numbers (1, 2, 3...) — NOT UniProt numbers.

**Before interpreting ProLIF results when the task references specific residues (e.g., "confirm Met793 interaction"):**
1. Determine which numbering scheme the input PDB uses.
2. If different from the task's reference scheme, run `molclaw-residue-mapper` to build a mapping table.
3. Translate ProLIF residue IDs to the task's reference scheme before drawing conclusions.

**Common catastrophic error:** ProLIF reports "HBDonor at MET76" from a Boltz-2 structure. Agent searches for "MET793" in ProLIF output, does not find it, and concludes "Met793 interaction is absent." In reality, MET76 (Boltz-2 internal) IS Met793 (UniProt). **Use residue_mapper with `query="tool:76"` to verify.**

## ⚠ Mandatory Image Download (L3 Principle 15)

**After ProLIF analysis, download ALL visualization outputs** (interaction heatmaps, frequency barplots, etc.) from the output directory using `server_file_to_base64`. These are Category A files essential for result communication and user verification.


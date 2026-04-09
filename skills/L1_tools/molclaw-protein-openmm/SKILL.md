---
name: molclaw-protein-openmm
description: Run OpenMM protein MD and extract evenly spaced trajectory frames for downstream structural analysis.
license: MIT license
metadata:
    skill-author: PJLab
---

# Protein OpenMM MD and Frame Extraction

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.


## Usage


### 2. Protein OpenMM MD
The description of tool *protein_openmm_md*.

```tex
Runs OpenMM-based protein molecular dynamics preparation and simulation for structure refinement workflows.
Args:
    protein_pdb (str): Absolute or relative path to input protein PDB.
    solvent_type (str): Solvent mode, 'explicit' or 'implicit', default 'explicit'.
    gb_model (str): GB model for implicit solvent mode, default 'GBn2'.
    water_model (str): Water model for explicit solvent mode, default 'tip3p'.
    force_field (str): OpenMM force field name, default 'amber14'.
    md_time (float): Production MD time in picoseconds, default 100000.0.
    platform (str): OpenMM compute platform, default 'CUDA'.
    full_md (bool): Run full MD procedure if True, default False.
    dry_run (bool): Validate setup and produce run directory without simulation, default False.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable execution summary.
    output_dir (str): Run-specific directory under tool_result/openmm_md_result.
    work_dir (str | None): Final OpenMM working directory containing generated files.
    protein_pdb (str): Resolved input protein path.
    trajectory_path (str | None): Path to md_traj.dcd when available.
    topology_path (str | None): Path to a topology PDB used for frame extraction.
    generated_files (List[str]): File paths relative to work_dir.
    md_time (float): Echoed requested MD time in ps.
    solvent_type (str): Echoed solvent mode.
    force_field (str): Echoed force field.
    full_md (bool): Echoed full MD mode.
```

How to use tool *protein_openmm_md* :

```python
response = await client.session.call_tool(
    "protein_openmm_md",
    arguments={
        "protein_pdb": "/path/to/input.pdb",
        "solvent_type": "implicit",
        "gb_model": "OBC2",
        "water_model": "tip3p",
        "force_field": "amber14",
        "md_time": 1000.0,
        "platform": "CUDA",
        "full_md": True,
        "dry_run": False
    }
)
result = client.parse_result(response)
key_output = result["work_dir"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "protein_pdb": "/path/to/input.pdb",
    "solvent_type": "implicit",
    "gb_model": "OBC2",
    "water_model": "tip3p",
    "force_field": "amber14",
    "md_time": 1000.0,
    "platform": "CUDA",
    "full_md": True,
    "dry_run": False
}

# 2) Variant mode
{
    "protein_pdb": "relative/path/to/protein.pdb",
    "solvent_type": "explicit",
    "water_model": "tip3p",
    "force_field": "charmm36",
    "md_time": 10000.0,
    "platform": "CUDA",
    "full_md": False,
    "dry_run": False
}
```

### 3. OpenMM Trajectory Frame Extraction
The description of tool *openmm_extract_frames*.

```tex
Extracts evenly spaced protein conformations from an OpenMM work directory for downstream screening and ensemble analysis.
Args:
    work_dir (str): OpenMM MD output directory containing topology and trajectory files.
    num_frames (int): Number of evenly spaced frames to extract, default 100.
    protein_only (bool): Keep only protein atoms in extracted frames, default False.
    align (bool): Align extracted structures to the first frame, default False.
    prefix (str): Filename prefix for extracted PDB frames, default 'frame'.
    dry_run (bool): Validate inputs and prepare output directory without extraction, default False.
Return:
    status (str): 'success', 'partial_success', or 'error'.
    msg (str): Human-readable extraction summary.
    output_dir (str): Run-specific directory under tool_result/openmm_md_result.
    work_dir (str): Resolved OpenMM working directory.
    topology_path (str | None): Resolved topology file path.
    trajectory_path (str | None): Resolved trajectory file path.
    frames_dir (str): Directory where extracted frame PDB files are saved.
    frame_count (int): Number of extracted frame files.
    frame_files (List[str]): Extracted frame file paths relative to output_dir.
```

How to use tool *openmm_extract_frames* :

```python
response = await client.session.call_tool(
    "openmm_extract_frames",
    arguments={
        "work_dir": "/path/to/work_dir",
        "num_frames": 100,
        "protein_only": False,
        "align": False,
        "prefix": "frame",
        "dry_run": False
    }
)
result = client.parse_result(response)
key_output = result["frame_files"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "work_dir": "/path/to/work_dir",
    "num_frames": 100,
    "protein_only": False,
    "align": False,
    "prefix": "frame",
    "dry_run": False
}

# 2) Variant mode
{
    "work_dir": "relative/path/to/openmm_md_output",
    "num_frames": 50,
    "protein_only": True,
    "align": True,
    "prefix": "conf",
    "dry_run": False
}
```

### 4. End-to-End Collaboration Workflow
Use the two tools in sequence via API calls:
1. Call *protein_openmm_md* to generate MD outputs and get `work_dir`.
2. Pass that `work_dir` into *openmm_extract_frames* to extract evenly spaced PDB frames.

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
if not await client.connect():
    print("connection failed")
    return

md_resp = await client.session.call_tool(
    "protein_openmm_md",
    arguments={
        "protein_pdb": "/path/to/input.pdb",
        "solvent_type": "implicit",
        "gb_model": "OBC2",
        "md_time": 1000.0,
        "full_md": True
    }
)
md_result = client.parse_result(md_resp)
work_dir = md_result["work_dir"]

frames_resp = await client.session.call_tool(
    "openmm_extract_frames",
    arguments={
        "work_dir": work_dir,
        "num_frames": 100,
        "prefix": "frame"
    }
)
frames_result = client.parse_result(frames_resp)
key_output = frames_result["frame_files"]

await client.disconnect() 
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


**Specific files to download from OpenMM output directory:** trajectory files (XTC/DCD), final frame PDB/GRO, topology (PSF/TOP), energy data (EDR), and simulation log. List ALL files in the output directory and download every structure/trajectory file.

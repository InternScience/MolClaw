---
name: molclaw-openawsem-tool
description: Runs OpenAWSEM simulations and extracts representative trajectory frames for downstream ensemble analysis.
license: MIT license
metadata:
    skill-author: PJLab
---

# OpenAWSEM Simulation and Trajectory Extraction

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Usage

### 1. OpenAWSEM Simulation
The description of tool *openawsem_sim*.

```tex
Run OpenAWSEM coarse-grained protein simulation for annealing or NVT workflows in structure screening and folding studies.
Args:
  sim_dir (str|None): Simulation directory containing *-openmmawsem.pdb or *_openmmawsem.pdb, default None.
  pdb (str|None): PDB file path or PDB ID used by awsem_create when sim_dir is not provided, default None.
  steps (float): Simulation step count, default 1e5.
  mode (str): Temperature control mode in {annealing, nvt}, default annealing.
  temperature (float): NVT temperature in Kelvin passed to source script argument --temperature, default 300.0.
  platform (str): OpenMM platform in {CPU, CUDA, OpenCL}, default CPU.
  use_frag_mem (bool): Whether to use fragment memory instead of single memory, default False.
  compute_q (bool): Whether to enable Q-value related terms when available, default False.
  dry_run (bool): Whether to validate setup without running MD steps, default False.
  gpu_id (str): GPU device index for CUDA/OpenCL platform, default 0.
Return:
  status (str): success, error, or partial_success execution status.
  msg (str): Human-readable execution summary.
  output_dir (str): Unique run directory under tool_result/openawsem_result.
  simulation_dir (str): Effective simulation directory used by the delegated source script.
  steps (float): Effective step count used in this run.
  mode (str): Effective simulation mode used in this run.
  temperature (float): Effective NVT temperature used in this run.
  platform (str): Effective compute platform used in this run.
  dry_run (bool): Effective dry-run flag used in this run.
  output_files (dict): Key output file paths such as final PDB, energy log, checkpoint, and trajectory files.
  metrics (dict): Parsed summary metrics such as energy log line count and last log line when available.
```

How to use tool *openawsem_sim* :

```python
response = await client.session.call_tool(
    "openawsem_sim",
    arguments={
        "sim_dir": "/path/to/awsem_sim_dir",
        "steps": 1000,
        "mode": "annealing",
        "temperature": 300.0,
        "platform": "CUDA",
        "use_frag_mem": False,
        "compute_q": False,
        "dry_run": False,
        "gpu_id": "0"
    }
)
result = client.parse_result(response)
simulation_dir = result["simulation_dir"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "sim_dir": "/path/to/awsem_sim_dir",
    "steps": 1000,
    "mode": "annealing",
    "temperature": 300.0,
    "platform": "CUDA",
    "use_frag_mem": False,
    "compute_q": False,
    "dry_run": False,
    "gpu_id": "0"
}

# 2) Variant mode
{
    "pdb": "relative/path/to/input.pdb",
    "steps": 50000,
    "mode": "nvt",
    "temperature": 310.0,
    "platform": "CPU",
    "dry_run": True
}
```

### 2. OpenAWSEM Trajectory Frame Extraction
The description of tool *openawsem_traj_extract*.

```tex
Extracts representative structures from OpenAWSEM trajectories for downstream ensemble analysis and screening.
Args:
    sim_dir (str): OpenAWSEM simulation directory containing trajectory and topology files.
    num_frames (int): Number of evenly spaced structures to extract when times is not provided, default 100.
    times (List[float]|None): Explicit extraction time points in picoseconds, default None.
    backend (str): Trajectory backend in {mdtraj, mdanalysis, auto}, default auto.
    dry_run (bool): Validate file discovery and prepare output directory without extraction, default False.
Return:
    status (str): success, error, or partial_success execution status.
    msg (str): Human-readable extraction summary.
    output_dir (str): Unique run directory under tool_result/openawsem_result.
    extracted_dir (str): Directory containing extracted PDB frames.
    sim_dir (str): Resolved simulation directory.
    trajectory_path (str|None): Detected trajectory file path.
    topology_path (str|None): Detected topology file path.
    frame_count (int): Number of extracted frame files.
    frame_files (List[str]): Extracted PDB file paths.
    index_file (str|None): Extraction index text file path.
```

How to use tool *openawsem_traj_extract* :

```python
response = await client.session.call_tool(
    "openawsem_traj_extract",
    arguments={
        "sim_dir": "/path/to/awsem_sim_dir",
        "num_frames": 100,
        "backend": "auto",
        "dry_run": False
    }
)
result = client.parse_result(response)
frame_files = result["frame_files"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "sim_dir": "/path/to/awsem_sim_dir",
    "num_frames": 100,
    "backend": "auto",
    "dry_run": False
}

# 2) Variant mode
{
    "sim_dir": "relative/path/to/awsem_sim_dir",
    "times": [0.0, 50.0, 100.0],
    "backend": "mdtraj",
    "dry_run": True
}
```

### 3. Simulation to Extraction Workflow
Use `openawsem_sim` first, then feed its `simulation_dir` into `openawsem_traj_extract`.

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
if not await client.connect():
    print("connection failed")
    return

sim_resp = await client.session.call_tool(
    "openawsem_sim",
    arguments={
        "sim_dir": "/path/to/awsem_sim_dir",
        "steps": 1000,
        "mode": "annealing",
        "platform": "CUDA",
        "dry_run": False
    }
)
sim_result = client.parse_result(sim_resp)

extract_resp = await client.session.call_tool(
    "openawsem_traj_extract",
    arguments={
        "sim_dir": sim_result["simulation_dir"],
        "num_frames": 100,
        "backend": "auto",
        "dry_run": False
    }
)
extract_result = client.parse_result(extract_resp)
frame_files = extract_result["frame_files"]

await client.disconnect()
```

---
name: molclaw-equiscore-tool
description: Unified EquiScore skill for pocket extraction, pocket scoring, and end-to-end docking-to-score pipeline execution.
license: MIT license
metadata:
    skill-author: PJLab
    tool-summary: |
        equiscore_pocket: Extract pockets and split ligand poses from docking outputs.
        equiscore_screen: Score extracted pockets with EquiScore and return ranking statistics.
        equiscore_pipeline: Run one-click pocket extraction plus scoring from docking results.
---

# EquiScore Multi-Tool Workflow

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

> [!NOTE]
> Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution.
> For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.

## Usage

### 1. Pocket Extraction
The description of tool *equiscore_pocket*.

```text
Extract binding pockets from docking results and prepare split single-molecule SDFs for EquiScore screening.
Args:
    docking_result (str): Path to a docking-result SDF file.
    receptor_pdb (str): Path to the receptor PDB file.
    pocket_cutoff (float|None): Optional numeric cutoff for pocket detection.
    dry_run (bool|None): If True, validate inputs and prepare outputs without executing EquiScore.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The subcommand executed ('get_pocket').
    run_dir (str|None): Run-specific directory under tool_result/equiscore_result.
    single_sdf_dir (str|None): Path to directory containing split single-molecule SDFs.
    pocket_dir (str|None): Path to the generated pocket folder.
    split_sdf_count (int|None): Number of split SDF files created.
    pocket_item_count (int|None): Number of pocket entries generated.
    sample_single_sdfs (List[str]|None): Sample single-SDF filenames.
    sample_pockets (List[str]|None): Sample pocket directory names.
```

How to use tool *equiscore_pocket* :

```python
response = await client.session.call_tool(
    "equiscore_pocket",
    arguments={
        "docking_result": "relative/path/to/docking_result.sdf",
        "receptor_pdb": "relative/path/to/receptor.pdb",
        "pocket_cutoff": 10.0,
        "dry_run": True
    }
)
result = client.parse_result(response)
key_output = result["single_sdf_dir"]
```

#### Example parameter sets

```python
# 1) Main mode
{
    "docking_result": "relative/path/to/docking_result.sdf",
    "receptor_pdb": "relative/path/to/receptor.pdb",
    "pocket_cutoff": None,
    "dry_run": False
}

# 2) Variant mode
{
    "docking_result": "relative/path/to/docking_result.sdf",
    "receptor_pdb": "relative/path/to/receptor.pdb",
    "pocket_cutoff": 8.5,
    "dry_run": True
}
```

### 2. Pocket Screening
The description of tool *equiscore_screen*.

```text
Score a pocket library with EquiScore and return prediction CSV plus summary statistics.
Args:
    pocket_dir (str): Path to a pocket directory produced by `equiscore_pocket`.
    ngpu (int): Number of GPUs to use. Default: 1.
    batch_size (int): Inference batch size. Default: 128.
    num_workers (int): Number of worker processes for data loading. Default: 8.
    weight_path (str|None): Optional path to model weights.
    multi_pose (bool): If True, score multiple poses per ligand.
    pose_num (int): Number of poses to evaluate when `multi_pose` is True. Default: 1.
    debug (bool): Enable debug mode.
    dry_run (bool|None): If True, validate inputs without running EquiScore.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The subcommand executed ('screen').
    run_dir (str|None): Run-specific directory under tool_result/equiscore_result.
    output_dir (str|None): Directory where screening outputs were written.
    predictions_path (str|None): Path to the CSV file with raw predictions.
    prediction_count (int|None): Number of prediction rows in the CSV.
    score_field (str|None): CSV column used for scoring, if detected.
    max_score (float|None): Maximum observed score.
    min_score (float|None): Minimum observed score.
    mean_score (float|None): Mean score.
    median_score (float|None): Median score.
```

#### Scoring Interpretation (EquiScore)

- EquiScore is trained as a classifier (`active=1`, `decoy=0`), so `0.5` can be used as a rough reference boundary.
- In practical virtual screening, absolute thresholding is less robust than ranking.
- Recommended usage:
    - Sort predictions by score column (commonly `test_pred`) in descending order.
    - Select top N or top N% compounds for downstream validation.
    - Typical settings include top 1% for enrichment-style filtering or top 50-200 molecules for follow-up.
- For higher confidence, combine EquiScore ranking with another docking/scoring method for consensus prioritization.

How to use tool *equiscore_screen* :

```python
response = await client.session.call_tool(
    "equiscore_screen",
    arguments={
        "pocket_dir": "relative/path/to/pockets",
        "ngpu": 1,
        "batch_size": 128,
        "num_workers": 8,
        "multi_pose": False,
        "pose_num": 1,
        "debug": False,
        "dry_run": False
    }
)
result = client.parse_result(response)
key_output = result["predictions_path"]
```

#### Example parameter sets

```python
# 1) Main mode
{
    "pocket_dir": "relative/path/to/pockets",
    "ngpu": 1,
    "batch_size": 128,
    "num_workers": 8,
    "multi_pose": False,
    "pose_num": 1,
    "debug": False,
    "dry_run": False
}

# 2) Variant mode
{
    "pocket_dir": "relative/path/to/pockets",
    "ngpu": 2,
    "weight_path": "relative/path/to/custom_equiscore.pt",
    "multi_pose": True,
    "pose_num": 5,
    "debug": False,
    "dry_run": False
}
```

### 3. End-to-End Pipeline
The description of tool *equiscore_pipeline*.

```text
Run one-click EquiScore workflow for pocket extraction and screening from docking output.
Args:
    docking_result (str): Path to a docking-result SDF file.
    receptor_pdb (str): Path to receptor PDB file.
    ngpu (int): Number of GPUs for the screening stage. Default: 1.
    weight_path (str|None): Optional path to a custom EquiScore model checkpoint.
    multi_pose (bool): Enable multi-pose scoring mode.
    pose_num (int): Number of poses to evaluate when `multi_pose` is True. Default: 1.
    dry_run (bool|None): Validate inputs and print command flow without launching EquiScore.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The subcommand executed ('pipeline').
    run_dir (str|None): Run-specific directory under tool_result/equiscore_result.
    work_dir (str|None): Pipeline working directory holding intermediate files.
    single_sdf_dir (str|None): Directory containing the split single-molecule SDFs.
    pocket_dir (str|None): Directory containing extracted pocket data.
    predictions_path (str|None): Path to the final EquiScore prediction CSV.
    split_sdf_count (int|None): Number of split SDF files produced.
    pocket_item_count (int|None): Number of pocket entries generated during extraction.
    prediction_count (int|None): Number of rows in the prediction CSV.
    score_field (str|None): CSV column used as the score.
    max_score (float|None): Maximum score.
    min_score (float|None): Minimum score.
    mean_score (float|None): Mean score.
    median_score (float|None): Median score.
```

How to use tool *equiscore_pipeline* :

```python
response = await client.session.call_tool(
    "equiscore_pipeline",
    arguments={
        "docking_result": "relative/path/to/docking_result.sdf",
        "receptor_pdb": "relative/path/to/receptor.pdb",
        "ngpu": 1,
        "multi_pose": False,
        "pose_num": 1,
        "dry_run": False
    }
)
result = client.parse_result(response)
key_output = result["predictions_path"]
```

#### Example parameter sets

```python
# 1) Main mode
{
    "docking_result": "relative/path/to/docking_result.sdf",
    "receptor_pdb": "relative/path/to/receptor.pdb",
    "ngpu": 1,
    "multi_pose": False,
    "pose_num": 1,
    "dry_run": False
}

# 2) Variant mode
{
    "docking_result": "relative/path/to/docking_result.sdf",
    "receptor_pdb": "relative/path/to/receptor.pdb",
    "ngpu": 2,
    "weight_path": "relative/path/to/custom_equiscore.pt",
    "multi_pose": True,
    "pose_num": 5,
    "dry_run": False
}
```

---
name: molclaw-karmadock-tool
description: Run KarmaDock graph generation and virtual screening to produce ranked ligand poses and summary metrics.
license: MIT license
metadata:
    skill-author: PJLab
---

# KarmaDock Virtual Screening

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Usage

### 1. KarmaDock Virtual Screening

The description of tool *karmadock_tool*.

```tex
Performs protein-ligand virtual screening with KarmaDock for batch ranking and optional pose export workflows.
Args:
    ligand_smi (str): Ligand SMILES input file path, required.
    protein_file (str): Protein PDB file path, required.
    crystal_ligand_file (str): Crystal ligand MOL2 file for pocket localization, required.
    score_threshold (float): Score threshold used for pose export mask, default 70.0.
    batch_size (int): Inference batch size, default 64.
    random_seed (int): Random seed for reproducibility, default 2020.
    dry_run (bool): Validate inputs and create tracked output directory without execution, default False.
Return:
    status (str): success, partial_success, or error execution status.
    msg (str): Human-readable execution summary.
    output_dir (str): Run-specific directory under tool_result/karmadock_tool_result.
    ligand_smi (str): Resolved ligand SMILES file absolute path.
    protein_file (str): Resolved protein PDB file absolute path.
    crystal_ligand_file (str): Resolved crystal ligand MOL2 absolute path.
    score_threshold (float): Effective score threshold used in this run.
    batch_size (int): Effective batch size used.
    random_seed (int): Effective random seed used.
    out_init (bool): Always True in wrapper.
    out_uncorrected (bool): Always True in wrapper.
    out_corrected (bool): Always True in wrapper.
    dry_run (bool): Effective dry-run flag.
    return_code (int | None): Delegated process return code.
    pose_export_hint (str | None): Diagnostic message when SDF export is requested but missing.
    key_files (dict): Key output files including score_csv and pose_sdf_files.
    metrics (dict): Summary metrics including num_ligands_scored and karma score extrema.
```

#### Scoring Interpretation (KarmaDock)

- `score.csv` columns:
    - `pdb_id`: ligand identifier from input library (or dataset complex ID).
    - `karma_score`: direct KarmaDock score from the MDN-based scoring head.
    - `karma_score_ff`: score after MMFF94 force-field corrected pose.
    - `karma_score_aligned`: score after RDKit-aligned corrected pose.
- Direction: all KarmaDock scores are interpreted as higher-is-better in ranking workflows.
- Practical readout:
    - Prefer candidates with consistently high values across `karma_score`, `karma_score_ff`, and `karma_score_aligned`.
    - If `karma_score` is high but corrected scores drop strongly, pose stability/reliability is weaker and should be down-weighted.
- Threshold usage:
    - `score_threshold` is a practical filtering knob and should be tuned per target/library distribution.
    - Common practice is to rank by score and select top N or top N%, instead of relying on one fixed threshold.
- Limitation note:
    - KarmaDock is efficient for large-scale prescreening, but pose physical validity can still require downstream docking/MD validation.

How to use tool *karmadock_tool* :

```python
response = await client.session.call_tool(
    "karmadock_tool",
    arguments={
        "ligand_smi": "/path/to/ligands.smi",
        "protein_file": "/path/to/protein.pdb",
        "crystal_ligand_file": "/path/to/crystal_ligand.mol2",
        "score_threshold": 70.0,
        "batch_size": 64
    }
)
result = client.parse_result(response)
key_output = result["output_dir"]

```

#### Example parameter sets

```python
# 1) Main mode: dry run check
{
    "ligand_smi": "/path/to/ligands.smi",
    "protein_file": "/path/to/protein.pdb",
    "crystal_ligand_file": "/path/to/crystal_ligand.mol2",
    "score_threshold": 70.0,
    "batch_size": 64,
    "random_seed": 2020,
    "dry_run": True
}

# 2) Variant mode: real run with stricter threshold
{
    "ligand_smi": "/path/to/ligands.smi",
    "protein_file": "/path/to/protein.pdb",
    "crystal_ligand_file": "/path/to/crystal_ligand.mol2",
    "score_threshold": 50.0,
    "batch_size": 64,
    "random_seed": 2023,
    "dry_run": False
}
```

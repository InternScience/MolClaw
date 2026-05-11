---
name: molclaw-chai1-predict
description: Predict protein structures with Chai-1 from sequence or FASTA input and return model scoring summaries.
license: MIT license
metadata:
    skill-author: PJLab
---

# Chai-1 Protein Structure Prediction

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Usage

### 1. Chai-1 Prediction (Sequence/FASTA)

The description of tool *chai1_predict*.

```tex
Predict protein structures with Chai-1 from sequence or FASTA input, run inference (unless dry-run), and return per-model scoring summaries for downstream selection.
Args:
    mode (str): One of 'sequence', 'fasta', or 'info'; API also accepts 'predict' as an alias of 'sequence'.
    seq (str|None): Comma-separated protein sequence(s) for sequence mode, e.g., "MKFL...,AIQR...".
    name (str|None): Comma-separated chain names corresponding to `seq`; defaults to chain_1, chain_2, ... if omitted.
    fasta_path (str|None): Path to an input FASTA file for fasta mode.
    samples (int): Number of models/samples to generate, must be >= 1. Default: 5.
    dry_run (bool): If True, only prepare inputs and write `input.fasta` without running Chai-1 inference.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    output_dir (str|None): Run artifact directory path.
    model_scores (List[dict]|None): Per-model summaries with keys 'model_idx', 'cif_path', 'scores', and 'score_path'.
    best_model (dict|None): Top model summary with keys 'model_idx', 'aggregate_score', and 'cif_path'.
```

How to use tool *chai1_predict* :

```python
response = await client.session.call_tool(
    "chai1_predict",
    arguments={
        "mode": "sequence",
        "seq": "MKFLILLFNILCLFPVLAADNHGVS",
        "name": "my_protein",
        "samples": 5,
        "dry_run": True
    }
)
result = client.parse_result(response)
best_model = result["best_model"]

```

#### Example parameter sets

```python
# 1) Sequence mode (README/tool_factory validated; main mode)
{
    "mode": "predict",  # alias of sequence
    "seq": "MKFLILLFNILCLFPVLAADNHGVS",
    "name": "my_protein",
    "dry_run": True
}

# 2) FASTA mode (wrapper/API supported variant mode)
{
    "mode": "fasta",
    "fasta_path": "/abs/path/input.fasta",
    "samples": 5,
    "dry_run": True
}

# 3) Info mode (source code run_chai1 behavior)
{
    "mode": "info"
}
```

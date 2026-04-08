---
name: molclaw-chai1-predict
description: Predict protein structures with Chai-1 from sequence or FASTA input and return model scoring summaries.
license: MIT license
metadata:
    skill-author: PJLab
---

# Chai-1 Protein Structure Prediction

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.


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

### 2. Chai-1 Prediction (Sequence/FASTA)

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


## ⚠ Confidence Metric Checkpoint (L3 Principle 12 Checkpoint A)

After Chai-1 prediction, check confidence metrics:
- **pTM > 0.5:** Reasonable fold prediction
- **ipTM > 0.4:** Complex prediction may be meaningful. ipTM < 0.4 suggests unreliable complex interface.
- **pLDDT < 60:** Unreliable prediction — flag in report

## ⚠ Numbering Scheme (L3 Principle 17)

Chai-1 predicted structures use **1-based sequential numbering** from the input sequence — NOT UniProt numbering. If downstream analysis (ProLIF, per-residue decomposition) references specific residues, apply `molclaw-residue-mapper` first.

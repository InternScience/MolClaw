---
name: molclaw-pack-sidechains
description: Predicts full-atom sidechain conformations from backbone PDBs using AttnPacker for structure preparation workflows.
license: MIT license
metadata:
    skill-author: PJLab
---

# AttnPacker Sidechain Packing

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

### 2. Protein Sidechain Packing
The description of tool *pack_sidechains*.

```tex
Predict full-atom sidechain conformations from backbone PDBs for protein structure preparation workflows.
Args:
  input_pdb (str): Input PDB file path, required.
  device (str|None): Compute device such as cuda:0, default None (auto by source script).
  chunk_size (int): Inference chunk size for long proteins, default 500.
  no_post_process (bool): Skip rotamer post-processing for faster runtime, default False.
  max_optim_iters (int): Maximum optimization iterations in post-process, default 250.
  steric_wt (float): Steric clash penalty weight, default 1.0.
  optim_repeats (int): Post-process optimization repeats, default 2.
  dry_run (bool): Create a traceable run directory without running inference, default False.
Return:
  status (str): 'success', 'error', or 'partial_success'.
  msg (str): Human-readable execution message.
  input_pdb (str): Input PDB path used for this run.
  output_dir (str): Unique run directory under tool_result/pack_sidechains_result.
  output_pdb (str): Expected or generated output PDB path.
  device (str|None): Device value used for execution.
  chunk_size (int): Chunk size used.
  no_post_process (bool): Whether post-process was skipped.
  max_optim_iters (int): Max optimization iterations used.
  steric_wt (float): Steric weight used.
  optim_repeats (int): Optimization repeats used.
  dry_run (bool): Whether dry-run mode was used.
  error_type (str, optional): Exception type when status is 'error'.
  traceback (str, optional): Python traceback when status is 'error'.
```

How to use tool *pack_sidechains* :

```python
response = await client.session.call_tool(
    "pack_sidechains",
    arguments={
        "input_pdb": "/path/to/input.pdb",
        "device": "cuda:0",
        "chunk_size": 500,
        "no_post_process": False,
        "max_optim_iters": 250,
        "steric_wt": 1.0,
        "optim_repeats": 2,
        "dry_run": False
    }
)
result = client.parse_result(response)
output_pdb = result["output_pdb"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "input_pdb": "/path/to/input.pdb",
    "device": "cuda:0",
    "chunk_size": 500,
    "no_post_process": False,
    "max_optim_iters": 250,
    "steric_wt": 1.0,
    "optim_repeats": 2,
    "dry_run": False
}

# 2) Variant mode
{
    "input_pdb": "relative/path/to/test_backbone.pdb",
    "chunk_size": 500,
    "dry_run": True
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


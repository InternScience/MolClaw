---
name: molclaw-goca-tool
description: Run GoCa coarse-grained protein MD pipeline and collect key simulation artifacts from a unified run directory.
license: MIT license
metadata:
    skill-author: PJLab
---

# GoCa Pipeline

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.
- GoCa executable path is fixed by wrapper to `/root/lwj/wll/code/drug/GoCa/GoCa`.


## Usage


### 2. GoCa Pipeline
The description of tool *goca_pipeline*.

```tex
Runs GoCa coarse-grained setup and optional full MD workflow for protein structure relaxation and trajectory generation.
Args:
    protein_pdb (str): Input protein PDB path, required.
    full_md (bool): Whether to run EM, production MD, and post-processing, default True.
    temperature (float): GoCa reduced temperature used for MD, default 45.0.
    md_time (float): MD simulation length in ps, default 12000.0.
    gpu_ids (str | None): Optional GROMACS GPU device IDs, default None.
    dry_run (bool): Create tracked run directory and return normalized parameters without execution, default False.
Return:
    status (str): success, partial_success, or error.
    msg (str): Human-readable run summary.
    output_dir (str): Run-specific directory under tool_result/goca_pipeline_result.
    work_dir (str): Relative GoCa working directory under output_dir.
    protein_pdb (str): Resolved input protein PDB absolute path.
    full_md (bool): Effective full_md value used by wrapper.
    temperature (float): Effective reduced temperature used by wrapper.
    md_time (float): Effective MD time in ps used by wrapper.
    gpu_ids (str | None): Effective GPU IDs used by wrapper.
    dry_run (bool): Effective dry_run value used by wrapper.
    key_files (dict): Key output files relative to output_dir.
    analysis_dir (str | None): Analysis directory relative to output_dir when generated.
```

How to use tool *goca_pipeline* :

```python
response = await client.session.call_tool(
    "goca_pipeline",
    arguments={
        "protein_pdb": "/path/to/input.pdb",
        "full_md": True,
        "md_time": 1000.0,
        "temperature": 45.0,
        "gpu_ids": None,
        "dry_run": False
    }
)
result = client.parse_result(response)
key_output = result["output_dir"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "protein_pdb": "/path/to/input.pdb",
    "full_md": True,
    "md_time": 1000.0,
    "temperature": 45.0,
    "gpu_ids": None,
    "dry_run": True
}

# 2) Variant mode
{
    "protein_pdb": "relative/path/to/protein.pdb",
    "full_md": False,
    "md_time": 50000.0,
    "temperature": 50.0,
    "gpu_ids": "0",
    "dry_run": False
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


**Specific files to download from GoCa output:** All Cα trajectory PDB files, output configuration files. These are coarse-grained structures that will need full-atom reconstruction via `molclaw-pulchura-rebuild` and `molclaw-pack-sidechains`.

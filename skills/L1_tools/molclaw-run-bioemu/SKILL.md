---
name: molclaw-run-bioemu
description: Run BioEmu sequence sampling and extract ensemble structures for downstream conformation analysis.
license: MIT license
metadata:
    skill-author: PJLab
---

# BioEmu Sampling and Structure Extraction

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.

## Usage


### 2. BioEmu Sampling

The description of tool *run_bioemu*.

```tex
Generate BioEmu conformational samples for a sequence, store outputs under the shared result root, and return run metadata and key artifacts.
Args:
    sequence (str): Input sequence string or a path (FASTA/A3M) readable by BioEmu.
    num_samples (int): Number of conformational samples to generate.
    export_pdbs (bool): If True, export individual PDB files for each sample (default False).
    dry_run (bool): If True, validate inputs and create run directory without executing BioEmu.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The invoked command ('run_bioemu').
    run_dir (str|None): Path to the run-specific output directory under tool_result/bioemu_result.
    output_dir (str|None): Same as `run_dir` for compatibility.
    files (List[str]|None): Sorted list of generated files under the run directory.
    pdb_path (str|None): First detected PDB file path if present.
    xtc_path (str|None): First detected XTC file path if present.
    sampling_statistics (dict|None): Parsed sampling statistics if available.
    sampling_statistics_path (str|None): Path to sampling_statistics.json if present.
    sequence_input (str|None): Resolved sequence or input path echoed by BioEmu.
    num_samples_requested (int|None): Number of requested samples echoed back.
    export_pdbs (bool|None): Whether PDB export was requested.
```

How to use tool *run_bioemu* :

```python
response = await client.session.call_tool(
    "run_bioemu",
    arguments={
        "sequence": "GYDPETGTWG",
        "num_samples": 5,
        "export_pdbs": False,
        "dry_run": True
    }
)
result = client.parse_result(response)
key_output = result["run_dir"]

```

#### Example parameter sets

```python
# 1) Main mode: short sampling from sequence string
{
    "sequence": "GYDPETGTWG",
    "num_samples": 5,
    "export_pdbs": False,
    "dry_run": False
}

# 2) Variant mode: FASTA file input with PDB export
{
    "sequence": "relative/path/to/sequence.fasta",
    "num_samples": 200,
    "export_pdbs": True,
    "dry_run": False
}
```

### 3. BioEmu Structure Extraction

The description of tool *extract_bioemu_structures*.

```tex
Extracts per-conformation structures and ensemble metadata from a BioEmu output directory for post-processing workflows.
Args:
    input_dir (str): BioEmu output directory containing topology PDB and XTC trajectory.
    prefix (str): Prefix for individual PDB filenames, default 'conf'.
    merge_pdb (bool): Export merged multi-model PDB, default False.
    extract_npz (bool): Extract NPZ payload data when present, default False.
    no_individual_pdbs (bool): Skip individual PDB exports, default False.
    no_stats (bool): Skip ensemble statistics computation, default False.
    sidechain_relax (bool): Run sidechain relaxation step, default False.
    dry_run (bool): Validate input and prepare output directory without extraction, default False.
Return:
    status (str): 'success', 'partial_success', or 'error'.
    msg (str): Human-readable extraction summary.
    output_dir (str): Run-specific directory under tool_result/bioemu_result.
    input_dir (str): Resolved BioEmu input directory.
    pdb_path (str | None): Resolved topology PDB path.
    xtc_path (str | None): Resolved trajectory XTC path.
    individual_pdb_dir (str): Directory for individual extracted PDB files.
    merged_pdb_path (str | None): Path to merged PDB file if requested.
    ensemble_statistics_path (str | None): Path to ensemble statistics JSON when generated.
    files (List[str]): Generated file paths relative to output_dir (e.g., 'individual_pdbs/conf_0000.pdb').
    exported_individual_count (int): Number of individual PDB files exported.
    stats_available (bool): Whether statistics were generated.
```

How to use tool *extract_bioemu_structures* :

```python
response = await client.session.call_tool(
    "extract_bioemu_structures",
    arguments={
        "input_dir": "/path/to/bioemu_run_dir",
        "prefix": "conf",
        "merge_pdb": False,
        "extract_npz": False,
        "no_individual_pdbs": False,
        "no_stats": False,
        "sidechain_relax": False,
        "dry_run": False
    }
)
result = client.parse_result(response)
key_output = result["individual_pdb_dir"]

```

#### Example parameter sets

```python
# 1) Main mode: extract individual PDBs + stats
{
    "input_dir": "/path/to/bioemu_run_dir",
    "prefix": "conf",
    "merge_pdb": False,
    "extract_npz": False,
    "no_individual_pdbs": False,
    "no_stats": False,
    "sidechain_relax": False,
    "dry_run": False
}

# 2) Variant mode: merged PDB + NPZ extraction
{
    "input_dir": "relative/path/to/bioemu_output",
    "prefix": "sample",
    "merge_pdb": True,
    "extract_npz": True,
    "no_individual_pdbs": True,
    "no_stats": False,
    "sidechain_relax": False,
    "dry_run": False
}
```

### 4. End-to-End Collaboration Workflow

Use the two tools in sequence via API calls:
1. Call *run_bioemu* to produce sampling outputs and get `run_dir`.
2. Pass that `run_dir` to *extract_bioemu_structures* for per-frame structure extraction.

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
if not await client.connect():
    print("connection failed")
    return

run_resp = await client.session.call_tool(
    "run_bioemu",
    arguments={
        "sequence": "GYDPETGTWG",
        "num_samples": 5,
        "export_pdbs": False,
        "dry_run": False
    }
)
run_result = client.parse_result(run_resp)
bioemu_run_dir = run_result["run_dir"]

extract_resp = await client.session.call_tool(
    "extract_bioemu_structures",
    arguments={
        "input_dir": bioemu_run_dir,
        "prefix": "conf",
        "merge_pdb": False,
        "extract_npz": False,
        "no_individual_pdbs": False,
        "no_stats": False,
        "sidechain_relax": False,
        "dry_run": False
    }
)
extract_result = client.parse_result(extract_resp)
key_output = extract_result["files"]

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


**Specific files to download from BioEmu output:** All sampled PDB structures in the ensemble. Verify the count of downloaded structures matches the requested `num_samples` (L3 Principle 11).

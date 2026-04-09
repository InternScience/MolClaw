---
name: reference_analyze_mmpbsa
description: Reference doc for the MCP `analyze_mmpbsa` call used by the Protein-Ligand MM/PBSA workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# analyze_mmpbsa Reference

## Usage


### 2. Scenario Description

Reads the MM/PBSA workspace from `run_mmpbsa`, auto-detects CSV files, and emits plots/reports so analysts can interpret the binding energy distributions.

Args:
- `work_dir` (str): Workspace produced by `prepare_complex` and `run_mmpbsa` (required).

Returns:
- `status` (str): `'success'` or `'error'`.
- `msg` (str): Run summary or failure explanation.
- `work_dir` (str): Echoes the input workspace.
- `output_dir` (str): Reports directory (typically `work_dir/results`).
- `detected_mode` (str): One of `'dual'`, `'single_pb'`, `'single_gb'`, or `'none'`.
- `detected_inputs` (Dict[str, str | None]): Auto-detected CSV paths.
- `missing_files` (List[str]): Files that were expected but not found.
- `command` (str): Executed analyzer command line.
- `files`, `reports` (Dict[str, str | None]): Generated artifact paths (CSV, PNG, MD).

### 3. How to use tool `analyze_mmpbsa`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "analyze_mmpbsa",
    arguments={
        "work_dir": "complex_workspace",
    },
)
result = DrugSDAClient.parse_result(response)
await client.disconnect()
```

#### Example parameter sets
1. **Default report generation**

```python
{
    "work_dir": "complex_workspace",
}
```

2. **Variant workspace**

```python
{
    "work_dir": "complex_workspace_alt",
}
```

Key outputs: `reports` and `files` capture the generated PNGs/CSVs that can populate the final workflow summary, while `detected_mode` indicates whether PB/GB runs were found.

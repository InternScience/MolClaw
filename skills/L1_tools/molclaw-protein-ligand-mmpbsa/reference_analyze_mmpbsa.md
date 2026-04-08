---
name: reference_analyze_mmpbsa
description: Reference doc for the MCP `analyze_mmpbsa` call used by the Protein-Ligand MM/PBSA workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# analyze_mmpbsa Reference

## Usage

### 1. MCP Server Definition

```python
import json
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

class DrugSDAClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.session = None

    async def connect(self):
        self.transport = streamablehttp_client(url=self.server_url)
        self.read, self.write, self.get_session_id = await self.transport.__aenter__()
        self.session_ctx = ClientSession(self.read, self.write)
        self.session = await self.session_ctx.__aenter__()
        await self.session.initialize()

    async def disconnect(self):
        if self.session:
            await self.session_ctx.__aexit__(None, None, None)
        if hasattr(self, "transport"):
            await self.transport.__aexit__(None, None, None)

    @staticmethod
    def parse_result(result):
        if hasattr(result, "content") and result.content and hasattr(result.content[0], "text"):
            return json.loads(result.content[0].text)
        return result
```

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

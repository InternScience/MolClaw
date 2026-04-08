---
name: reference_run_mmpbsa
description: Reference doc for the MCP `run_mmpbsa` call used by the Protein-Ligand MM/PBSA workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# run_mmpbsa Reference

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

Executes gmx_MMPBSA on the prepared workspace; writes GB/PB CSVs and returns parsed energy summaries for the workflow.

Args:
- `work_dir` (str): Workspace from `prepare_complex` containing em.gro, md.xtc, md.tpr, topol.top, ligand files (required).
- `method` (str): Select `'gb'`, `'pb'`, or `'both'` (default: `'both'`).
- `nproc` (int | str): MPI process count (default: 32).
- `interval` (int): Frame sampling interval (default: 1).
- `startframe`, `endframe` (int): Frame range (defaults: 1 and large upper bound to cover all frames).
- `generate_input` (bool): Auto-create `mmpbsa.in` (default: True).
- `dry_run` (bool): Validate inputs without running the analysis (default: False).

Returns:
- `status` (str): `'success'` or `'error'`.
- `msg` (str): Execution narrative or failure detail.
- `work_dir` (str): Echoes the input workspace.
- `output_dir` (str): Directory where results are written.
- `command` (str | None): Executed gmx_MMPBSA command (absent on dry runs).
- `gb_dir`, `pb_dir` (str | None): Output folders (e.g., `work_dir/mmgbsa`, `work_dir/mmpbsa`).
- `results` (Dict[str, Any]): Parsed energies from FINAL_RESULTS/FINAL_DECOMP.

### 3. How to use tool `run_mmpbsa`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "run_mmpbsa",
    arguments={
        "work_dir": "complex_workspace",
        "method": "both",
        "nproc": 32,
        "generate_input": True,
        "interval": 1,
    },
)
result = DrugSDAClient.parse_result(response)
await client.disconnect()
```

#### Example parameter sets
1. **GB+PB default run**

```python
{
    "work_dir": "complex_workspace",
    "method": "both",
    "nproc": 32,
    "generate_input": True,
    "interval": 1,
}
```

2. **PB-only quick pass**

```python
{
    "work_dir": "complex_workspace",
    "method": "pb",
    "nproc": 16,
    "generate_input": False,
    "interval": 1,
}
```

Key outputs: `results` provides final MM/GB(PB) energies and `pb_dir`/`gb_dir` contain the expected CSV artifacts referenced by the workflow.

---
name: reference_gmx_mmpbsa_propro
description: Tool reference for the MCP `gmx_mmpbsa_propro` call that calculates protein-protein free energy.
license: MIT license
metadata:
    skill-author: PJLab
---

# gmx_mmpbsa_propro Reference

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

Run `gmx_MMPBSA_propro` inside the prepared protein-only MD directory to compute GB, PB, or both binding energies.

Args:
- `work_dir` (str): `prepare_protein_md.run_dir` containing `em.gro`, `md.xtc`, `md.tpr`, `topol.top`, etc. (required).
- `method` (str): Calculation mode, one of `['gb', 'pb', 'both']` (default: `'gb'`).
- `nproc` (int | str): MPI process count (default: 16).
- `skip_mmpbsa` (bool): If True, only builds the index file (default: False).
- `gro` (str | None): Optional override for the GRO file path (default: None).
- `dry_run` (bool): Validate inputs without executing the full calculation (default: False).

Return:
- `status` (str): `'success'`, `'error'`, or `'partial_success'`.
- `msg` (str): Summary or error message.
- `output_dir` (str): Result directory under `tool_result/gmx_mmpbsa_propro_result`.
- `work_dir` (str): Resolved absolute path of the input workspace.
- `method` (str): Effective calculation method.
- `nproc` (int): Effective process count.
- `skip_mmpbsa` (bool): Effective flag used.
- `dry_run` (bool): Effective flag used.
- `resolved_inputs` (dict): Absolute paths selected for inputs.
- `output_files` (dict): Key output paths (index files, `gb_result_csv`, `pb_result_csv`).
- `metrics` (dict): Parsed binding energy metrics (e.g., DELTA G values).

### 3. How to use tool `gmx_mmpbsa_propro`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "gmx_mmpbsa_propro",
    arguments={
        "work_dir": "Protein_MD_01",
        "method": "gb",
        "nproc": 32,
        "skip_mmpbsa": False,
        "dry_run": False,
    },
)
result = DrugSDAClient.parse_result(response)
await client.disconnect()
```

#### Example parameter sets

1. **Production GB run** (matching `python gmx_mmpbsa_propro.py -g em.gro --method gb --nproc 64` documented in the CLI guide)

```python
{
    "work_dir": "Protein_MD_01",
    "method": "gb",
    "nproc": 64,
    "skip_mmpbsa": False,
}
```

2. **Dual-mode variant** (inspired by the `gmx_mmpbsa_propro` validations with both modes enabled)

```python
{
    "work_dir": "Protein_MD_02",
    "method": "both",
    "nproc": 32,
    "skip_mmpbsa": False,
}
```

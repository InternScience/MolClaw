---
name: reference_prepare_complex
description: Reference doc for the MCP `prepare_complex` call used by the Protein-Ligand MM/PBSA workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# prepare_complex Reference

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

Builds the MD-ready complex for MM/PBSA runs so that downstream `run_mmpbsa` can rely on a structured workspace.

Args:
- `protein` (str): Path to the cleaned receptor PDB (required).
- `ligand` (str): Ligand file (`sdf`, `mol2`, `pdbqt`, or `pdb`) (required).
- `pose` (int): Pose index inside the ligand file (default: 1).
- `gpu_ids` (str | None): Comma-separated GPU IDs (default: "0").
- `full_md` (bool): Run the full minimization/equilibration/production MD pipeline (default: True).
- `nvt_time`, `npt_time`, `md_time` (float): Equilibration/production durations in picoseconds (defaults 1.0, 1.0, 100.0).
- `ph` (float | None): Optional pH override for protonation modeling.

Returns:
- `status` (str): `'success'` or `'error'`.
- `msg` (str): Summary or failure details.
- `run_dir` (str): Timestamped run directory under `tool_result/gmx_mmpbsa_result`.
- `output_dir` (str): Complex workspace containing MD artifacts.
- `files` (List[str] | None): Enumerated files produced in `output_dir` (e.g., `em.gro`, `md.xtc`).

### 3. How to use tool `prepare_complex`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "prepare_complex",
    arguments={
        "protein": "fixed_protein.pdb",
        "ligand": "ligand.sdf",
        "pose": 1,
        "gpu_ids": "0",
        "full_md": True,
        "nvt_time": 1.0,
        "npt_time": 1.0,
        "md_time": 100.0,
    },
)
result = DrugSDAClient.parse_result(response)
complex_dir = result.get("output_dir")
await client.disconnect()
```

#### Example parameter sets
1. **Full MD workspace (mirrors gmxMMPBSA scripts default)**

```python
{
    "protein": "fixed_protein.pdb",
    "ligand": "ligand.sdf",
    "pose": 1,
    "gpu_ids": "0",
    "full_md": True,
    "nvt_time": 1.0,
    "npt_time": 1.0,
    "md_time": 100.0,
}
```

2. **Variant with extended GPU/PH controls**

```python
{
    "protein": "fixed_protein.pdb",
    "ligand": "ligand.pdb",
    "pose": 1,
    "gpu_ids": "0,1",
    "full_md": True,
    "nvt_time": 2.0,
    "npt_time": 2.0,
    "md_time": 120.0,
    "ph": 6.5,
}
```

Key output for the workflow: `output_dir` feeds both `run_mmpbsa.work_dir` and (when enabled) `analyze_mmpbsa.work_dir`.

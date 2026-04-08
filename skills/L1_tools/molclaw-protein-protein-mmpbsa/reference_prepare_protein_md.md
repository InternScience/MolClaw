---
name: reference_prepare_protein_md
description: Tool reference for the MCP `prepare_protein_md` call powering the protein-protein workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# prepare_protein_md Reference

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

Prepare a protein-only MD workspace for protein-protein MM/PBSA analysis by running the full GROMACS pipeline with customizable times and temperatures.

Args:
- `protein_pdb` (str): Cleaned protein PDB path produced by `fix_pdb` (required).
- `full_md` (bool): Run full MD pipeline (setup, minimization, equilibration, production) (default: False, but True for this workflow).
- `md_time` (float): Production MD time in picoseconds (default: 100000.0 = 100 ns).
- `temperature` (float): Thermostat temperature in Kelvin (default: 300.0).
- `nvt_time` (float): NVT equilibration time in picoseconds (default: 100.0).
- `npt_time` (float): NPT equilibration time in picoseconds (default: 100.0).

Return:
- `status` (str): `'success'` or `'error'`.
- `msg` (str): Execution summary or failure message.
- `protein_pdb` (str): Resolved path of the input PDB.
- `run_dir` (str): Generated workspace directory (e.g., `<protein>_MD_<timestamp>`).
- `full_md` (bool): Effective full-MD flag used this run.
- `md_time` (float): Effective MD duration applied.
- `temperature` (float): Applied thermostat temperature.
- `nvt_time` (float): Effective NVT time.
- `npt_time` (float): Effective NPT time.
- `files` (List[str]): Files generated in `run_dir` (e.g., em.gro, md.tpr, md.xtc, topol.top).

### 3. How to use tool `prepare_protein_md`

```python
client = DrugSDAClient("http://180.184.86.2:32208/mcp")
await client.connect()
response = await client.session.call_tool(
    "prepare_protein_md",
    arguments={
        "protein_pdb": "protein_protein_complex_fixed.pdb",
        "full_md": True,
        "md_time": 100000.0,
        "temperature": 300.0,
        "nvt_time": 100.0,
        "npt_time": 100.0,
    },
)
result = DrugSDAClient.parse_result(response)
workspace = result.get("run_dir")
await client.disconnect()
```

#### Example parameter sets

1. **Standard full-MD run** (from `prepare_protein_md.py -p protein_fixed.pdb --full-md --md-time 20 --temperature 300 --nvt-time 1 --npt-time 1` documented in README files)

```python
{
    "protein_pdb": "protein_fixed.pdb",
    "full_md": True,
    "md_time": 20.0,
    "temperature": 300.0,
    "nvt_time": 1.0,
    "npt_time": 1.0,
}
```

2. **Extended equilibration** (inspired by the `prepare_protein_md.py` CLI examples with longer runs)

```python
{
    "protein_pdb": "protein_fixed.pdb",
    "full_md": True,
    "md_time": 50000.0,
    "temperature": 310.0,
    "nvt_time": 2.0,
    "npt_time": 2.0,
}
```

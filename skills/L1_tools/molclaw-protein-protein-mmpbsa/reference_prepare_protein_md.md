---
name: reference_prepare_protein_md
description: Tool reference for the MCP `prepare_protein_md` call powering the protein-protein workflow.
license: MIT license
metadata:
    skill-author: PJLab
---

# prepare_protein_md Reference

## Usage

### 1. Scenario Description

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

### 2. How to use tool `prepare_protein_md`

```python
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

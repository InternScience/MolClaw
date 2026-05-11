---
name: molclaw-prolif-pdb
description: ProLIF static complex analysis skill for a single protein-ligand structure.
license: MIT license
metadata:
    skill-author: PJLab
---

# ProLIF Single-Structure PDB Analysis Skill

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

> [!NOTE]
> Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution.
> For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.

## Task Description
Analyze interaction fingerprints from one static protein-ligand complex structure. Use this skill for fast assessment of crystal structures, top docking poses, or representative MD frames.

## Input Source Mapping
| Parameter | Source Guidance |
|-----------|-----------------|
| `structure_path` | Can come from PDB retrieval tools, best docking poses, MD frame extraction (e.g., `openmm_extract_frames`), or complex preparation tools (e.g., `prepare_complex`) outputting complex PDB files |
| `ligand_selection` | User-defined ligand selection string that matches ligand identifiers in the structure file |
| `protein_selection` | Defaults to `protein`; can be customized to limit the analyzed region |

## Usage
### Tool: `prolif_pdb`

```text
Analyze a single complex structure and return ProLIF interaction fingerprints or counts with summary metrics.
Args:
    structure_path (str): Path to the complex structure file (commonly PDB).
    ligand_selection (str): Selection string identifying ligand atoms.
    protein_selection (str): Selection string for protein atoms. Default: 'protein'.
    interactions (List[str]|None): Optional interaction types to compute.
    count (bool): If True, compute interaction counts instead of fingerprints. Default: False.
    vicinity_cutoff (float|None): Optional distance cutoff for vicinity interactions.
    params_json (str|None): Optional JSON parameter file path for ProLIF interaction settings.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable summary or error message.
    command (str): The executed command label ('pdb').
    output_dir (str|None): Run-specific directory under tool_result/prolif_result.
    output_file (str|None): Path to the produced CSV file.
    n_frames (int|None): Number of processed frames (typically 1 for static structures).
    n_interactions (int|None): Number of interaction columns in output.
    frequent_interactions (List[dict]|None): High-frequency interactions (>30%) with keys 'interaction' and 'frequency'.
    result_summary (dict|None): Full summary dictionary from the wrapper.
```

### How To Use `prolif_pdb`

```python
response = await client.session.call_tool(
    "prolif_pdb",
    arguments={
        "structure_path": "relative/path/to/complex.pdb",
        "ligand_selection": "resname LIG",
        "protein_selection": "protein",
        "interactions": ["Hydrophobic", "HBAcceptor"]
    }
)
result = client.parse_result(response)
key_output = result["output_file"]
```

### Example Parameter Sets

```python
# 1) Main mode
{
    "structure_path": "relative/path/to/complex.pdb",
    "ligand_selection": "resname LIG",
    "protein_selection": "protein",
    "interactions": ["Hydrophobic", "HBDonor"]
}

# 2) Variant mode
{
    "structure_path": "relative/path/to/complex.pdb",
    "ligand_selection": "resname LIG",
    "count": True,
    "params_json": "relative/path/to/prolif_override.json"
}
```

## Tool Priority: interaction-visualizer is PRIMARY

> **Default:** For all single-structure protein-ligand interaction analysis, use
> `molclaw-interaction-visualizer` (local script) as the **primary** tool.
> Use `prolif_pdb` (this tool) **only** when you specifically need ProLIF-format
> fingerprint data for downstream `prolif_docking` / `prolif_md` pipeline compatibility,
> or when the interaction-visualizer script is unavailable.

| Need | Use `interaction-visualizer` (local, **PRIMARY**) | Use `prolif_pdb` (MCP, fallback) |
|------|:-------------------------------------------------:|:--------------------------------:|
| Single-structure interaction analysis | ✅ **default** | Only if visualizer unavailable |
| Schrödinger-style 2D interaction diagram | ✅ | ❌ |
| PyMOL 3D auto-rendering | ✅ | ❌ |
| Residue role annotations (Hinge/Gatekeeper/DFG) | ✅ | ❌ |
| Decision-ready JSON for agent loop | ✅ | ❌ |
| `partner_site.csv` for ligand atom modification diagnosis | ✅ | ❌ |
| Native `--resid_offset` for PDB→UniProt mapping | ✅ | ❌ (manual mapping needed) |
| MCP server unavailable | ✅ (local) | ❌ |
| ProLIF-format fingerprint for `prolif_docking`/`prolif_md` pipeline | ❌ | ✅ use this |
| Interaction fingerprint CSV for cross-structure comparison | ✅ | ✅ |

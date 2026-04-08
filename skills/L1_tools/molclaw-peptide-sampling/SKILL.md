---
name: molclaw-peptide-sampling
description: Generate peptide molecules using PepInvent, supporting template-based generation, custom peptide sequence modification, and info queries for available templates and amino acids.
license: MIT license
metadata:
    skill-author: PJLab
---

# Peptide Molecule Generation (PepInvent)

## When to Use This Tool

Use PepInvent when you need to generate **peptide or peptide-like molecules**. This includes exploring peptide scaffolds with masked positions, generating analogs of a known peptide sequence, and building peptide libraries.

**Do NOT use when:** designing peptides that must bind a specific protein target (use L2 Skill 09 which combines PepInvent with EvoBind and validation); generating small molecules (use other REINVENT4 tools).

## Overview — Three Tools

1. **`get_pepinvent_info`** — Query available templates and supported amino acids (**call first if unsure**)
2. **`pepinvent_peptide_sampling_by_template`** — Generate peptides from predefined structural templates
3. **`pepinvent_peptide_sampling_by_peptide`** — Generate variants of a user-provided peptide sequence

### Recommended Workflow
```
Step 1: Call get_pepinvent_info('templates') → see available templates
Step 2: Call get_pepinvent_info('amino_acids') → see supported amino acids
Step 3: Choose the appropriate generation tool
```

---

## Tool 1: `get_pepinvent_info`

```tex
Retrieve information about PepInvent's available templates or supported amino acids.
Args:
    mode (str): 'templates' or 'amino_acids'
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    content (str): The requested information as text
```

```python
response = await client.session.call_tool("get_pepinvent_info", arguments={"mode": "templates"})
templates = client.parse_result(response)["content"]
```

## Tool 2: `pepinvent_peptide_sampling_by_template`

```tex
Generate peptide molecules from a predefined structural template.
Args:
    template (str): Template name. Options:
        - 'tripeptide_mask_middle', 'tripeptide_mask_ends'
        - 'tetrapeptide_mask_ends', 'tetrapeptide_mask_middle'
        - 'pentapeptide_mask_partial', 'pentapeptide_mask_all'
        - 'hexapeptide_mask_partial', 'hexapeptide_alternating'
        - 'cyclic_scaffold', 'stapled_peptide'
    n (int): Number of peptides to sample
    filter_preset (str): Options: 'none', 'minimal', 'default', 'strict'. Default 'default'.
    mw_min (float): Minimum MW filter. 0 = no constraint. Default 0.
    mw_max (float): Maximum MW filter. 0 = no constraint. Default 0.
Return:
    status, msg, save_smiles_file, output_smiles_list
```

```python
response = await client.session.call_tool(
    "pepinvent_peptide_sampling_by_template",
    arguments={"template": "tetrapeptide_mask_middle", "n": 50, "filter_preset": "default", "mw_min": 400, "mw_max": 800}
)
```

## Tool 3: `pepinvent_peptide_sampling_by_peptide`

```tex
Generate peptide variants by modifying a user-provided peptide sequence.
Args:
    peptide (str): Peptide as SMILES with residues separated by '|?|'. Example: 'N[C@@H](CCCCN)C(=O)|?|N[C@@H](CC(C)C)C(=O)|?|N[C@@H](CCCNC(=N)N)C(=O)'
    n (int): Number of peptides to sample
    filter_preset (str): Default 'default'
    mw_min (float): 0 = no constraint. Default 0.
    mw_max (float): 0 = no constraint. Default 0.
Return:
    status, msg, save_smiles_file, output_smiles_list
```

```python
response = await client.session.call_tool(
    "pepinvent_peptide_sampling_by_peptide",
    arguments={"peptide": "N[C@@H](CCCCN)C(=O)|?|N[C@@H](CC(C)C)C(=O)|?|N[C@@H](CCCNC(=N)N)C(=O)", "n": 50, "filter_preset": "default", "mw_min": 300, "mw_max": 800}
)
```

## Template Selection Guide

| Need | Template | Rationale |
|------|---------|-----------|
| Vary middle residue | `tripeptide_mask_middle` | Fixed anchors, explore core |
| Diversify terminals | `tripeptide_mask_ends` / `tetrapeptide_mask_ends` | N/C-terminal diversity |
| Maximum diversity | `pentapeptide_mask_all` | All positions open |
| Cyclic peptide | `cyclic_scaffold` | Constrained ring topology |
| Stapled peptide | `stapled_peptide` | Enhanced metabolic stability |

## MW Guide

| Length | Typical MW | Suggested `mw_min`-`mw_max` |
|--------|-----------|------------------------------|
| Tripeptide | 300-500 | 250-600 |
| Tetrapeptide | 400-650 | 350-750 |
| Pentapeptide | 500-800 | 400-900 |
| Hexapeptide | 600-1000 | 500-1100 |

## Important Notes

1. **Lipinski does NOT apply to peptides.** Peptides inherently violate RO5.
2. **mw_min=0 and mw_max=0 mean "no constraint"**, not "MW must be 0."
3. **Call `get_pepinvent_info` first** when unfamiliar with available options.

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

```python
actual_count = len(result["output_smiles_list"])
```

**If actual count < 70% of requested:** Retry with `filter_preset='none'`, wider MW range, or increased `n`.

---
name: molclaw-denovo-sampling
description: Generate entirely new drug-like molecules from scratch without any starting molecule, using REINVENT4's de novo prior.
license: MIT license
metadata:
    skill-author: PJLab
---

# De Novo Molecule Generation

## When to Use This Tool

Use `reinvent_denovo_sampling` when you need to generate molecules **without any starting structure** — pure chemical space exploration. This is useful for building initial compound libraries, generating diverse scaffolds for screening, or creating random drug-like molecules for testing pipelines.

**Do NOT use when:** you have a starting molecule and want analogs (use `reinvent_mol2mol_sampling`); you want targeted optimization toward specific properties (use `reinvent_similarity_optimization`); you need to design linkers, R-groups, or peptides (use the corresponding specialized tools).

## Tool Description

```tex
Generate new molecules de novo (from scratch, no input molecule required).
Args:
    n (int): Number of molecules to sample. Actual valid output is typically 50-80% of n.
    lipinski (bool): Whether to apply Lipinski's Rule of Five filtering, default True
    filter_preset (str): Filter preset controlling chemical quality. Options:
        - 'none': No filtering — raw model output
        - 'minimal': Remove only chemically unreasonable structures
        - 'default': Standard chemical filters (reactive groups, toxic alerts)
        - 'strict': Stringent filters
        - 'druglike': Drug-likeness oriented filtering (recommended for drug discovery)
        - 'all': Apply all available filters
        Default: 'druglike'
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    save_smiles_file (str): Path to the saved CSV file with generated molecules and computed properties
    output_smiles_list (List[str]): List of generated SMILES strings
```

## Recommended Parameters

| Purpose | `n` | `filter_preset` | `lipinski` |
|---------|-----|-----------------|------------|
| Quick test / pipeline validation | 10-20 | 'default' | True |
| Drug-like library building | 100-500 | 'druglike' | True |
| Maximum diversity exploration | 200-1000 | 'minimal' | False |
| Fragment-like library | 50-200 | 'strict' | True |

## Usage Example

```python
response = await client.session.call_tool(
    "reinvent_denovo_sampling",
    arguments={
        "n": 100,
        "lipinski": True,
        "filter_preset": "druglike"
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

## Note on Downstream Use

De novo generated molecules are typically used as starting points for further workflows: property filtering (Skill 3), docking screening (Skill 2), or iterative optimization (Skill 5). Since these molecules have no target bias, expect low hit rates in docking — this is normal for de novo generation.

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

**After calling this tool, IMMEDIATELY verify the actual number of molecules generated.**

```python
actual_count = len(result["output_smiles_list"])
```

**If actual count < 70% of requested:** Consider retrying with a less restrictive `filter_preset` or increased `n`.

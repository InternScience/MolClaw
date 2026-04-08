---
name: molclaw-mol2mol-sampling
description: Generate new molecules by transforming an input molecule using different priors for scaffold-aware, similarity-controlled molecular optimization.
license: MIT license
metadata:
    skill-author: PJLab
---

# Mol2Mol Molecule Generation

## When to Use This Tool

Use `reinvent_mol2mol_sampling` when you **have a starting molecule** and need structurally related variants. This is the most commonly used REINVENT4 generation tool for lead optimization, scaffold hopping, and analog exploration.

**Do NOT use when:** you have no starting molecule (use `reinvent_denovo_sampling`); you want to optimize toward explicit property targets with RL (use `reinvent_similarity_optimization`); you want to enumerate R-groups on a fixed scaffold (use `libinvent_rgroup_sampling_by_scaffold`).

## Tool 1: `reinvent_mol2mol_sampling` — Single Molecule

```tex
Generate new molecules by transforming the input molecule using different priors.
Args:
    smiles (str): Input SMILES string of the starting molecule
    n (int): Number of molecules to sample. Actual valid output is typically 40-80% of n due to deduplication and filtering. Set n = 1.5-2x your target count.
    min_similarity (float): Minimum Tanimoto similarity threshold (Morgan FP) to the input. Molecules below this threshold are discarded. Range: 0.0-1.0.
    prior_type (str): Prior type controlling the generation style. Options:
        - 'similarity': Broad chemical space exploration (Tanimoto range ~0.2-0.6)
        - 'medium_similarity': Balanced exploration (Tanimoto ~0.4-0.7)
        - 'high_similarity': Conservative optimization (Tanimoto ~0.7-1.0)
        - 'scaffold': Strict Murcko scaffold preservation
        - 'scaffold_generic': Generic scaffold preservation — allows atom-type changes on the ring system while preserving ring topology. Best for retaining a core while varying substituents.
        - 'mmp': Matched molecular pair style — small, localized modifications
    lipinski (bool): Whether to apply Lipinski's Rule of Five filtering, default True
    filter_preset (str): Chemical filter preset. Options: 'none', 'minimal', 'default', 'strict'. Default 'default'.
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    save_smiles_file (str): Path to the saved CSV file containing all generated molecules with properties (output_smiles, input_smiles, similarity, MW, LogP, HBD, HBA, TPSA, etc.)
    output_smiles_list (List[str]): List of generated SMILES strings that passed all filters
```

## Tool 2: `batch_reinvent_mol2mol_sampling` — Multiple Molecules

```tex
Batch version: apply mol2mol sampling to each molecule in a list. Useful when you have multiple seeds (e.g., Top 5 from a previous round) and want derivatives of each.
Args:
    smiles_list (List[str]): List of input SMILES strings
    n (int): Number of molecules to sample PER input molecule
    min_similarity (float): Minimum Tanimoto similarity threshold
    prior_type (str): Same options as single version
    lipinski (bool): Default True
    filter_preset (str): Default 'default'
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    batch_result (List[dict]): One entry per input SMILES, each containing:
        - input_smiles (str)
        - output_smiles_list (List[str])
        - save_smiles_file (str)
```

## Prior Type Selection Guide

| Task Scenario | Recommended `prior_type` | Recommended `min_similarity` | Rationale |
|--------------|--------------------------|------------------------------|-----------|
| Early hit discovery, broad exploration | `similarity` | 0.3-0.5 | Maximize chemical diversity |
| Hit-to-lead, balanced | `medium_similarity` | 0.5-0.6 | Balance novelty and similarity |
| Lead optimization, conservative | `high_similarity` | 0.7-0.8 | Small modifications only |
| "Retain core scaffold" / "keep ring system" | `scaffold_generic` | 0.5-0.6 | Preserves ring topology, allows substituent variation |
| "Keep exact scaffold and substitution pattern" | `scaffold` | 0.6-0.7 | Strict scaffold SMILES matching |
| "Only local modifications (MMP-style)" | `mmp` | 0.7-0.9 | Minimal, localized changes |

**Default when user has no preference:** `similarity` with `min_similarity=0.6`.

**For iterative optimization requiring scaffold retention** (e.g., "retain quinazoline core"): use `scaffold_generic` with `min_similarity=0.5`. Always verify scaffold preservation in the output via substructure matching.

## Recommended `n` Values

| Purpose | Recommended `n` | Expected valid output |
|---------|-----------------|----------------------|
| Quick exploration | 10-20 | 5-15 |
| Standard generation | 30-50 | 15-35 |
| Large library building | 100-200 | 50-140 |
| Iterative rounds (per seed) | 10-15 | 5-10 |

## Usage Example — Single Molecule

```python
response = await client.session.call_tool(
    "reinvent_mol2mol_sampling",
    arguments={
        "smiles": "COCCOC1=C(C=C2C(=C1)C(=NC=N2)NC3=CC=CC(=C3)C#C)OCCOC",
        "n": 30,
        "min_similarity": 0.5,
        "prior_type": "scaffold_generic",
        "lipinski": True,
        "filter_preset": "default"
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

## Usage Example — Batch (Multiple Seeds)

```python
response = await client.session.call_tool(
    "batch_reinvent_mol2mol_sampling",
    arguments={
        "smiles_list": [top1_smiles, top2_smiles, top3_smiles, top4_smiles, top5_smiles],
        "n": 10,
        "min_similarity": 0.6,
        "prior_type": "high_similarity",
        "lipinski": True,
        "filter_preset": "default"
    }
)
result = client.parse_result(response)
for item in result["batch_result"]:
    print(f"Input: {item['input_smiles']}, Generated: {len(item['output_smiles_list'])}")
```

## Important Notes

1. **Scaffold preservation is probabilistic.** Even with `scaffold` or `scaffold_generic` priors, not all generated molecules are guaranteed to contain the original scaffold. Always run substructure verification after generation when scaffold retention is required.
2. **Output CSV contains rich data.** The `save_smiles_file` CSV includes columns for similarity to input, MW, LogP, HBD, HBA, TPSA, Lipinski violations, and more — useful for downstream filtering without additional tool calls.
3. **Iterative use pattern.** In multi-round optimization, use the best molecule from Round N as the `smiles` input for Round N+1. This is the standard seed-update approach.

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

**After calling this tool, IMMEDIATELY verify the actual number of molecules generated by programmatically counting entries in the output file.** Do NOT rely on the requested count `n` or on memory.

```python
actual_count = len(result["output_smiles_list"])
```

**If actual count < 70% of requested:** Consider retrying with adjusted parameters (lower `filter_preset`, lower `min_similarity`, increase `n`). **If actual count differs from requested:** Report the ACTUAL count in all downstream summaries and the final report. A report claiming "generated 50 molecules" when only 33 exist is data fabrication.

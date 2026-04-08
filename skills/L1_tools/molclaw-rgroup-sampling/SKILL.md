---
name: molclaw-rgroup-sampling
description: Generate new molecules by decorating a scaffold with R-groups at specified attachment points, using LibInvent for scaffold-constrained molecular generation.
license: MIT license
metadata:
    skill-author: PJLab
---

# R-Group Molecule Generation (LibInvent)

## When to Use This Tool

Use LibInvent R-group sampling when you have a **fixed molecular scaffold with defined attachment points** and want to explore different substituents. Ideal for SAR studies, scaffold decoration, and library enumeration.

**Do NOT use when:** you want to modify the overall structure (use `reinvent_mol2mol_sampling`); you want RL-driven R-group optimization toward property targets (use `libinvent_rgroup_optimization`).

## Tool 1: `libinvent_rgroup_sampling_by_scaffold` — Custom Scaffold

```tex
Generate molecules by decorating a user-provided scaffold at marked R-group positions.
Args:
    scaffold (str): Scaffold SMILES with R-group positions marked as [*:1], [*:2], etc. Example: 'c1ccc([*:1])cc1C(=O)N[*:2]'
    n (int): Number of molecules to sample
    lipinski (bool): Default True
    filter_preset (str): Options: 'none', 'minimal', 'default', 'strict'. Default 'default'.
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    save_smiles_file (str): Path to saved CSV with decorated molecules and properties
    output_smiles_list (List[str]): List of generated fully-decorated SMILES
```

## Tool 2: `libinvent_rgroup_sampling_by_scaffold_name` — Predefined Scaffolds

```tex
Generate molecules using a predefined common drug scaffold.
Args:
    scaffold_name (str): Options:
        - 'benzamide': amide-linked biaryl
        - 'biphenyl': biphenyl axis
        - 'pyrimidine': trisubstituted pyrimidine
        - 'indole': indole scaffold
        - 'quinoline': quinoline scaffold
        - 'piperidine_phenyl': phenylpiperidine
        - 'sulfonamide': sulfonamide
        - 'phenyl': disubstituted phenyl
        - 'pyridine': pyridine
        - 'morpholine': morpholine
        - 'triazine': triazine
        - 'trisubstituted_benzene': 1,3,5-trisubstituted benzene
    n (int): Number of molecules to sample
    filter_preset (str): Default 'default'
    lipinski (bool): Default True
Return:
    Same as Tool 1
```

## Scaffold SMILES Format

Mark each R-group position with `[*:N]` (N = unique integer):
- 1 position: `c1ccc([*:1])cc1`
- 2 positions: `c1ccc([*:1])cc1C(=O)N[*:2]`
- 3 positions: `[*:1]c1cc([*:2])nc([*:3])n1`

**Common mistakes:** Use `[*:1]` not `[*1]` or bare `*`. Ensure valid RDKit-parseable SMILES.

## Usage Examples

```python
# Custom scaffold
response = await client.session.call_tool(
    "libinvent_rgroup_sampling_by_scaffold",
    arguments={"scaffold": "c1ccc([*:1])cc1C(=O)N[*:2]", "n": 100, "lipinski": True, "filter_preset": "default"}
)

# Predefined scaffold
response = await client.session.call_tool(
    "libinvent_rgroup_sampling_by_scaffold_name",
    arguments={"scaffold_name": "pyrimidine", "n": 100, "lipinski": True, "filter_preset": "default"}
)
```

## Important Notes

1. **Output is the fully decorated molecule**, not the R-group fragment alone.
2. **For RL-driven R-group optimization** with property targets, use `libinvent_rgroup_optimization` instead.
3. **Custom scaffold parsing errors** are the most common failure. If the tool errors, try `by_scaffold_name` with the closest predefined scaffold as a diagnostic.

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

```python
actual_count = len(result["output_smiles_list"])
```

**If actual count < 70% of requested:** Retry with `filter_preset='minimal'` or increased `n`.

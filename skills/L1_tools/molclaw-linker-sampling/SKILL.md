---
name: molclaw-linker-sampling
description: Generate linker molecules connecting two warhead fragments, for applications such as PROTAC design, bivalent ligands, and fragment merging.
license: MIT license
metadata:
    skill-author: PJLab
---

# Linker Molecule Generation (LinkInvent)

## When to Use This Tool

Use LinkInvent linker sampling when you have **two molecular fragments (warheads)** and need to generate linker structures connecting them. Common applications include PROTAC design, bivalent ligand construction, and fragment-based drug design.

**Do NOT use when:** you want to modify a complete molecule (use `reinvent_mol2mol_sampling`); you want to add R-groups to a scaffold (use `libinvent_rgroup_sampling`).

## Tool 1: `linkinvent_linker_sampling_by_warheads` — Custom Warhead SMILES

```tex
Generate linker molecules connecting two user-specified warhead fragments.
Args:
    warheads (str): SMILES of two warheads separated by '|'. Each warhead must contain exactly one '*' attachment point. Example: '*c1ccc(O)cc1|*N1CCNCC1'
    n (int): Number of molecules to sample
    filter_preset (str): Options: 'none', 'minimal', 'default', 'strict'. Default 'default'.
    lipinski (bool): Default True. Set False for PROTACs (inherently large).
    min_linker_atoms (int): Minimum heavy atoms in linker. 0 = no constraint. Default 0.
    max_linker_atoms (int): Maximum heavy atoms in linker. 0 = no constraint. Default 0.
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    save_smiles_file (str): Path to saved CSV
    output_smiles_list (List[str]): List of generated linked molecule SMILES
```

## Tool 2: `linkinvent_linker_sampling_by_warhead_pair_name` — Predefined Pairs

```tex
Generate linker molecules using a predefined warhead pair (no SMILES needed).
Args:
    warhead_pair_name (str): Options:
        - 'phenyl_phenyl', 'phenyl_pyridine', 'phenyl_piperidine',
        - 'phenyl_morpholine', 'pyridine_morpholine', 'phenol_furan',
        - 'indole_piperazine', 'thiophene_piperazine', 'benzamide_piperidine'
    n (int): Number of molecules to sample
    filter_preset (str): Default 'default'
    lipinski (bool): Default True
    min_linker_atoms (int): Default 0
    max_linker_atoms (int): Default 0
Return:
    Same as Tool 1
```

## Linker Length Guide

| Application | `min_linker_atoms`-`max_linker_atoms` | Rationale |
|------------|--------------------------------------|-----------| 
| Fragment merging | 1-5 | Short, rigid |
| Bivalent ligand | 3-8 | Moderate flexibility |
| PROTAC (CRBN-based) | 6-12 | Shorter preferred for CRBN |
| PROTAC (VHL-based) | 8-15 | Longer often needed |

## Usage Examples

```python
# Custom warheads
response = await client.session.call_tool(
    "linkinvent_linker_sampling_by_warheads",
    arguments={
        "warheads": "*c1ccc(O)cc1|*N1CCNCC1",
        "n": 50, "lipinski": True, "filter_preset": "default",
        "min_linker_atoms": 3, "max_linker_atoms": 8
    }
)

# Predefined pair
response = await client.session.call_tool(
    "linkinvent_linker_sampling_by_warhead_pair_name",
    arguments={
        "warhead_pair_name": "phenyl_piperidine",
        "n": 50, "lipinski": False, "filter_preset": "default",
        "min_linker_atoms": 6, "max_linker_atoms": 12
    }
)
```

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

```python
actual_count = len(result["output_smiles_list"])
```

**If actual count < 70% of requested:** Retry with looser `filter_preset`, wider linker atom range, or increased `n`.

---
name: molclaw-mol-structure-metrics
description: Compute a set of molecular structure complexity descriptors for a list of SMILES strings, returning detailed metrics for each molecule including the number of rotatable bonds, total/aromatic/aliphatic/saturated rings, heteroatoms, and bridgehead atoms, as well as the fraction of sp³-hybridized carbon atoms (Fsp³).
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecular Structure Properties Calculation

The description of tool *calculate_mol_structure_complexity*.

```tex
Compute a set of molecular structure complexity descriptors for each SMILES.
Args:
    smiles_list (List[str]): List of input SMILES strings, (e.g., ["N[C@@H](Cc1ccc(O)cc1)C(=O)O", "CC(C)C1=CC=CC=C1"])
Return:
    status (str): success/error
    msg (str): message
    metrics (List[dict]): List of dict, each containing feature keys.
        --smiles (str): A SMILES string of smiles_list
        --num_rotatable_bonds (int): Number of rotatable bonds
        --num_rings (int): Number of total rings
        --num_aromatic_rings (int): Number of aromatic rings
        --num_aliphatic_rings (int): Number of aliphatic rings
        --num_saturated_rings (int): Number of saturated rings
        --num_heteroatoms (int): Number of heteroatoms
        --fraction_csp3 (float): The fraction of sp³-hybridized carbon atoms (Fsp³)
        --num_bridgehead_atoms (int): Number of bridgehead atoms
```

How to use tool *calculate_mol_structure_complexity*:

```python
response = await client.session.call_tool(
    "calculate_mol_structure_complexity",			
    arguments={
        "smiles_list": smiles_list
    }
)
result = client.parse_result(response)
metrics = result["metrics"]
```


---
name: molclaw-mol-hydrophobicity-metrics
description: Computes hydrophobicity-related molecular descriptors for a given list of SMILES strings, returning the octanol-water partition coefficient (logP) and molar refractivity for each input molecule.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecular Hydrophobicity-related Properties Calculation

The description of tool *calculate_mol_hydrophobicity*.

```tex
Compute hydrophobicity-related molecular descriptors for each SMILES.
Args:
    smiles_list (List[str]): List of input SMILES strings, (e.g., ["N[C@@H](Cc1ccc(O)cc1)C(=O)O", "CC(C)C1=CC=CC=C1"])
Return:
    status (str): success/error
    msg (str): message
    metrics (List[dict]): List of dict, each containing feature keys.
        --smiles (str): A SMILES string of smiles_list
        --logp (float): The octanol-water partition coefficient (logP)
        --molar_refractivity (float): Molar refractivity
```

How to use tool *calculate_mol_hydrophobicity*:

```python
response = await client.session.call_tool(
    "calculate_mol_hydrophobicity",			
    arguments={
        "smiles_list": smiles_list
    }
)
result = client.parse_result(response)
metrics = result["metrics"]
```


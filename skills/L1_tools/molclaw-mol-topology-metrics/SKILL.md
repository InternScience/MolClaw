---
name: molclaw-mol-topology-metrics
description: Compute a comprehensive set of topological descriptors for a list of SMILES strings, returning the Topological Polar Surface Area (TPSA), a series of valence and non-valence molecular connectivity indices (Chi0–Chi4), the Hall–Kier alpha value, and Kappa shape indices (Kappa1–Kappa3) for each input molecule.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecular Topology Properties Calculation

The description of tool *calculate_mol_topology*.

```tex
Compute a set of topological descriptors for each SMILES.
Args:
    smiles_list (List[str]): List of input SMILES strings, (e.g., ["N[C@@H](Cc1ccc(O)cc1)C(=O)O", "CC(C)C1=CC=CC=C1"])
Return:
    status (str): success/error
    msg (str): message
    metrics (List[dict]): List of dict, each containing several feature keys.
        --smiles (str): A SMILES string of smiles_list
        --tpsa (float): Topological polar surface area
        --chi0v (float): Non-valence molecular connectivity index
        --chi1v (float): Non-valence molecular connectivity index
        --chi2v (float): Non-valence molecular connectivity index
        --chi3v (float): Non-valence molecular connectivity index
        --chi4v (float): Non-valence molecular connectivity index
        --chi0n (float): Non-valence molecular connectivity index
        --chi1n (float): Non-valence molecular connectivity index
        --chi2n (float): Non-valence molecular connectivity index
        --chi3n (float): Non-valence molecular connectivity index
        --chi4n (float): Non-valence molecular connectivity index
        --hall_kier_alpha (float): Hall–Kier alpha value
        --kappa1 (float): Kappa shape index
        --kappa2 (float): Kappa shape index
        --kappa3 (float): Kappa shape index
```

How to use tool *calculate_mol_topology*:

```python
response = await client.session.call_tool(
    "calculate_mol_topology",			
    arguments={
        "smiles_list": smiles_list
    }
)
result = client.parse_result(response)
metrics = result["metrics"]
```


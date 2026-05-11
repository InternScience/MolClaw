---
name: molclaw-mol-complexity-metrics
description: Compute custom molecular complexity-related descriptors for a given list of SMILES strings, returning the molecular complexity score, aromatic proportion, and asphericity value for each input molecule.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecular Complexity-related Properties Calculation

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *calculate_mol_complexity*.

```tex
Compute custom molecular complexity-related descriptors for each SMILES.
Args:
    smiles_list (List[str]): List of input SMILES strings, (e.g., ["N[C@@H](Cc1ccc(O)cc1)C(=O)O", "CC(C)C1=CC=CC=C1"])
Return:
    status (str): success/error
    msg (str): message
    metrics (List[dict]): List of dict, each containing feature keys.
        --smiles (str): A SMILES string of smiles_list
        --molecular_complexity (int): Molecular complexity
        --aromatic_proportion (float): Aromatic proportion 
        --asphericity (float): Asphericity
```

How to use tool *calculate_mol_complexity*:

```python
response = await client.session.call_tool(
    "calculate_mol_complexity",			
    arguments={
        "smiles_list": smiles_list
    }
)
result = client.parse_result(response)
metrics = result["metrics"]
```

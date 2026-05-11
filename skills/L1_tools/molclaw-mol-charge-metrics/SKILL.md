---
name: molclaw-mol-charge-metrics
description: Compute Gasteiger partial charges and formal charge for a list of SMILES strings, returning the minimum, maximum, average, and range of the Gasteiger charges alongside the formal charge for each molecule.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecular Charge-related Properties Calculation

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *calculate_mol_charge*.

```tex
Compute Gasteiger partial charges and formal charge for each SMILES.
Args:
    smiles_list (List[str]): List of input SMILES strings, (e.g., ["N[C@@H](Cc1ccc(O)cc1)C(=O)O", "CC(C)C1=CC=CC=C1"])
Return:
    status (str): success/error
    msg (str): message
    metrics (List[dict]): List of dict, each containing several feature keys.
        --smiles (str): A SMILES string of smiles_list
        --min_gasteiger_charge (float): Minimum of Gasteiger charges
        --max_gasteiger_charge (float): Maximum of Gasteiger charges
        --avg_gasteiger_charge (float): Average of Gasteiger charges
        --gasteiger_charge_range (float): Range of Gasteiger charges
        --formal_charge (int): Formal charge
```

How to use tool *calculate_mol_charge*:

```python
response = await client.session.call_tool(
    "calculate_mol_charge",			
    arguments={
        "smiles_list": smiles_list
    }
)
result = client.parse_result(response)
metrics = result["metrics"]
```

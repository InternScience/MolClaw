---
name: molclaw-compound-retrieve
description: Retrieve SMILES strings from PubChem database using compound names. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Retrieve Compound SMILES

The description of tool *retrieve_smiles_by_compoundname*.

```tex
Retrieve SMILES strings from PubChem using compound names.
Args:
    compound_names (List[str]): List of input compound names (e.g., ["aspirin", "caffeine"])
Return:
    status (str): success/partial_success/error
    msg (str): message
    retrieve_smiles (List[dict]): List of dict, each containing the keys 'compound_name' and 'smiles'.
        --compound_name (str): A compound name of compound_names 
        --smiles (str): The retrieved SMILES string, if it exists; otherwise, None.
```

How to use tool *retrieve_smiles_by_compoundname* :

```python
response = await client.session.call_tool(
    "retrieve_smiles_by_compoundname",
    arguments={
        "compound_names": compound_names
    }
)
result = client.parse_result(response)
retrieve_smiles = result["retrieve_smiles"]
```


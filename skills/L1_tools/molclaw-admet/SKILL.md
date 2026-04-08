---
name: molclaw-admet
description: Predict the ADMET (absorption, distribution, metabolism, excretion, and toxicity) properties of the input molecules. 
license: MIT license
metadata:
    skill-author: PJLab
---

# ADMET Properties Prediction

The description of tool *pred_mol_admet*.

```tex
Predict the ADMET (absorption, distribution, metabolism, excretion, and toxicity) properties of the input molecules from smiles list or file.
Args:
    smiles_list (List[str]): List of input SMILES strings, (e.g., ["N[C@@H](Cc1ccc(O)cc1)C(=O)O", "CC(C)C1=CC=CC=C1"]), default is []
    smiles_file (str): Path to a file containing SMILES strings (TXT or CSV format), default is ''
Return:
    status (str): success/error
    msg (str): message
    json_content (List[Dcit]): List of dict, each containing the keys 'smiles', 'physicochemical', 'druglikeness' and 'admet_predictions', where 'admet_predictions' includes over 90 key-value pairs representing various molecular properties 
    json_file (str): Path to the json file saving the ADMET prediction results
```

How to use tool *pred_mol_admet* :

```python
response = await client.session.call_tool(
    "pred_mol_admet",
    arguments={
        "smiles_list": smiles_list,
        "smiles_file": ''
    }
)
result = client.parse_result(response)
admet_predictions = result["json_content"]
```


---

## ⚠ Computation-First Declaration (L3 Principles 10, 13)

ADMET predictions from `pred_mol_admet` are **Level 1 direct tool computations** — the highest authority for ADMET data. When reporting these values:

- **Label as:** "ADMET-AI predicted CYP3A4 inhibition probability: 0.72 (statistical prediction)" — Category 1 tool-computed fact.
- **NEVER say:** "This molecule inhibits CYP3A4" — ADMET-AI provides probabilities, not binary facts.
- **NEVER substitute** with literature IC50/EC50 values unless explicitly comparing computational vs. experimental. If literature values are cited, label them: "⚠️ LITERATURE VALUE: ..."
- **All probabilities must be in [0, 1].** Values outside this range indicate tool error — re-run, do not accept.

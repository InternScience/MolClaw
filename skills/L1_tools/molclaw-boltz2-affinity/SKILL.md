---
name: molclaw-boltz2-affinity
description: Predict binding affinity between target protein sequence and small molecule SMILES using Boltz-2. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Boltz-2 Protein-Ligand Binding

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

step 1. Use skill **molclaw-protein-sequence-retrieve** to get the target protein sequence information. If the target protein sequence has been provided, skip this step.

step 2. Finally use tool *pred_binding_affinity_boltz2* to predict the binding affinity.  

Tool description:

```tex
Use Boltz to predict binding affinity between protein (receptor) and small molecule (ligand).
Args:
    protein (List[dict]): Protein chains, each element contains 'chain' and 'sequence' (e.g., [{{'chain': 'A', 'sequence': 'MGNAAAAKKGSEQASQRRSSLEQP*'}}])
    smiles (str): Input SMILES string (e.g., "N[C@@H](Cc1ccc(O)cc1)C(=O)O")
Return:
    status (str): success/error
    msg (str): message
    affinity_probability_binary (float): Represents the predicted probability (ranging from 0 to 1) that a ligand is a binder, making it ideal for distinguishing active compounds from decoys during the hit-discovery stage. A value below 0.5 indicates uncertain or weak binding.
    affinity_pred_value (float): Estimates the specific binding affinity as log10(IC50) in μM to quantify how small molecular modifications affect potency, serving as a key metric for ligand optimization phases like hit-to-lead and lead-optimization.
    complex_cif_file (str): Structure file of the protein–molecule complex
```

Tool usage:

```python
response = await client.session.call_tool(
    "pred_binding_affinity_boltz2",
    arguments={
        "protein": protein_chains,
        "smiles": smiles
    }
)
result = client.parse_result(response)
affinity_probability_binary = result["affinity_probability_binary"]
affinity_pred_value = result["affinity_pred_value"]
```

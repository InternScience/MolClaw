---
name: molclaw-boltz2-affinity
description: Predict binding affinity between target protein sequence and small molecule SMILES using Boltz-2. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Boltz-2 Protein-Ligand Binding

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


---

## ⚠ Mandatory Complex CIF Download (L3 Principle 14)

**After calling `pred_binding_affinity_boltz2`, ALWAYS download the `complex_cif_file`** — this is the predicted protein-ligand complex structure. It is a Category A file, essential for downstream interaction analysis (ProLIF), visualization, and user verification.

```python
import base64, os
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": result["complex_cif_file"]}
)
dl = client.parse_result(response)
local_path = f"step{N}_boltz2_complex.cif"
with open(local_path, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))
assert os.path.getsize(local_path) > 0
```

## ⚠ Output Plausibility Check (L3 Principle 12 Checkpoint A)

- `affinity_probability_binary` must be in [0, 1]. Values outside this range indicate tool error.
- `affinity_probability_binary` < 0.5 suggests uncertain/weak binding — note this in the report.
- The predicted complex structure uses **1-based sequential numbering** from the input sequence. If you need to interpret specific residue interactions, apply residue numbering mapping (see `molclaw-residue-mapper`).

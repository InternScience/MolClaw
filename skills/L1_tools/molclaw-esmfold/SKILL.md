---
name: molclaw-esmfold
description: Use ESMFold model to predict 3D structure of the input protein sequence. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Protein Structure Prediction

The description of tool *pred_protein_structure_esmfold*.

```tex
Use the ESMFold model for protein 3D structure prediction.
Args:
    sequence (str): Protein sequence
Return:
    status: success/error
    msg: message
    pdb_path (str): The predicted pdb file path
```

How to use tool *pred_protein_structure_esmfold* :

```python
response = await client.session.call_tool(
    "pred_protein_structure_esmfold",
    arguments={
        "sequence": sequence
    }
)
result = client.parse_result(response)
pred_protein_structure = result["pdb_path"]
```



---

## ⚠ Mandatory Output File Download (L3 Principle 14)

**After calling this tool, you MUST download all output structure files** from the MCP server to the local workspace using `server_file_to_base64`. A tool call is NOT considered complete until its output files have been downloaded and verified locally (`ls -la <file>` — size must be > 0).

```python
import base64, os
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": result["output_file"]}  # or relevant output field
)
dl = client.parse_result(response)
local_path = "stepNN_descriptive_name.ext"
with open(local_path, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))
assert os.path.getsize(local_path) > 0, f"Download failed: {local_path}"
```

**Download policy:** All structure output files are **Category A (user-critical)** — essential for user verification, downstream analysis, and reproducibility. When in doubt, download. Over-collection is always preferred over under-collection.


---

## ⚠ Confidence Metric Checkpoint (L3 Principle 12 Checkpoint A)

After ESMFold prediction, check pLDDT (stored in B-factor column):
- **pLDDT > 85:** Excellent confidence
- **pLDDT 70-85:** Good
- **pLDDT < 70:** Moderate to low — note in report as limitation
- **pLDDT < 50:** Very low — consider alternative structure sources

## ⚠ Numbering Scheme (L3 Principle 17)

ESMFold structures use **1-based sequential numbering** from the input sequence. If the task references UniProt residue numbers, apply `molclaw-residue-mapper` to build the mapping before any residue-specific analysis.

## ⚠ Sequence Length Limitation

ESMFold quality degrades significantly for sequences > 800 residues. For longer proteins, use Chai-1 (`molclaw-chai1-predict`) instead.

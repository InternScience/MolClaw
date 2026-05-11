---
name: molclaw-sequence-valid-check
description: Check if the input protein sequence is valid. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Protein Sequence Valid Check

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *is_valid_protein_sequence*.

```tex
Check if the input protein sequence string is valid.
Args:
    sequences (List[str]): List of input protein sequences
Return:
    status (str): success/partial_success/error
    msg (str): message
    valid_res (List[dict]): List of dict, each containing the keys 'sequence' and 'is_valid'.
        --sequence (str): A protein sequence of the input sequences list 
        --is_valid (bool): Is the protein sequence valid or not
```

How to use tool *is_valid_protein_sequence* :

```python

response = await client.session.call_tool(
    "is_valid_protein_sequence",
    arguments={
        "sequences": sequence_list
    }
)
result = client.parse_result(response)
valid_res = result["valid_res"]
```

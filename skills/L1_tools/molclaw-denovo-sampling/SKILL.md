---
name: molclaw-denovo-sampling
description: Generate new molecules de novo. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Generation De Novo

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *reinvent_denovo_sampling*.

```tex
Generate new molecules de novo.
Args:
    n (int): Number of molecules for sampling
    lipinski (bool): Whether to apply Lipinski's rule of five filtering, default is True
    filter_preset (str): Filter preset, options: ['none', 'minimal', 'default', 'strict', 'druglike', 'all'], default is 'druglike'
Return:
    status (str): success/error
    msg (str): message
    save_smiles_file (str): Path to the saved SMILES file
    output_smiles_list (List[str]): List of generated SMILES strings
```

How to use tool *reinvent_denovo_sampling* :

```python
response = await client.session.call_tool(
    "reinvent_denovo_sampling",
    arguments={
        "n": n,
        "lipinski": True,
        "filter_preset": filter_type
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

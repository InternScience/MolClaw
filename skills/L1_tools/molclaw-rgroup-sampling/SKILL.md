---
name: molclaw-rgroup-sampling
description: Generate new molecules sampling from the input scaffold. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Generation from Scaffold

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *libinvent_rgroup_sampling_by_scaffold*.

```tex
Generate new molecules sampling from the input scaffold.
Args:
    scaffold (str): Input scaffold SMILES string containing R-group position markers such as [*:1], [*:2], etc. e.g., 'c1ccc([*:1])cc1C(=O)N[*:2]'
    n (int): Number of molecules for sampling
    lipinski (bool): Whether to apply Lipinski's rule of five filtering, default is True
    filter_preset (str): Filter preset, options: ['none', 'minimal', 'default', 'strict'], default is 'default'
Return:
    status (str): success/error
    msg (str): message
    save_smiles_file (str): Path to the saved SMILES file
    output_smiles_list (List[str]): List of generated SMILES strings
```

How to use tool *libinvent_rgroup_sampling_by_scaffold* :

```python
response = await client.session.call_tool(
    "libinvent_rgroup_sampling_by_scaffold",
    arguments={
        "scaffold": scaffold,
        "n": n,
        "lipinski": True,
        "filter_preset": filter_type
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

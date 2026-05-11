---
name: molclaw-linker-sampling
description: Generate new molecules sampling from the input two warhead fragments. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Generation from Warhead Fragments

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *linkinvent_linker_sampling_by_warheads*.

```tex
Generate new molecules sampling from the input two warhead fragments.
Args:
    warheads (str): SMILES of two warheads separated by '|', e.g., '*c1ccc(O)cc1|*N1CCNCC1'
    n (int): Number of molecules for sampling
    filter_preset (str): Filter preset, options: ['none', 'minimal', 'default', 'strict'], default is 'default'
    lipinski (bool): Whether to apply Lipinski's rule of five filtering, default is True
    min_linker_atoms (int): Minimum number of atoms in the linker, default is 0
    max_linker_atoms (int): Maximum number of atoms in the linker, default is 0
Return:
    status (str): success/error
    msg (str): message
    save_smiles_file (str): Path to the saved SMILES file
    output_smiles_list (List[str]): List of generated SMILES strings
```

How to use tool *linkinvent_linker_sampling_by_warheads* :

```python
response = await client.session.call_tool(
    "linkinvent_linker_sampling_by_warheads",
    arguments={
        "warheads": warheads,
        "n": n,
        "lipinski": True,
        "filter_preset": filter_type,
        "min_linker_atoms": min_linker_atoms,
        "max_linker_atoms": max_linker_atoms
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

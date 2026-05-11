---
name: molclaw-mol2mol-sampling
description: Generate new molecules sampling from the input molecule. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Mol2Mol Molecule Generation

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *reinvent_mol2mol_sampling*.

```tex
Generate new molecules sampling from the input molecule using different priors ('similarity': broad exploration, 'medium_similarity': balanced exploration, 'high_similarity': conservative optimization, 'scaffold': strict scaffold preservation, 'scaffold_generic': generic scaffold preservation, 'mmp': MMP-style local modifications).
Args:
    smiles (str): Input SMILES string
    n (int): Number of molecules for sampling
    min_similarity (float): Minimum similarity threshold, default is 0.6
    prior_type (str): Prior type for generation, options: ['scaffold_generic', 'scaffold', 'mmp', 'similarity', 'high_similarity', 'medium_similarity'], default is 'similarity'
    lipinski (bool): Whether to apply Lipinski's rule of five filtering, default is True
    filter_preset (str): Filter preset, options: ['none', 'minimal', 'default', 'strict'], default is 'default'
Return:
    status (str): success/error
    msg (str): message
    save_smiles_file (str): Path to the saved SMILES file
    output_smiles_list (List[str]): List of generated SMILES strings
```

How to use tool *reinvent_denovo_sampling* :

```python
response = await client.session.call_tool(
    "reinvent_mol2mol_sampling",
    arguments={
        "smiles": smiles,
        "n": n,
        "min_similarity": min_similarity,
        "prior_type": prior_type,
        "lipinski": True,
        "filter_preset": filter_type
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

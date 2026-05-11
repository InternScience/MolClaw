---
name: molclaw-peptide-sampling
description: Generate new peptide molecules sampling from the input peptide sequence. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Peptide Molecule Generation

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *pepinvent_peptide_sampling_by_peptide*.

```tex
Generate new peptide molecules sampling from the input peptide sequence.
Args:
    peptide (str): SMILES representation of a peptide sequence, with amino acid residues separated by '|?|', e.g., 'N[C@@H](CCCCN)C(=O)|?|N[C@@H](CC(C)C)C(=O)|?|N[C@@H](CCCNC(=N)N)C(=O)' 
    n (int): Number of molecules for sampling
    filter_preset (str): Filter preset, options: ['none', 'minimal', 'default', 'strict'], default is 'default'
    mw_min (float): Minimum molecular weight, default is 0.0
    mw_max (float): Maximum molecular weight, default is 0.0
Return:
    status (str): success/error
    msg (str): message
    save_smiles_file (str): Path to the saved SMILES file
    output_smiles_list (List[str]): List of generated SMILES strings
```

How to use tool *pepinvent_peptide_sampling_by_peptide* :

```python
response = await client.session.call_tool(
    "pepinvent_peptide_sampling_by_peptide",
    arguments={
        "peptide": smiles,
        "n": n,
        "filter_preset": filter_type,
        "mw_min": mw_min,
        "mw_max": mw_max
    }
)
result = client.parse_result(response)
output_smiles_list = result["output_smiles_list"]
```

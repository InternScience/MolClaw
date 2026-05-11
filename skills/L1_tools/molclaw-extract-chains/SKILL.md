---
name: molclaw-extract-chains
description: Extract protein sequence of each chain from the protein structure file (pdb format).
license: MIT license
metadata:
    skill-author: PJLab
---

# Extract Protein Chains

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

Use tool *extract_pdb_chains* to extract protein chains from the repaired pdb file

Tool description:

```tex
Extract the amino acid sequence of each chain from the PDB file.
Args:
    pdb_file_path (str): Path to input pdb file
Return:
    status (str): success/error
    msg (str): message
    chains (List[dict]): List of dict, each containing the keys 'chain' and 'sequence'.
        --chain (str): Chain ID
        --sequence (str): Sequence string
```

Tool usage:

```python
response = await client.session.call_tool(
    "extract_pdb_chains",
    arguments={
        "pdb_file_path": fixed_pdb_path
    }
)
result = client.parse_result(response)
protein_chains = result['chains']
```

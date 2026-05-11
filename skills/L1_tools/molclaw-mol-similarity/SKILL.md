---
name: molclaw-mol-similarity
description: Calculate both Tanimoto similarities and the count of shared structural fragments between a target molecule and a list of candidate molecules via Morgan fingerprints. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Similarity Calculation

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

**Scene 1**: Compute the Tanimoto similarities between a target molecule and a list of candidate molecules using Morgan fingerprints. Need to use the tool *calculate_morgan_fingerprint_similarity*.

The description of tool *calculate_morgan_fingerprint_similarity*.

```tex
Compute the Tanimoto similarities between a target molecule and a list of candidate molecules using Morgan fingerprints.
Args:
    target_smiles (str): SMILES string of the target molecule
    candidate_smiles_list (List[str]): List of candidate molecule SMILES strings
    radius (int): Morgan fingerprint radius, default is 2
    nBits (int): Morgan fingerprint vector bits number, default is 2048
Return:
    status (str): success/error
    msg (str): message
    similarities (List[dict]): List of dict, each containing the keys 'smiles' and 'score'.
        --smiles (str): A SMILES string of candidate_smiles_list
        --score (float): Similarity value between the candidate SMILES and the target SMILES
```

How to use tool *calculate_morgan_fingerprint_similarity* :

```python
response = await client.session.call_tool(
    "calculate_morgan_fingerprint_similarity",
    arguments={
        "target_smiles": target_smiles,
        "candidate_smiles_list": candidate_smiles_list,
        "radius": radius,
        "nBits": nBits
    }
)
result = client.parse_result(response)
similarities = result["similarities"]
```

**Scene 2**: Compute the count of shared structural fragments between a target molecule and a list of candidate molecules using Morgan fingerprints. Need to use the tool *calculate_common_fragments*.

The description of tool *calculate_common_fragments*.

```tex
Compute the count of shared structural fragments between a target molecule and a list of candidate molecules using Morgan fingerprints.
Args:
    target_smiles (str): SMILES string of the target molecule
    candidate_smiles_list (List[str]): List of candidate molecule SMILES strings
    radius (int): Morgan fingerprint radius, default is 2
Return:
    status (str): success/error
    msg (str): message
    fragments_info (List[dict]): List of dict, each containing the keys 'smiles' and 'common_fragment_count'.
        --smiles (str): A SMILES string of candidate_smiles_list
        --common_fragment_count (float): Number of structural fragments shared between the candidate SMILES and the target SMILES
```

How to use tool *calculate_common_fragments* :

```python
response = await client.session.call_tool(
    "calculate_common_fragments",
    arguments={
        "target_smiles": target_smiles,
        "candidate_smiles_list": candidate_smiles_list,
        "radius": radius
    }
)
result = client.parse_result(response)
fragments_info = result["fragments_info"]
```

---
name: molclaw-extract-chains
description: Extract protein sequence of each chain from the protein structure file (pdb format).
license: MIT license
metadata:
    skill-author: PJLab
---

# Extract Protein Chains

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


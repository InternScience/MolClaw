---
name: molclaw-chroma-toolkit
description: Chroma toolkit skill covering chroma_monomer for single-chain generation, chroma_complex for multi-chain assembly generation, and chroma_symmetry for symmetry-constrained protein design.
license: MIT license
metadata:
    skill-author: PJLab
    tool-summary: |
        chroma_monomer: Generates a de novo single-chain protein candidate.
        chroma_complex: Generates a de novo multi-chain protein complex candidate.
        chroma_symmetry: Generates a symmetry-constrained oligomeric protein candidate.
---

# Chroma Protein Generation Toolkit

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Usage

### 1. Monomer Protein Generation
The description of tool *chroma_monomer*.

```tex
Generates a de novo single-chain protein candidate for exploratory protein design workflows.
Args:
    length (int): Number of residues in the monomer chain. Default: 100.
    steps (int): Diffusion sampling step count. Default: 500.
    device (str): Chroma execution device string. Default: 'cuda:0'.
    fmt (str): Output structure format, one of {'cif', 'pdb'}. Default: 'cif'.
    api_key (str|None): Optional Chroma API key for model access.
    dry_run (bool): If True, validate parameters and prepare output paths without model sampling. Default: False.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable execution summary.
    tool_name (str): Tool identifier 'chroma_monomer'.
    output_dir (str): Run-specific output directory under tool_result/chroma_toolkit_result.
    output_file (str): Target output structure file path.
    length (int): Effective residue length used in generation.
    steps (int): Effective sampling steps used in generation.
    device (str): Effective execution device.
    format (str): Effective output format.
```

How to use tool *chroma_monomer* :

```python
response = await client.session.call_tool(
    "chroma_monomer",
    arguments={
        "length": 150,
        "steps": 500,
        "device": "cuda:0",
        "fmt": "cif",
        "dry_run": False
    }
)
result = client.parse_result(response)
output_file = result["output_file"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "length": 150,
    "steps": 500,
    "device": "cuda:0",
    "fmt": "cif",
    "dry_run": False
}

# 2) Variant mode
{
    "length": 100,
    "steps": 50,
    "fmt": "cif",
    "dry_run": True
}
```

### 2. Complex Protein Generation
The description of tool *chroma_complex*.

```tex
Generates a multi-chain protein complex candidate for interface and assembly design studies.
Args:
    chains (str): Comma-separated chain lengths, for example '100,120'. Default: '100,100'.
    steps (int): Diffusion sampling step count. Default: 500.
    device (str): Chroma execution device string. Default: 'cuda:0'.
    fmt (str): Output structure format, one of {'cif', 'pdb'}. Default: 'cif'.
    api_key (str|None): Optional Chroma API key for model access.
    dry_run (bool): If True, validate parameters and prepare output paths without model sampling. Default: False.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable execution summary.
    tool_name (str): Tool identifier 'chroma_complex'.
    output_dir (str): Run-specific output directory under tool_result/chroma_toolkit_result.
    output_file (str): Target output structure file path.
    chains (str): Effective chain-length specification used in generation.
    steps (int): Effective sampling steps used in generation.
    device (str): Effective execution device.
    format (str): Effective output format.
```

How to use tool *chroma_complex* :

```python
response = await client.session.call_tool(
    "chroma_complex",
    arguments={
        "chains": "100,120",
        "steps": 500,
        "device": "cuda:0",
        "fmt": "cif",
        "dry_run": False
    }
)
result = client.parse_result(response)
output_file = result["output_file"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "chains": "100,120",
    "steps": 500,
    "device": "cuda:0",
    "fmt": "cif",
    "dry_run": False
}

# 2) Variant mode
{
    "chains": "80,80,80",
    "steps": 50,
    "fmt": "pdb",
    "dry_run": True
}
```

### 3. Symmetry-Constrained Protein Generation
The description of tool *chroma_symmetry*.

```tex
Generates a symmetry-constrained protein design candidate for oligomeric architecture exploration.
Args:
    group (str): Symmetry group label such as 'C_3' or 'D_2'.
    length (int): Residue count per protomer chain. Default: 100.
    steps (int): Diffusion sampling step count. Default: 500.
    num_chain_neighbors (int): Neighbor-chain count for symmetry conditioner. Default: 2.
    langevin_factor (float): Langevin factor for conditioned sampling. Default: 8.0.
    inverse_temperature (float): Inverse temperature for conditioned sampling. Default: 8.0.
    device (str): Chroma execution device string. Default: 'cuda:0'.
    fmt (str): Output structure format, one of {'cif', 'pdb'}. Default: 'cif'.
    api_key (str|None): Optional Chroma API key for model access.
    dry_run (bool): If True, validate parameters and prepare output paths without model sampling. Default: False.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable execution summary.
    tool_name (str): Tool identifier 'chroma_symmetry'.
    output_dir (str): Run-specific output directory under tool_result/chroma_toolkit_result.
    output_file (str): Target output structure file path.
    group (str): Effective symmetry group used in generation.
    length (int): Effective residue length per chain.
    steps (int): Effective sampling step count.
    num_chain_neighbors (int): Effective neighbor-chain parameter.
    langevin_factor (float): Effective Langevin factor.
    inverse_temperature (float): Effective inverse temperature.
    device (str): Effective execution device.
    format (str): Effective output format.
```

How to use tool *chroma_symmetry* :

```python
response = await client.session.call_tool(
    "chroma_symmetry",
    arguments={
        "group": "C_3",
        "length": 80,
        "steps": 500,
        "num_chain_neighbors": 2,
        "langevin_factor": 8.0,
        "inverse_temperature": 8.0,
        "device": "cuda:0",
        "fmt": "cif",
        "dry_run": False
    }
)
result = client.parse_result(response)
output_file = result["output_file"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "group": "C_3",
    "length": 80,
    "steps": 500,
    "num_chain_neighbors": 2,
    "langevin_factor": 8.0,
    "inverse_temperature": 8.0,
    "device": "cuda:0",
    "fmt": "cif",
    "dry_run": False
}

# 2) Variant mode
{
    "group": "D_2",
    "length": 100,
    "steps": 50,
    "num_chain_neighbors": 3,
    "langevin_factor": 6.0,
    "inverse_temperature": 10.0,
    "fmt": "pdb",
    "dry_run": True
}
```

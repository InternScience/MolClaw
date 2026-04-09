---
name: molclaw-evobind-tool
description: Design linear or cyclic peptide binders from receptor FASTA sequences using EvoBind2 with structured result outputs.
license: MIT license
metadata:
    skill-author: PJLab
---

# EvoBind2 Peptide Binder Design

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.


## Usage


### 2. EvoBind2 Binder Design
The description of tool *evobind_tool*.

```tex
Design linear or cyclic peptide binders from a receptor sequence using EvoBind2 in structure-guided screening workflows.
Args:
  fasta (str): Receptor FASTA file path.
  peptide_length (int): Binder peptide length, default 10.
  num_designs (int): Number of independent design rounds, default 10.
  num_iterations (int): Monte Carlo iterations per round, default 100.
  max_recycles (int): AlphaFold2 recycle count, default 1.
  model_name (str): AlphaFold2 model in {model_1, model_2, model_3, model_4, model_5}, default model_1.
  target_residues (str): Receptor target residues as comma-separated 1-indexed positions or all, default all.
  cyclic (bool): Whether to enable cyclic peptide design, default False.
  msa_file (str|None): Optional precomputed MSA .a3m file path, default None.
  dry_run (bool): Whether to print planned commands without executing design rounds, default False.
  skip_env_check (bool): Whether to skip source workflow environment checks, default False.
Return:
  status (str): success, error, or partial_success execution status.
  msg (str): Human-readable execution summary.
  output_dir (str): Unique run directory under tool_result/evobind_tool_result.
  fasta (str): Resolved absolute FASTA input path.
  peptide_length (int): Effective peptide length used in this run.
  num_designs (int): Effective number of design rounds used in this run.
  num_iterations (int): Effective number of iterations used in this run.
  max_recycles (int): Effective recycle count used in this run.
  model_name (str): Effective model name used in this run.
  target_residues (str): Effective target residue specification used in this run.
  cyclic (bool): Effective cyclic flag used in this run.
  dry_run (bool): Effective dry-run flag used in this run.
  skip_env_check (bool): Effective environment-check skip flag used in this run.
  output_files (dict): Key output file paths including run logs and summary artifacts when available.
  metrics (dict): Parsed summary metrics such as candidate count and top-ranked scores when available.
```

How to use tool *evobind_tool* :

```python
response = await client.session.call_tool(
    "evobind_tool",
    arguments={
        "fasta": "relative/path/to/receptor.fasta",
        "peptide_length": 10,
        "num_designs": 10,
        "num_iterations": 100,
        "max_recycles": 1,
        "model_name": "model_1",
        "target_residues": "all",
        "cyclic": False,
        "dry_run": False,
        "skip_env_check": False
    }
)
result = client.parse_result(response)
key_output = result["output_dir"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "fasta": "relative/path/to/1ssc_receptor.fasta",
    "peptide_length": 10,
    "num_designs": 10,
    "num_iterations": 100,
    "max_recycles": 1,
    "model_name": "model_1",
    "target_residues": "all",
    "cyclic": False,
    "dry_run": False,
    "skip_env_check": False
}

# 2) Variant mode
{
    "fasta": "relative/path/to/target.fasta",
    "peptide_length": 12,
    "num_designs": 50,
    "num_iterations": 500,
    "max_recycles": 3,
    "model_name": "model_2",
    "target_residues": "10,15,20,25",
    "cyclic": True,
    "msa_file": "relative/path/to/receptor.a3m",
    "dry_run": True,
    "skip_env_check": True
}
```

---

## ⚠ Mandatory Design Count Verification (L3 Principle 11)

After calling EvoBind, **programmatically count** the actual number of designs returned. Report the ACTUAL count (not the requested `num_designs`). If actual < requested, note the discrepancy.

## ⚠ Mandatory Structure File Download (L3 Principle 14)

Download ALL designed peptide structure files from the output directory. These are Category A files essential for downstream Chai-1 validation and ProLIF analysis.

## ⚠ ipTM is a Design Score, NOT an Independent Validation (L3 Principle 9)

EvoBind's ipTM is the design tool's own scoring metric. **Independent validation with Chai-1 is mandatory** before concluding that a design is successful. See L2 Skill 09 for the full validation protocol.

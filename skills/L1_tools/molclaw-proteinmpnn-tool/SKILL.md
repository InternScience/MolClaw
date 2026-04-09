---
name: molclaw-proteinmpnn-tool
description: Design or score protein sequences from PDB structures using a ProteinMPNN workflow wrapper.
license: MIT license
metadata:
    skill-author: PJLab
---

# ProteinMPNN Sequence Design

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.

## Usage


### 2. Protein Sequence Design and Scoring
The description of tool *proteinmpnn_tool*.

```tex
Run ProteinMPNN sequence design or scoring from protein structures with optional chain constraints and amino-acid controls.
Args:
    pdb_input (str): Input PDB file path or a directory containing multiple PDB files.
    model_name (str): Model name in {v_48_002, v_48_010, v_48_020, v_48_030} (default: "v_48_020").
    use_soluble (bool): Use soluble-protein model weights (default: False).
    ca_only (bool): Run CA-only model mode (default: False).
    num_seq (int): Number of sequences generated per target (default: 8).
    sampling_temp (str): Sampling temperature string; supports multiple values separated by spaces (default: "0.1").
    chains_to_design (str): Chain IDs to redesign, e.g. "A" or "A C" (default: "").
    fixed_positions (str): Residue position lists for chain constraints (default: "").
    specify_non_fixed (bool): Interpret listed positions as designable positions instead of fixed positions (default: False).
    homooligomer (bool): Enable tied-position design for homooligomers (default: False).
    omit_aas (str): Globally omitted amino acids (default: "X").
    bias_aa (str): Amino-acid bias JSON string (default: "").
    score_only (bool): Run scoring-only mode instead of sequence generation (default: False).
    path_to_fasta (str): FASTA path used in scoring mode (default: "").
    save_probs (bool): Save probability matrices (default: False).
    seed (int): Random seed (default: 0).
    skip_check (bool): Skip dependency checks in source pipeline (default: False).
    dry_run (bool): Validate inputs and create run directory without executing the pipeline (default: False).
Return:
    status (str): "success", "error", or "partial_success".
    msg (str): Human-readable execution summary.
    output_dir (str): Unique run directory under tool_result/proteinmpnn_tool_result.
    results_dir (str): Result directory path under output_dir/results.
    model_name (str): Effective model name used in this run.
    num_seq (int): Effective number of sequences used in this run.
    sampling_temp (str): Effective sampling temperature used in this run.
    score_only (bool): Effective scoring mode flag.
    dry_run (bool): Effective dry-run flag.
    output_files (dict): Produced output paths such as seqs/scores/probs directories.
    metrics (dict): Summary metrics, including sequence/score/prob file counts when available.
```

How to use tool *proteinmpnn_tool* :

```python
response = await client.session.call_tool(
    "proteinmpnn_tool",
    arguments={
        "pdb_input": "/path/to/input.pdb",
        "num_seq": 8,
        "sampling_temp": "0.1",
        "dry_run": True
    }
)
result = client.parse_result(response)
key_output = result["results_dir"]

```

#### Example parameter sets

```python
# 1) Main mode
{
    "pdb_input": "/path/to/input.pdb",
    "model_name": "v_48_020",
    "num_seq": 8,
    "sampling_temp": "0.1",
    "chains_to_design": "A",
    "dry_run": False
}

# 2) Variant mode
{
    "pdb_input": "/path/to/input.pdb",
    "score_only": True,
    "path_to_fasta": "relative/path/to/sequences.fasta",
    "seed": 42,
    "dry_run": False
}
```

---

## ⚠ Mandatory Design Count Verification (L3 Principle 11)

After calling ProteinMPNN, **programmatically verify** the actual number of designed sequences returned. If using `num_seq_per_target=8`, verify that 8 sequences were actually produced. Report the ACTUAL count.

## ⚠ Mandatory Structure Validation Download (L3 Principle 14)

After ProteinMPNN design, the standard workflow requires ESMFold validation (self-consistency check). **Download ALL predicted structures** from ESMFold for designed sequences. These are Category A files.

## ⚠ Cysteine Constraint Reminder (L3 Section 6.3)

When the design goal does NOT involve introducing new disulfide bonds, use `omit_aas="CX"` to prevent introduction of non-native cysteines that could form problematic disulfide bonds. This is especially important in thermostability design (L2 Skill 10, Scene F).

---
name: molclaw-rgroup-optimization
description: Goal-directed R-group optimization using reinforcement learning. Generates scaffold-decorated molecules optimized toward QED, property constraints, and optional similarity targets, with R-group-level controls.
license: MIT license
metadata:
    skill-author: PJLab
---

# R-Group RL Optimization (LibInvent Staged Learning)

## When to Use This Tool

Use `libinvent_rgroup_optimization` when you have a **fixed scaffold** and want to find R-group decorations that are **optimized toward specific property targets** (QED, MW, LogP, TPSA) using reinforcement learning. This tool combines the scaffold-constrained generation of LibInvent with the goal-directed optimization of REINVENT4's staged_learning mode.

**Key difference from `libinvent_rgroup_sampling`:**

| Feature | `rgroup_sampling` | `rgroup_optimization` (this tool) |
|---------|-------------------|----------------------------------|
| REINVENT4 `run_type` | `sampling` | `staged_learning` |
| Generation | Random R-group decoration | RL-guided toward property targets |
| Property control | Post-filtering only | Built-in multi-property scoring |
| R-group constraints | None | MW and ring count limits for R-groups |
| Similarity to reference | Not supported | Optional Tanimoto similarity target |
| Computation cost | Fast | Slower (proportional to `max_steps`) |

**Use this tool when:**
- You have a scaffold with `[*:N]` attachment points AND specific property goals
- The task requires "optimize R-groups to maximize QED while keeping MW < 500"
- `rgroup_sampling` + filtering yields too few molecules meeting property constraints
- You need R-group-specific constraints (e.g., "R-groups should be small, max 1 ring")

## Tool Description

```tex
RL-based R-group optimization on a fixed scaffold.
Args:
    scaffolds_file (str): Path to a .smi file containing one or more scaffolds with [*:N] attachment points (one scaffold per line)
    target_smiles (str): Optional reference molecule SMILES for similarity scoring. Default '' (no similarity target).
    similarity_weight (float): Weight for Tanimoto similarity to target_smiles. Only used when target_smiles is non-empty. Default 0.0.
    qed_weight (float): Weight for QED optimization. Default 0.4.
    mw_weight (float): Weight for molecular weight scoring (double_sigmoid). Default 0.2.
    mw_low (float): Lower bound of optimal MW range. Default 200.
    mw_high (float): Upper bound of optimal MW range. Default 500.
    logp_weight (float): Weight for LogP scoring (double_sigmoid). Default 0.1.
    logp_low (float): Lower bound of optimal LogP range. Default 0.
    logp_high (float): Upper bound of optimal LogP range. Default 5.
    tpsa_weight (float): Weight for TPSA scoring. Default 0.0.
    tpsa_low (float): Default 0.
    tpsa_high (float): Default 140.
    rgroup_mw_weight (float): Weight for R-group molecular weight constraint. Default 0.0.
    rgroup_mw_min (float): Minimum R-group MW. Default 15.
    rgroup_mw_max (float): Maximum R-group MW. Default 200.
    rgroup_rings_weight (float): Weight for R-group ring count constraint. Default 0.0.
    rgroup_rings_min (int): Minimum rings in R-group. Default 0.
    rgroup_rings_max (int): Maximum rings in R-group. Default 2.
    max_steps (int): Maximum RL training steps. Default 50.
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    save_smiles_file (str): Path to the saved CSV with optimized molecules
    output_smiles_list (List[str]): List of optimized SMILES
```

## Scaffold File Preparation

The tool requires a `.smi` file (one scaffold SMILES per line). Prepare it before calling:

```python
# Create scaffold file
scaffold_smiles = "c1ccc([*:1])cc1C(=O)N[*:2]"
with open("scaffolds.smi", "w") as f:
    f.write(scaffold_smiles + "\n")

# Then call the tool
response = await client.session.call_tool(
    "libinvent_rgroup_optimization",
    arguments={
        "scaffolds_file": "scaffolds.smi",
        "target_smiles": "",
        "similarity_weight": 0.0,
        "qed_weight": 0.4,
        "mw_weight": 0.2,
        "mw_low": 300,
        "mw_high": 500,
        "logp_weight": 0.1,
        "logp_low": 1,
        "logp_high": 4,
        "tpsa_weight": 0.1,
        "tpsa_low": 40,
        "tpsa_high": 120,
        "rgroup_mw_weight": 0.1,
        "rgroup_mw_min": 15,
        "rgroup_mw_max": 150,
        "rgroup_rings_weight": 0.1,
        "rgroup_rings_min": 0,
        "rgroup_rings_max": 2,
        "max_steps": 50
    }
)
```

## R-Group Constraint Guide

| Constraint | Use Case | Recommended Settings |
|-----------|----------|---------------------|
| Small R-groups (fragment-like) | Lead-like library | `rgroup_mw_max=100`, `rgroup_rings_max=1` |
| Medium R-groups | Standard drug-like | `rgroup_mw_max=200`, `rgroup_rings_max=2` |
| No R-group constraint | Maximum diversity | `rgroup_mw_weight=0.0`, `rgroup_rings_weight=0.0` |

## Important Notes

1. **Scaffold file must exist** before calling this tool. The tool checks for file existence and will error if the file is not found.
2. **`target_smiles` and `similarity_weight` work together.** Both must be set for similarity scoring to activate. If `target_smiles=''` or `similarity_weight=0.0`, similarity scoring is disabled.
3. **The output CSV column name is `SMILES`** (uppercase).
4. **This tool runs RL training** and takes minutes, not seconds.

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

```python
actual_count = len(result["output_smiles_list"])
```

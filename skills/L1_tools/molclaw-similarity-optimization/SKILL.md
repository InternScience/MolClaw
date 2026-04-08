---
name: molclaw-similarity-optimization
description: Goal-directed molecular optimization using reinforcement learning (staged_learning). Generates molecules similar to a target while optimizing multiple physicochemical properties simultaneously via weighted scoring components.
license: MIT license
metadata:
    skill-author: PJLab
---

# Similarity-Guided RL Molecular Optimization (REINVENT4 Staged Learning)

## When to Use This Tool

Use `reinvent_similarity_optimization` when you have a **target molecule** and want to generate derivatives that are similar to it **while simultaneously optimizing specific physicochemical properties** (QED, MW, LogP, TPSA, etc.). Unlike sampling-based tools (`reinvent_mol2mol_sampling`) that randomly sample then filter, this tool uses **reinforcement learning (RL)** to actively guide generation toward molecules that score well on a multi-component objective function.

**Key difference from `reinvent_mol2mol_sampling`:**

| Feature | `mol2mol_sampling` (sampling mode) | `similarity_optimization` (RL mode) |
|---------|-----------------------------------|--------------------------------------|
| REINVENT4 `run_type` | `sampling` | `staged_learning` |
| Generation strategy | Random sampling from prior, post-filtering | RL-guided generation toward target scores |
| Property control | Only via post-filtering | Built-in scoring components with configurable weights |
| Multi-objective | No (single similarity threshold) | Yes (up to 12 scoring components with individual weights) |
| Computation cost | Fast (seconds) | Slower (minutes, proportional to `max_steps`) |
| Best for | Chemical space exploration, library building | **Target-directed property optimization** |

**Use this tool when:**
- The user specifies explicit property targets (e.g., "improve QED to >0.7", "keep MW between 300-500", "reduce LogP to 2-4")
- You need molecules that are similar to a reference AND satisfy multiple property constraints
- The task is "optimize this molecule's drug-likeness" or "generate analogs with better ADMET properties"
- `mol2mol_sampling` + filtering produces too few hits because the property constraints are tight

**Do NOT use when:**
- You just need diverse analogs without specific property targets (use `mol2mol_sampling`)
- You have no target molecule (use `reinvent_denovo_sampling`)
- You want to optimize R-groups on a fixed scaffold (use `libinvent_rgroup_optimization`)

## Tool Description

```tex
Reinforcement-learning-based molecular optimization: generates molecules similar to a target while optimizing a weighted combination of physicochemical properties.
Args:
    target_smiles (str): Target molecule SMILES — the reference for similarity calculation
    similarity_weight (float): Weight for Tanimoto similarity to target. Higher = more emphasis on resembling the target. Default 0.7. Range: 0.0-1.0.
    fp_radius (int): Morgan fingerprint radius for similarity calculation. Options: 1 (ECFP2, loose), 2 (ECFP4, standard), 3 (ECFP6, strict). Default 3.
    qed_weight (float): Weight for QED (Quantitative Estimate of Drug-likeness). Default 0.3. Set >0 to optimize drug-likeness.
    mmp_weight (float): Weight for Matched Molecular Pair similarity. Default 0.0.
    mw_weight (float): Weight for molecular weight scoring. Default 0.0. Uses double_sigmoid transform.
    mw_low (float): Lower bound of optimal MW range. Default 200.
    mw_high (float): Upper bound of optimal MW range. Default 500.
    logp_weight (float): Weight for LogP scoring. Default 0.0. Uses double_sigmoid transform.
    logp_low (float): Lower bound of optimal LogP range. Default 0.
    logp_high (float): Upper bound of optimal LogP range. Default 5.
    tpsa_weight (float): Weight for TPSA scoring. Default 0.0. Uses double_sigmoid transform.
    tpsa_low (float): Lower bound of optimal TPSA range. Default 0.
    tpsa_high (float): Upper bound of optimal TPSA range. Default 140.
    max_steps (int): Maximum RL training steps. More steps = better convergence but slower. Default 100.
Return:
    status (str): 'success' or 'error'
    msg (str): Descriptive message
    save_smiles_file (str): Path to the saved CSV file containing generated molecules with their SMILES and scores
    output_smiles_list (List[str]): List of generated SMILES (the best molecules found during RL optimization)
```

## Weight Configuration Recipes

### Recipe 1: Pure Similarity Exploration
Generate molecules maximally similar to target, no property constraints.
```python
arguments = {
    "target_smiles": target,
    "similarity_weight": 1.0,
    "fp_radius": 2,
    "qed_weight": 0.0,
    "mmp_weight": 0.0,
    "mw_weight": 0.0, "mw_low": 200, "mw_high": 500,
    "logp_weight": 0.0, "logp_low": 0, "logp_high": 5,
    "tpsa_weight": 0.0, "tpsa_low": 0, "tpsa_high": 140,
    "max_steps": 50
}
```

### Recipe 2: Similarity + Drug-likeness (Most Common)
Balance target similarity with overall drug-likeness.
```python
arguments = {
    "target_smiles": target,
    "similarity_weight": 0.6,
    "fp_radius": 3,
    "qed_weight": 0.4,
    "mmp_weight": 0.0,
    "mw_weight": 0.0, "mw_low": 200, "mw_high": 500,
    "logp_weight": 0.0, "logp_low": 0, "logp_high": 5,
    "tpsa_weight": 0.0, "tpsa_low": 0, "tpsa_high": 140,
    "max_steps": 100
}
```

### Recipe 3: Multi-Property Constrained Optimization
Optimize toward specific property ranges while maintaining similarity.
```python
arguments = {
    "target_smiles": target,
    "similarity_weight": 0.4,
    "fp_radius": 2,
    "qed_weight": 0.2,
    "mmp_weight": 0.0,
    "mw_weight": 0.15, "mw_low": 300, "mw_high": 450,   # Constrain MW
    "logp_weight": 0.15, "logp_low": 1, "logp_high": 3,  # Target LogP 1-3
    "tpsa_weight": 0.1, "tpsa_low": 60, "tpsa_high": 120, # Target TPSA
    "max_steps": 150
}
```

### Recipe 4: Solubility-Focused Optimization
Improve aqueous solubility (lower LogP, higher TPSA) while retaining similarity.
```python
arguments = {
    "target_smiles": target,
    "similarity_weight": 0.5,
    "fp_radius": 2,
    "qed_weight": 0.1,
    "mmp_weight": 0.0,
    "mw_weight": 0.1, "mw_low": 200, "mw_high": 500,
    "logp_weight": 0.2, "logp_low": 0, "logp_high": 2.5,  # Push LogP down
    "tpsa_weight": 0.1, "tpsa_low": 80, "tpsa_high": 140,  # Push TPSA up
    "max_steps": 100
}
```

## How Scoring Works

Each scoring component uses a **transform function** (typically double_sigmoid) to convert the raw property value into a score between 0 and 1. Values within the `[low, high]` range score ~1.0; values outside score lower. The total score is a weighted sum of all component scores.

**Weight guidelines:**
- Weights do NOT need to sum to 1.0 — REINVENT4 normalizes internally
- A weight of 0.0 completely disables that component
- Higher weight = stronger optimization pressure for that property
- Start with 2-3 components, add more if needed

## `max_steps` Selection Guide

| Scenario | Recommended `max_steps` | Expected runtime |
|----------|------------------------|------------------|
| Quick test / parameter tuning | 30 | ~1 min |
| Standard optimization | 100 | ~3-5 min |
| Thorough optimization | 200 | ~10-15 min |
| Difficult multi-objective | 300+ | ~15-30 min |

## Usage Example

```python
response = await client.session.call_tool(
    "reinvent_similarity_optimization",
    arguments={
        "target_smiles": "COCCOC1=C(C=C2C(=C1)C(=NC=N2)NC3=CC=CC(=C3)C#C)OCCOC",
        "similarity_weight": 0.5,
        "fp_radius": 2,
        "qed_weight": 0.3,
        "mmp_weight": 0.0,
        "mw_weight": 0.1,
        "mw_low": 300,
        "mw_high": 500,
        "logp_weight": 0.1,
        "logp_low": 1,
        "logp_high": 3,
        "tpsa_weight": 0.0,
        "tpsa_low": 0,
        "tpsa_high": 140,
        "max_steps": 100
    }
)
result = client.parse_result(response)
optimized_smiles = result["output_smiles_list"]
```

## Important Notes

1. **This tool runs RL training, not just sampling.** Each call takes minutes, not seconds. The `max_steps` parameter directly controls runtime.
2. **Output molecules are the BEST found during RL**, not random samples. They are pre-selected for high scores on the combined objective.
3. **Combine with downstream evaluation.** RL-optimized molecules still need docking validation, ADMET profiling, and other checks — the RL scoring function is an approximation, not a substitute for full evaluation.
4. **Scaffold preservation is NOT guaranteed.** Unlike `mol2mol_sampling` with `scaffold_generic` prior, this tool optimizes freely. If scaffold retention is needed, use `mol2mol_sampling` for generation and this tool's concepts (QED/property ranges) as post-filtering criteria.
5. **The output CSV column name is `SMILES`** (uppercase), not `output_smiles`.

---

## ⚠ Mandatory Generation Count Verification (L3 Principle 11)

**After calling this tool, verify the output molecule count.** RL optimization typically produces fewer unique molecules than the batch_size × max_steps suggests, because the diversity filter removes duplicates.

```python
actual_count = len(result["output_smiles_list"])
```

## ⚠ Computation-First Principle (L3 Principle 13)

When using this tool for property optimization, the weight configuration MUST be grounded in tool-computed property values of the starting molecule (from `pred_mol_admet` or `calculate_mol_basic_info`), not from LLM estimates. For example, if the starting molecule's LogP is 3.2 (computed), set `logp_high` to a value lower than 3.2 to push LogP down.

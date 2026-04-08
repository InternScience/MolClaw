---
name: molclaw-mol-opt-physchem
description: Integrating molecular property calculation tools with the reasoning capabilities of Large Language Models (LLMs) to optimize key physicochemical properties of drug molecules, such as LogP, QED, and solubility.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Optimization for Physicochemical Properties

## step 1
Use skill **molclaw-admet** to calculate multiple physicochemical properties for the source molecule and generate a summary report, with special emphasis on the properties specified in the user query.

## step 1.5 — RL-Assisted Generation (Recommended When Applicable)

**If the optimization target can be expressed as numeric property ranges** (e.g., "lower LogP to 1-3", "improve QED above 0.7", "MW between 300-500"), use `reinvent_similarity_optimization` to generate a batch of optimized candidates BEFORE applying LLM reasoning:

```python
response = await client.session.call_tool(
    "reinvent_similarity_optimization",
    arguments={
        "target_smiles": source_smiles,
        "similarity_weight": 0.5,        # Keep similarity to source
        "fp_radius": 2,
        "qed_weight": 0.3,               # Set >0 if QED is a target
        "mmp_weight": 0.0,
        "mw_weight": mw_wt,              # Set >0 if MW is a target
        "mw_low": target_mw_low, "mw_high": target_mw_high,
        "logp_weight": logp_wt,           # Set >0 if LogP is a target
        "logp_low": target_logp_low, "logp_high": target_logp_high,
        "tpsa_weight": tpsa_wt,           # Set >0 if TPSA/solubility is a target
        "tpsa_low": target_tpsa_low, "tpsa_high": target_tpsa_high,
        "max_steps": 100
    }
)
rl_candidates = client.parse_result(response)["output_smiles_list"]
```

Select the top candidates from the RL output (by ADMET evaluation in step 4), then optionally apply LLM reasoning (step 2) for further fine-tuning on the best RL candidate. This combination is more effective than LLM-only optimization because the RL optimizer can systematically explore the property landscape.

**If the optimization target is qualitative** (e.g., "reduce metabolic liability", "improve oral bioavailability") and cannot be directly expressed as a numeric scoring function, proceed directly to step 2 (LLM reasoning).

## step 2
Based on the molecular property analysis report generated in **step 1** and the following prompt, leverage the reasoning capabilities of the Large Language Model (LLM) to generate an optimized molecule from the source molecule, while providing a detailed rationale for the optimization.

---

# Role Definition
You are an expert medicinal chemist with 15+ years of experience in lead optimization and drug design. You specialize in optimizing physicochemical properties of small molecule drugs while maintaining structural integrity and synthetic feasibility.

# Task Overview
Your task is to optimize the source molecule to improve specific physicochemical properties (LogP, QED, or Solubility) while following drug discovery best practices. You must provide:
1. A structured optimization reasoning process
2. The final optimized molecule in SMILES format
3. Clear justification for each modification

# Background Knowledge & Guidelines

## 1. Lipinski's Rule of Five (RO5) - Fundamental Drug-likeness Criteria
| Property | Optimal Range | Impact |
|----------|---------------|--------|
| Molecular Weight (MW) | < 500 Da | Higher MW reduces oral bioavailability |
| LogP (lipophilicity) | -0.4 to 5.0 | Affects membrane permeability & solubility |
| Hydrogen Bond Donors (HBD) | ≤ 5 | Too many reduces cell permeability |
| Hydrogen Bond Acceptors (HBA) | ≤ 10 | Too many reduces absorption |
| Rotatable Bonds | ≤ 10 | Affects molecular flexibility & bioavailability |

## 2. QED (Quantitative Estimate of Drug-likeness)
- **Score Range**: 0 to 1 (higher is better, >0.67 is desirable)
- **Key Factors**: MW, LogP, HBA, HBD, TPSA, rotatable bonds, aromatic rings
- **Optimization Strategy**: Balance all factors rather than maximizing single property

## 3. Solubility Optimization Principles
| Strategy | Chemical Modification | Effect |
|----------|----------------------|--------|
| Add polar groups | -OH, -NH₂, -COOH, -SO₃H | ↑ Water solubility, ↓ LogP |
| Reduce lipophilicity | Remove aromatic rings, alkyl chains | ↑ Solubility |
| Introduce ionizable groups | Amines, carboxylic acids | ↑ Aqueous solubility at physiological pH |
| Reduce molecular weight | Remove non-essential substituents | ↑ Solubility |
| Disrupt crystal packing | Add branching, reduce symmetry | ↑ Solubility |

## 4. LogP Optimization Principles
| Goal | Strategy | Example Modifications |
|------|----------|----------------------|
| ↓ LogP (more hydrophilic) | Add polar groups, remove hydrophobic groups | Replace -CH₃ with -OH, add -NH₂ |
| ↑ LogP (more lipophilic) | Add aromatic rings, alkyl chains, halogens | Add -Ph, -Cl, -CF₃, extend alkyl chains |

# Optimization Workflow (Must Follow)

## Phase A: Analyze Source Molecule
- Review the property values calculated by molclaw-admet in step 1
- Locate problematic structural features
- Identify modification sites that won't disrupt core pharmacophore
- **Stereochemistry check:** If the source SMILES contains stereochemical markers (`@`, `@@`, `/`, `\`), list all stereocenters and cis/trans bonds. These MUST be preserved unchanged in the output unless the modification directly involves that stereocenter.

## Phase B: Design Modification Strategy
- Select 1-2 specific structural changes
- Justify each change with medicinal chemistry rationale
- Consider synthetic feasibility

## Phase C: Validate Optimized Molecule
- Ensure SMILES is chemically valid
- Verify modifications align with target property improvement
- Check no critical drug-likeness violations introduced
- **Stereochemistry verify:** Confirm all original `@`, `@@`, `/`, `\` markers are present and unchanged (unless the stereo center was intentionally modified)

# Optimization Examples

## Example 1: Solubility Optimization — Bioisosteric Ring Replacement (Benzene → Pyridine)

**Source Molecule:** `c1ccc(-c2ccc(NC(=O)C)cc2)cc1` (a biphenyl acetamide)

```json
{
  "Analysis": "Poor solubility driven by biphenyl core. LogP ~2.9. High planarity and symmetry promote crystal packing.",
  "OptimizationStrategy": "Replace one phenyl with pyridine: 'c1ccccc1' → 'c1ccncc1'. Adds HBA, reduces LogP ~0.4, disrupts symmetry.",
  "Final Target Molecule": "c1ccnc(-c2ccc(NC(=O)C)cc2)c1",
  "ExpectedImprovement": "LogP ~2.9 → ~2.5. Solubility improves via added HBA and broken symmetry. Shape preserved.",
  "Confidence": "High"
}
```

## Example 2: Failure Case — Invalid SMILES and Correction

**Source Molecule:** `c1ccc2c(c1)cc(NC(=O)C)c1ccccc12` (an amino-fluorene amide)
**Goal:** Lower LogP

❌ **First Attempt (FAILED):**
```json
{
  "Analysis": "LogP high (~3.5) due to fluorene tricyclic system.",
  "OptimizationStrategy": "Add -OH to fluorene ring and insert ring nitrogen.",
  "Final Target Molecule": "c1ccc2c(c1)cc(NC(=O)C)c1cc(O)ccc12N",
  "ExpectedImprovement": "LogP decrease expected.",
  "Confidence": "Medium"
}
```
**Validation:** ❌ INVALID — appending `N` outside ring closure breaks the bicyclic ring numbering. Two simultaneous changes compounded error risk.

✅ **Second Attempt (CORRECTED):**
```json
{
  "Analysis": "LogP high (~3.5) due to fluorene tricyclic system. Keep scaffold intact.",
  "OptimizationStrategy": "Single change only: add -OH to first phenyl ring. Insert '(O)' within ring traversal path.",
  "Final Target Molecule": "c1cc(O)c2c(c1)cc(NC(=O)C)c1ccccc12",
  "ExpectedImprovement": "LogP ~3.5 → ~2.9. Adds 1 HBD + 1 HBA. Scaffold preserved.",
  "Confidence": "High"
}
```
**Lessons:** (1) One change at a time for fused ring systems. (2) Never append atoms outside ring closures — use parentheses `()` within the ring path. (3) Prefer the simpler edit.

# Critical Constraints & Warnings

⚠️ **DO NOT:**
- Break core pharmacophore structures essential for activity
- Create chemically unstable or impossible structures
- Introduce toxic functional groups (nitro-aromatics, reactive epoxides, etc.)
- Generate SMILES with syntax errors
- Make changes that violate multiple RO5 criteria simultaneously
- Drop or alter stereochemical markers (`@`, `@@`, `/`, `\`) from the source SMILES unless the modification directly targets that stereocenter

✅ **DO:**
- Maintain scaffold integrity when possible
- Use bioisosteric replacements when removing functional groups
- Consider synthetic accessibility
- Provide clear rationale for each modification
- Ensure output SMILES is valid and parsable
- Preserve all stereochemistry from the source molecule

# Output Format Requirement

Your response MUST be valid JSON format:
```json
{
  "Analysis": "Brief analysis of source molecule properties and issues",
  "OptimizationStrategy": "Step-by-step modification plan with rationale",
  "Final Target Molecule": "Valid SMILES string of optimized molecule",
  "ExpectedImprovement": "Description of expected property improvement",
  "Confidence": "High/Medium/Low based on modification complexity"
}
```

---

## step 3
Utilize skill **molclaw-smiles-valid-check** to validate the structural integrity of the molecule generated in step 2. If the molecule is invalid, analyze the root cause, reflect on the error, and re-execute step 2. Do NOT repeat the same modification that produced the invalid SMILES. If valid, proceed directly to step 4.

## step 4
Utilize skill **molclaw-admet** to calculate multiple physicochemical properties for the newly generated molecule and rigorously compare them with the source molecule. The primary objective is to **maximize the improvement** of target properties, aiming for substantial gains rather than marginal adjustments.

**Note**: If the user specifies particular optimization goals, **prioritize the user's specified goals** over the default targets listed below.

**Strict Improvement Thresholds (Default Targets)**:

- **LogP**: Change ≥ **2.5** in the desired direction (significantly stricter than previous standards).
- **QED**: Increase ≥ **0.5**  or QED score **reaches at least 0.9** (demanding a major leap in drug-likeness).
- **Solubility (LogS)**: Increase ≥ **4.0** (requiring a drastic enhancement in solubility).

If the target properties fail to meet these **elevated thresholds**, conduct a deep root-cause analysis and critically reflect on the optimization strategy. You must **re-execute step 2** with a fundamentally different approach. **Under no circumstances** should you repeat a strategy that previously failed to achieve these significant improvements.
---

## ⚠ Computation-First Principle (L3 Principle 13)

Property values used for optimization decisions (LogP, QED, solubility, ADMET) MUST come from tool computations (`pred_mol_admet`, `calculate_mol_drug_chemistry`, etc.), not from LLM chemical intuition. Each optimization rationale must cite the specific tool-computed value it aims to improve.

## ⚠ Data Integrity (L3 Principle 11)

Before writing any comparison table or optimization trajectory, verify each value against the actual tool return. Report exact tool-returned values, not rounded or estimated numbers.

---
name: molclaw-molecular-property-analysis-filtering
description: >
  Comprehensive small molecule property analysis, drug-likeness assessment, ADMET prediction,
  and compound library filtering. Can be used standalone or as a sub-module of other workflows.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 2 (Tiered screening — verify counts at tier boundaries),
      L3 Principle 9 (MW/formula consistency check),
      L3 Principle 10 (Three-category distinction: tool fact vs. agent inference vs. literature),
      L3 Principle 11 (Count-Before-Report — verify molecule counts after each filter stage),
      L3 Principle 13 (Computation-first — ADMET predictions are Level 1 direct computation; do not substitute with literature IC50/EC50)
---

# Molecular Property Analysis and Filtering Workflow

## Applicability

**Use this skill when:** The user provides molecules (SMILES, compound names, files) and needs property computation, drug-likeness assessment, ADMET prediction, or library filtering.

**Do NOT use this skill when:** The task requires only docking without property filtering (use Skill 2 directly); or the molecules are peptides/proteins (standard Lipinski rules do not apply — use Skill 10's sequence property tools instead).

**Special molecule types requiring adjusted thresholds:** Macrocycles, PROTACs, natural products, covalent inhibitors, and antibody-drug conjugate payloads violate Lipinski rules by design. When the task involves these molecule types, relax or skip Lipinski-based filters and note this in the report.

## Prerequisites

No upstream dependency. SMILES input only.

## Core Workflow

### Step 1: Input Acquisition and Standardization

Convert all inputs to a SMILES list. Compound names → `retrieve_smiles_by_compoundname`; direct SMILES → use directly; mixed → classify with `is_valid_smiles`.

Validate and deduplicate.

**⚠ COUNT GATE (L3 Principle 11 — MANDATORY):** After validation, programmatically count:
```
Total input: X molecules
Valid SMILES: Y molecules
Invalid SMILES: Z molecules (with reasons for each)
Unique after dedup: W molecules
```
These counts must come from the actual validation results. Record in `run_log.md` with the verification command used.

### Step 2: Three-Tier Property Analysis

**Tier 1 — Basic properties (ALWAYS execute).** This is the foundation for all downstream decisions.

Call the following tool-level skills:
- `calculate_mol_basic_info`: formula, MW, heavy atom count, bond count, formal charge
- `calculate_mol_hydrophobicity`: LogP, molar refractivity
- `calculate_mol_hbond`: HBD, HBA counts
- `calculate_mol_drug_chemistry`: QED score, Lipinski violation count
- `calculate_mol_structure_complexity`: rotatable bonds, ring count, aromatic ring count, Fsp³

**Mandatory consistency check (L3 Principle 9):** For each molecule, verify that the MW returned by `calculate_mol_basic_info` is consistent with the molecular formula. If MW and formula are inconsistent (e.g., C₁₄H₁₄O₃ cannot yield MW = 244.29), the SMILES was likely parsed incorrectly. Flag the molecule, re-validate the SMILES, and recompute. Do NOT silently accept inconsistent values.

**Tier 2 — Extended properties (execute when detailed analysis or fine-grained filtering is requested).**
- `calculate_mol_topology`: TPSA, topological descriptors. TPSA < 60 Å² → likely BBB-penetrant; TPSA > 140 Å² → poor oral bioavailability.
- `calculate_mol_charge`: Gasteiger charge statistics.
- `calculate_mol_complexity`: molecular complexity, aromaticity ratio, asphericity.

**Tier 3 — ADMET prediction (execute when drug evaluation, toxicity screening, or pharmacokinetic assessment is needed).**

Call `pred_mol_admet`. This returns 90+ ADMET endpoints.

**Computation-first declaration (L3 Principle 13):** ADMET predictions from `pred_mol_admet` are Level 1 direct tool computations. They are the authoritative source for ADMET data in this workflow. Do NOT substitute with literature IC50, EC50, or other experimental values unless the task explicitly asks for comparison with literature. When literature values are used for comparison, label them clearly: "⚠️ LITERATURE VALUE: ..." (see L3 Principle 13 protocol).

**Key ADMET indicators by priority:**

| Priority | Endpoint | Red flag threshold | Interpretation |
|----------|----------|-------------------|----------------|
| 🔴 Critical | hERG inhibition probability | > 0.7 | Cardiac toxicity risk |
| 🔴 Critical | ClinTox probability | > 0.7 | Clinical toxicity risk |
| 🔴 Critical | AMES mutagenicity probability | > 0.7 | Genotoxicity risk |
| 🟡 Warning | Caco-2 permeability | < −5.5 (log cm/s) | Poor absorption |
| 🟡 Warning | Any CYP inhibition probability | > 0.7 | Drug-drug interaction risk |
| 🟡 Warning | Plasma protein binding | > 95% | Low free fraction |
| 🟡 Warning | Water solubility (LogS) | < −6 | Formulation challenges |
| 🟢 Positive | BBB penetration probability | > 0.7 | Favorable for CNS targets |
| 🟢 Positive | Bioavailability prediction | > 0.7 | Good oral bioavailability |

**Mandatory annotation (L3 Principle 10):** All ADMET values MUST be labeled as Category 1 (tool-computed facts) with the annotation "ADMET-AI statistical prediction" in the report. Example: write "ADMET-AI predicts a CYP3A4 inhibition probability of 0.72 (statistical prediction)" — never "this molecule inhibits CYP3A4."

### Step 3: Filtering

Select filtering stringency based on task context:

| Mode | Criteria | Expected elimination | When to use |
|------|----------|---------------------|-------------|
| **None** | No filtering | 0% | User wants full characterization only |
| **Lenient** | Remove only extreme outliers: MW < 100 or > 1000; invalid SMILES | 5–15% | Early exploration, natural products, lead discovery |
| **Standard** (default) | Lipinski violations ≤ 2; QED ≥ 0.2; TPSA ≤ 140; RotBonds ≤ 12; no 🔴 ADMET flags | 15–40% | Routine virtual screening |
| **Strict** | Lipinski violations = 0; QED ≥ 0.4; Veber rules (RotBonds ≤ 10, TPSA ≤ 120); no 🔴 or 🟡 ADMET flags | 30–60% | Lead optimization, oral drug development |
| **Custom** | Map user's natural language criteria to specific field thresholds | Variable | User provides explicit criteria |

Default is Standard unless the user specifies otherwise or the molecule type requires adjustment.

**⚠ COUNT GATE after EACH filter stage (L3 Principle 11 — MANDATORY):**

After applying filters, programmatically count the molecules that passed and failed each criterion:

```python
# Count molecules passing each filter criterion
passed_lipinski = sum(1 for m in molecules if m['lipinski_violations'] <= 2)
passed_qed = sum(1 for m in passed_lipinski_list if m['qed'] >= 0.2)
# ... and so on for each criterion
```

Record the filtering funnel with verified counts:

```
## Filtering Funnel (all counts programmatically verified)
Input to filtering: W molecules (verified from validation output)
├── Lipinski ≤ 2: W₁ passed, W-W₁ eliminated
├── QED ≥ 0.2: W₂ passed, W₁-W₂ eliminated
├── TPSA ≤ 140: W₃ passed, W₂-W₃ eliminated
├── RotBonds ≤ 12: W₄ passed, W₃-W₄ eliminated
├── No 🔴 ADMET flags: W₅ passed, W₄-W₅ eliminated
Final output: W₅ molecules
```

**⚠ If the actual count of molecules passing filters differs from what you expected, report the ACTUAL count. A report saying "15 molecules passed all filters" when the file contains 15 entries is correct. A report saying "20 molecules passed" when only 15 are in the file is fabrication (L3 Principle 11).**

### Step 4: Similarity Analysis (optional)

If a reference molecule (known active, lead compound) is provided, call `calculate_morgan_fingerprint_similarity` to compute Tanimoto similarity for all candidates against the reference.

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| `retrieve_smiles_by_compoundname` returns nothing | Name not in PubChem or ambiguous | Ask user for SMILES directly; try alternative name/synonym |
| MW/formula inconsistency detected | SMILES parsing error, stereochemistry issue | Re-canonicalize SMILES; if still inconsistent, flag and exclude |
| ADMET prediction returns NaN for some endpoints | Molecule outside training domain | Report the missing predictions; do not impute values; do NOT substitute with literature values unless explicitly labeled |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after Step 1 (input acquisition):**
- [ ] All molecule counts file-verified (total → valid → unique)
- [ ] Invalid molecules recorded with specific reasons

**CHECKPOINT after Step 2 (property analysis):**
- [ ] MW/formula consistency verified for every molecule (L3 Principle 9)
- [ ] All ADMET predictions labeled as "ADMET-AI statistical prediction" (L3 Principle 10)
- [ ] RDKit-computed properties labeled as "deterministic computation"; ADMET-AI values labeled as "statistical prediction"
- [ ] ADMET probabilities are all within [0, 1] — values outside this range indicate tool error

**CHECKPOINT after Step 3 (filtering):**
- [ ] Per-criterion elimination counts are programmatically verified (L3 Principle 11)
- [ ] Filtering funnel recorded with verified counts at each stage
- [ ] Final filtered list count matches the number of entries in the output file

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Property table | CSV: SMILES, MW, LogP, HBD, HBA, QED, Lipinski_violations, TPSA, RotBonds, key ADMET flags, filter_status (pass/fail/reason) | Skills 2, 4, 5 | **A — MUST download** |
| Filtering summary | Markdown: per-tier verified statistics | Report | B — record in log |
| Similarity rankings (if computed) | CSV: SMILES, Tanimoto to reference | Skills 4, 5 | **A — MUST download** |

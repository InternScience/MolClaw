---
name: molclaw-protein-sequence-design-validation
description: >
  Structure-guided protein sequence design, mutation effect prediction, and multi-layer
  functional validation. Includes iterative refinement protocol and specialized thermostability
  enhancement with binding interface preservation strategy.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Section 6.3 (Protein design strategy — including thermostability-interface preservation),
      L3 Principle 4 (Iterative design), Principle 9 (Never trust single output),
      L3 Principle 11 (Count-Before-Report — verify design counts and validation metrics),
      L3 Principle 13 (Computation-first — stability predictions must come from tools),
      L3 Principle 14 (Mandatory structure file collection — download ESMFold predictions, Chai-1 complexes),
      L3 Principle 15 (Mandatory image file collection — download pLDDT plots, ProLIF outputs),
      L3 Principle 17 (Residue numbering reconciliation — map design positions to UniProt),
      L3 Principle 20 (Honest annotation of uncertainty)
---

# Protein Sequence Design and Validation Workflow

## Applicability

**Use this skill when:** The goal is to improve a protein's own properties — stability, solubility, expression level, enzyme activity, thermostability — through sequence design or mutation engineering.

**Do NOT use this skill when:** The goal is to design a peptide/protein that BINDS another target (use Skill 9); or small molecule optimization (use Skill 5).

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Protein 3D structure | Skill 1 `prepared_pdb` | Yes |
| Protein sequence | Skill 1 `fasta_path` | Yes |
| Numbering scheme info | Skill 1 `numbering_scheme` | Required (for residue mapping) |

## Scene Classification

| Scene | Goal | Core tool | Trigger |
|-------|------|-----------|---------| 
| **A: Full/partial sequence redesign** | Redesign sequence for improved properties | `proteinmpnn_tool` | "design protein sequence," "redesign for stability" |
| **B: Mutation effect prediction** | Identify beneficial mutations | `pred_mutant_sequence` (ProSST) | "predict mutation effects" |
| **C: Interface sequence design** | Optimize one side of a protein-protein interface | `proteinmpnn_tool` + ProLIF | "optimize binding interface" |
| **D: Homooligomer design** | Design symmetric multimers | `proteinmpnn_tool` `homooligomer` mode | "design symmetric dimer/trimer" |
| **E: Sequence scoring** | Evaluate compatibility of mutations | `proteinmpnn_tool` `score_only` mode | "score these mutants" |
| **F: Thermostability with interface preservation** | Maximize thermostability while preserving binding interfaces | `proteinmpnn_tool` + Chai-1 + ProLIF + conformational sampling | "improve stability without affecting binding," "thermostabilize while preserving interface" |

## ProteinMPNN Parameter Guide

**Model selection `model_name`:**

| Model | Backbone noise | Typical use |
|-------|---------------|-------------|
| `v_48_002` | 0.02 Å | Minimal changes; fine-tune existing sequence |
| `v_48_010` | 0.10 Å | Moderate optimization |
| `v_48_020` | 0.20 Å (**default**) | Standard design |
| `v_48_030` | 0.30 Å | Maximum novelty (patent circumvention, de-immunization) |

**`use_soluble`:** True for secreted/purified proteins. False for membrane proteins.

**`sampling_temp`:** Multi-temperature: `"0.1 0.2"` generates both conservative and diverse candidates.

**`omit_aas`:** `"X"` (default); `"CX"` (exclude Cys — **use this when the design goal does NOT involve introducing new disulfide bonds**, to prevent non-native disulfides); `"CMX"` (also exclude Met to prevent oxidation).

**Design scope control:**

| Scope | `fixed_positions` | Use when |
|-------|-------------------|----------|
| Full redesign | None | De novo fold, patent circumvention |
| Partial redesign | Fix catalytic, ligand-binding, disulfide Cys, core hydrophobics | Standard stability optimization |
| Surface-only redesign | Fix all buried residues | Solubility/expression improvement |

## Residue Position Mapping for Design (L3 Principle 17)

**Before specifying `fixed_positions` in ProteinMPNN**, translate between the task's residue numbering scheme and the structure's numbering scheme. ProteinMPNN uses the residue numbers in the input PDB file. If the task says "fix residues Met793, Thr790" (UniProt numbering) but the PDB uses different numbers, you must translate.

Record the mapping table in `run_log.md` and use the PDB's numbering when calling ProteinMPNN.

## Scene F: Thermostability Enhancement with Interface Preservation (L3 Section 6.3)

This is a constrained optimization: maximize protein thermostability while ensuring that specific binding interfaces remain intact. The core difficulty is that mutations improving thermostability in the protein core may propagate conformational changes to the interface, disrupting binding.

### Step F1: Define the Constraint Architecture

Partition ALL residues into three classes:

**Fixed (NEVER mutate):**
- All interface residues (both sides of each relevant interface)
- Structural cysteines forming disulfide bonds
- Catalytic residues
- User-specified essential residues

**Cautious (may mutate with validation):**
- Second-shell residues within 5 Å of fixed residues
- Residues in structurally critical regions (helix caps, turn residues)

**Free (preferred mutation targets):**
- Surface-exposed non-interface residues
- Loop regions distant from functional sites
- Positions where ProSST indicates tolerance for substitution

**Residue numbering (L3 Principle 17):** Build the mapping table FIRST, then classify residues using the structure's numbering while recording the task's numbering for reference.

**Cysteine constraint:** Use `omit_aas="CX"` unless the design explicitly requires new disulfide bonds. This prevents introduction of non-native cysteines that could form problematic disulfide bonds.

### Step F2: Multi-Round Design with Interface Validation

**Round 1: Baseline + Initial Design**

1. **Structure prediction baseline:** If no experimental structure is available, predict wild-type structure (ESMFold/Chai-1). Record pLDDT as baseline.
2. **Interface/pocket identification:** Run pocket detection or ProLIF protein-protein mode to define interface residues. **Download structure files.**
3. **Conformational sampling baseline:** Run BioEmu or OpenMM to characterize wild-type conformational diversity. **Download all trajectory/structure files.**
4. **ProteinMPNN design** with fixed interface residues, multiple temperatures (0.1, 0.2), ≥ 8 candidates.
5. **Score by NLL fitness.**

**⚠ COUNT GATE:** Verify actual number of designs generated from ProteinMPNN output.

**Round 2: Structural Validation + Refinement**

1. **Select top candidates by fitness** (typically top 3–5).
2. **Predict structure** of each designed sequence (ESMFold). **Download ALL predicted PDB files.**
3. **Critical diagnostic step — Per-residue pLDDT comparison:**
   - Compare designed sequence pLDDT with wild-type pLDDT at EVERY position.
   - Identify positions where design DECREASED local confidence → these positions may have been destabilized.
   - **Fix problematic positions** in next iteration.
   - Optionally open high-confidence positions that were previously cautious.
4. Generate refined candidates with updated constraints.

**Round 3: Interface Binding Validation**

1. **Complex structure prediction (Chai-1):** Predict complex of wild-type + binding partner AND top designed candidate + binding partner. **Download ALL complex structures.**
2. **Protein-protein docking (HDOCK):** Dock designed protein against binding partner. **Download docked complexes.**
3. **Interface interaction analysis (ProLIF protein-protein mode):** Compare wild-type and designed interactions. **Download ProLIF images.**
4. **Verify ALL fixed interface residues maintain native contacts.** Use mapped residue numbering.
5. **Conformational sampling comparison:** Run BioEmu/OpenMM on designed protein. **Download conformations.** Reduced conformational diversity relative to wild-type suggests improved thermostability.

**Key checkpoints specific to Scene F:**
- Were positions causing pLDDT drops in Round 2 correctly identified and constrained in subsequent rounds?
- Was the overall fold preserved throughout?
- Were critical interface contacts maintained?
- Did the final candidate show reduced conformational diversity relative to wild-type?

## ProSST Mutation Prediction (Scene B)

Call `pred_mutant_sequence` to predict mutation effects.

**Using ProSST to guide ProteinMPNN:** Run ProSST first, identify the top 10–20 mutable positions, then run ProteinMPNN with these as the only designable positions. This combined approach yields more conservative designs.

## Multi-Layer Validation (All Scenes)

### Layer 1: Self-Consistency Check

For each candidate sequence, predict its structure with `pred_protein_structure_esmfold` (single chain) or `chai1_predict` (multi-chain).

### Mandatory Structure Download (L3 Principle 14 — CRITICAL)

**Download the predicted structure for EVERY designed candidate:**
```python
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": esmfold_result["output_structure"]}
)
# Save as roundNN_candidate_MM_esmfold.pdb
```

**pLDDT assessment** via `calculate_pdb_quality_metrics`:
- \> 85: excellent
- 75–85: good
- 65–75: moderate — proceed with caution
- < 65: poor — likely design failure, discard

**Structural comparison limitation (L3 Principle 20):** "Direct backbone RMSD comparison is not available; self-consistency is assessed primarily through pLDDT confidence. High pLDDT (>85) provides strong evidence of a stable fold, but structural identity with the design template is inferred, not directly measured."

### Layer 2: Sequence Property Assessment

Call `calculate_protein_sequence_properties`. Compare designed vs. wild-type.

### Layer 3: Sequence Recovery and Mutation Analysis

**Recovery rate:** Fraction of designed positions retaining wild-type amino acid.

**Mutation classification by region (using mapped numbering):**
- Core mutations: high risk — flag each one
- Surface mutations: low risk
- Active site proximal mutations: high scrutiny

## Composite Ranking

| Design goal | pLDDT weight | Stability Δ weight | MPNN NLL weight | Recovery weight | Solubility Δ weight |
|-------------|-------------|-------------------|-----------------|-----------------|-------------------| 
| Stability | 0.35 | 0.25 | 0.20 | 0.10 | 0.10 |
| Solubility | 0.25 | 0.15 | 0.15 | 0.10 | 0.35 |
| Thermostability + interface (Scene F) | 0.25 | 0.20 | 0.15 | 0.10 | 0.05 + Chai-1 ipTM: 0.15 + Interface conservation: 0.10 |
| Interface binding | Replace stability with Chai-1 ipTM (0.35) and HDOCK (0.10) | | | |

## Iteration Protocol (L3 Principle 4)

**Round 1: Initial design.** Generate 5–10 candidates. Validate through Layers 1–3.

**Before Round 2, answer three questions (L3 Principle 5):**
1. "Round 1 best candidate has pLDDT 78 but instability_index increased by 15% (verified from tool return)."
2. "Fix the 5 positions that ProSST identified as intolerant; redesign only surface positions."
3. "pLDDT > 82 AND instability_index ≤ wild-type value."

**Round 2:** Adjust parameters. More conservative if Round 1 was too aggressive; more aggressive if too conservative.

**Round 3 (if needed):** Combinatorial optimization — combine best mutations from Rounds 1 and 2.

**Convergence:** pLDDT > 80 AND targets improved; or < 5% improvement for 2 rounds; or 3 rounds max (4 for Scene F).

### Round-Level Verification (L3 Principle 12 Checkpoint B)

Before writing any round summary:
```
### Round N Verification
- Designs generated: [verified count from ProteinMPNN output]
- pLDDT scores: [verified from ESMFold output per candidate]
- Property improvements: [verified from tool returns]
- Structure files downloaded: [list with sizes]
- All data verified: ✅
```

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| All designs pLDDT < 65 | Too many core mutations | More conservative model; fix core positions |
| ProteinMPNN produces identical sequences | Temperature too low; too many fixed positions | Increase `sampling_temp`; try multi-temperature |
| ProSST predicts all mutations destabilizing | Protein highly optimized | Surface-only redesign; accept limited improvement |
| Scene F: Interface contacts lost after design | Core mutations propagated to interface | Fix second-shell positions; increase fixed region |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after design generation:**
- [ ] Design count verified from output file
- [ ] All predicted structures downloaded and verified

**CHECKPOINT after validation:**
- [ ] pLDDT scores verified from tool returns
- [ ] RMSD limitation honestly stated in report
- [ ] Mutations classified by region (with mapped numbering)
- [ ] For Scene F: interface conservation verified against wild-type ProLIF

**CHECKPOINT before final report:**
- [ ] All structure files accounted for in file inventory
- [ ] All metrics in trajectory table file-verified
- [ ] Residue mapping table included

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Top candidate sequences | CSV: sequence, pLDDT, stability metrics, NLL | Report | **A — MUST download** |
| Predicted structures | PDB per candidate | User verification | **A — MUST download** |
| Mutation list | CSV: position (mapped), WT_aa, designed_aa, region | Report | **A — MUST download** |
| Validation summary | Markdown | Report | B — record in log |
| Iteration trajectory | Table with verified values | Report | B — record in log |
| ProLIF images (Scene F) | PNG/SVG | Report | **A — MUST download** |
| Chai-1 complexes (Scene F) | PDB/CIF | User verification | **A — MUST download** |
| Residue mapping table | CSV | Report | **A — MUST download** |

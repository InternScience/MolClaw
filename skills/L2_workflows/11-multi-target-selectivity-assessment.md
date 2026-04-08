---
name: molclaw-multi-target-selectivity-assessment
description: >
  Multi-target cross-docking and selectivity assessment. Dock candidates against multiple
  homologous targets, analyze interaction fingerprint differences, identify selectivity-
  determining residues, and guide selectivity optimization.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 3 (More than one method),
      L3 Principle 10 (Three-category distinction),
      L3 Principle 9 (Do not convert docking ΔScore to selectivity fold-change via ΔG=RT·ln(Kd)),
      L3 Principle 11 (Count-Before-Report — verify docking counts across targets),
      L3 Principle 13 (Computation-first — cross-target alignment must be computationally derived, not from LLM knowledge),
      L3 Principle 14 (Mandatory structure file collection — download docking poses for ALL targets),
      L3 Principle 15 (Mandatory image file collection — download ProLIF comparison heatmaps),
      L3 Principle 17 (Residue numbering reconciliation — CRITICAL for cross-target comparison),
      L3 Principle 18 (Docking parameter safeguards — minimum 25 Å box, identical parameters across targets)
---

# Multi-Target Selectivity Assessment Workflow

## Applicability

**Use this skill when:** The user has multiple homologous targets (e.g., CDK2/CDK4/CDK6, JAK1/JAK2/JAK3, Aurora A/B) and candidate molecules, and needs to assess selectivity.

**Do NOT use this skill when:** There is only one target (use Skill 2); the targets are unrelated (not homologous); or the task is optimizing selectivity without initial docking data (start with Skill 2).

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Multiple target protein structures | Skill 1 `prepared_pdb` (one per target) | Yes |
| Numbering scheme info per target | Skill 1 `numbering_scheme` (one per target) | Required |
| Candidate molecule SMILES | User or Skill 2/4/5 output | Yes |
| Known experimental selectivity data | User or literature | Optional |

## Core Workflow

### Step 1: Multi-Target Structure Preparation

For each target protein, execute Skill 1 independently. Record for each:
- Structure source and resolution
- Conformational state
- Whether a co-crystal ligand was present
- **Numbering scheme** (L3 Principle 17 — CRITICAL)

### Cross-Target Residue Alignment (L3 Principles 13 + 17 — MUST be computationally derived)

**⚠ This is a COMPUTATION-FIRST step.** The cross-target alignment must be derived from actual sequence/structural data, NOT from LLM training knowledge about protein families.

**Method 1 (preferred): Programmatic sequence alignment.**
```python
# Extract sequences from both target PDB files
# Align using residue_mapper.py or simple positional alignment
# Build cross-target correspondence table
```

**Method 2: DBREF-based UniProt mapping.**
For each target, extract the DBREF record → UniProt residue mapping. Then align via shared UniProt residue numbers.

**Method 3: residue_mapper.py with shared UniProt ID (if available).**
If homologous targets map to different UniProt IDs (e.g., CDK2 = P24941, CDK4 = P11802), build separate UniProt mappings, then align by conserved positions using sequence comparison.

**Build a cross-target alignment table:**

```
## Cross-Target Residue Alignment
| Functional role | Target 1 (UniProt/PDB/tool) | Target 2 (UniProt/PDB/tool) | Conservation |
|----------------|---------------------------|---------------------------|--------------|
| Gatekeeper | Thr790/Thr766/Thr122 (EGFR) | Thr315/Thr315/Thr47 (ABL) | Different AA |
| Hinge | Met793/Met769/Met125 (EGFR) | Met318/Met318/Met50 (ABL) | Conserved |
```

**Record the alignment table in `run_log.md` with the derivation method.** This table is essential for all downstream selectivity interpretation.

**⚠ FORBIDDEN:** Using LLM knowledge to state "the gatekeeper residue in CDK2 is Phe80" without computationally verifying this from the actual structure files. Even if correct, the information must be traced to a computational source.

### Step 2: Independent Pocket Detection Per Target

For each target, run both `fpocket_toolkit` and `pred_pocket_prank` (L3 Principle 3).

Verify that pocket residues in each target map to the same alignment positions.

### Step 3: Cross-Docking

Dock ALL candidate molecules against ALL target pockets using QuickVina.

**Docking parameter consistency (L3 Principle 18):**
- Use **identical parameters** across all targets: same box size (≥ 25 Å per dimension), same exhaustiveness.
- Document these parameters explicitly.
- If the pocket sizes differ significantly between targets, use the LARGER box size for ALL targets.

### Mandatory Cross-Docking Pose Download (L3 Principle 14 — CRITICAL)

**Download docking pose files for ALL (molecule × target) combinations:**
```python
for target in targets:
    for molecule in molecules:
        # Download pose PDBQT
        local_path = f"step{N}_{molecule_id}_{target_name}_pose.pdbqt"
        # ... server_file_to_base64 → local save → verify size > 0
```

**⚠ COUNT GATE (L3 Principle 11):** After cross-docking, verify the complete docking matrix:
```
Cross-docking verification:
- Molecules: M (verified)
- Targets: T (verified)
- Expected combinations: M × T = X
- Successful dockings: Y (verified by counting negative-score results)
- Failed dockings: X - Y (listed with reasons)
```

**Record the complete docking matrix with verified scores:**

| Molecule | Target 1 Vina | Target 2 Vina | Target 3 Vina | ΔScore (T1−T2) | ΔScore (T1−T3) |
|----------|--------------|--------------|--------------|----------------|----------------|
| Mol A | −8.5 | −6.2 | −7.1 | **−2.3** | −1.4 |
| Mol B | −7.8 | −7.5 | −7.3 | −0.3 | −0.5 |

### Step 4: Multi-Method Selectivity Scoring

**EquiScore cross-validation:** Run EquiScore on ALL (molecule × target) combinations. Compare Vina-based and EquiScore-based selectivity rankings.

**Boltz-2 binding probability (optional):** Predict binding probability for each pair.

**Download structure files from Boltz-2/EquiScore** (L3 Principle 14).

### Step 5: Interaction Fingerprint Differential Analysis

For each candidate molecule, run ProLIF on its docking pose in EACH target.

### Residue Numbering Mapping for Cross-Target ProLIF (L3 Principle 17 — CRITICAL)

**This is the most error-prone step in multi-target selectivity analysis.** ProLIF reports residue IDs using the numbering of each target's PDB file. Different target PDB files almost certainly use different numbering schemes. Before comparing interaction fingerprints across targets, ALL residue IDs must be mapped to a common reference scheme (typically UniProt or the cross-target alignment table).

**MAPPING GATE — Execute for EACH target's ProLIF output:**
1. Map ProLIF residue IDs → PDB author numbering → UniProt numbering (using the per-target mapping from Step 1).
2. Align across targets using the cross-target alignment table.
3. Compare interactions at the SAME alignment positions across targets.

CORRECT: "ProLIF detected HBond at Ala145 (Target1 Boltz-2 internal) = Ala743 UniProt. In Target2, the aligned position is Pro298 UniProt = Pro45 (Target2 Boltz-2 internal). ProLIF shows no HBond at Pro45 in Target2. This position (Ala743→Pro298) is a selectivity-determining residue."

WRONG: "ProLIF detected HBond at Ala145 in Target1 but not in Target2. This is a target-specific interaction." (Without mapping, Ala145 in Target1 and Ala145 in Target2 are NOT necessarily the same position.)

### Post-ProLIF Image Download (L3 Principle 15)

Download ALL ProLIF heatmaps for ALL targets. Download any comparison/overlay images.

**Analysis checklist:**
- **Target-specific interactions:** Present in desired target, ABSENT in off-targets → selectivity basis
- **Off-target-specific interactions:** Present in off-targets, absent in desired target
- **Conserved interactions:** Present in all targets → not relevant to selectivity

**Selectivity-determining residues:** Positions where BOTH (a) amino acid identity differs AND (b) interaction fingerprint differs. Identify using the cross-target alignment table.

### Step 6: Selectivity Optimization Recommendations

Based on Step 5's differential analysis (grounded in tool-computed data — L3 Principle 13):
- Which modifications enhance interactions with target-specific residues?
- Which modifications introduce clashes with off-target-specific residues?
- Are there packing differences to exploit?

**Computation-first rule:** Optimization recommendations must cite specific ProLIF-identified interactions and cross-target alignment positions. CORRECT: "Extending the molecule toward alignment position 523 (Thr in Target1, Lys in Target2) could exploit the size difference." WRONG: "Kinase selectivity is typically achieved through exploiting the gatekeeper residue" (generic LLM knowledge).

### Step 7: Experimental Data Comparison (if available)

If experimental IC₅₀ data is available:
- Compare computed selectivity DIRECTION with experimental direction
- **⚠ Do NOT compute selectivity fold-change from docking scores** (L3 Principle 9). ΔG = RT·ln(Kd) requires exact free energies; docking scores are approximations. Only the ranking direction is meaningful.
- If directions agree → high confidence. If disagree → discuss causes.

## Iteration Protocol

If initial cross-docking shows no selectivity:
1. **Diagnose:** Are pocket residues identical across targets?
2. **Try alternative pockets:** Check allosteric sites.
3. **Design for selectivity:** Use selectivity-determining residues to guide Skill 5 or Skill 4.
4. **Re-assess:** Re-run cross-docking with new molecules.

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| ΔScores all near zero | Pocket sequences very conserved | Focus on allosteric sites; design larger molecules |
| Docking fails for one target | Structure quality issue | Re-prepare; try different PDB; use predicted structure |
| ProLIF identical across targets | Box too small; peripheral differences missed | Increase box; include 2nd-shell residues |
| Cross-target residue comparison incorrect | Numbering mismatch | **Rebuild cross-target alignment table from scratch** |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after Step 1 (preparation):**
- [ ] All target structures prepared with documented numbering schemes
- [ ] Cross-target alignment table built computationally (not from LLM knowledge)
- [ ] Alignment table recorded in run_log.md

**CHECKPOINT after Step 3 (cross-docking):**
- [ ] All targets used identical docking parameters (including box ≥ 25 Å)
- [ ] Complete docking matrix verified (M × T combinations counted)
- [ ] All docking pose files downloaded
- [ ] Failed dockings explained

**CHECKPOINT after Step 5 (interaction analysis):**
- [ ] ProLIF residue IDs mapped to common reference scheme for ALL targets
- [ ] Selectivity-determining residues verified against cross-target alignment
- [ ] All ProLIF images downloaded

**CHECKPOINT before report:**
- [ ] No docking ΔScore converted to Kd selectivity ratio
- [ ] All selectivity claims grounded in tool-computed interactions
- [ ] Residue alignment table included in report
- [ ] All structure files and images in file inventory

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Cross-docking matrix | Table with verified scores and ΔScores | Report | **A — MUST download** |
| Docking pose files | PDBQT per (molecule × target) | Archive, user verification | **A — MUST download** |
| Selectivity ranking | CSV: molecule, ΔScores, consistency | Report | **A — MUST download** |
| ProLIF comparison | Per-molecule per-target interaction fingerprints (mapped) | Report, Skill 5 | **A — MUST download** |
| ProLIF images | PNG/SVG per target | Report | **A — MUST download** |
| Cross-target alignment table | CSV: alignment_position, target1_AA, target2_AA | Skill 5, Report | **A — MUST download** |
| Selectivity-determining residues | Table: alignment position, AA difference, interaction difference | Skill 5, Skill 4 | **A — MUST download** |
| Optimization recommendations | Markdown citing specific tool-computed data | Skill 5, Skill 4 | B — record in log |

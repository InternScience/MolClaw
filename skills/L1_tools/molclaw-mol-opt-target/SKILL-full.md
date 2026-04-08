---
name: molclaw-mol-opt-target
description: Integrating protein-ligand binding assessment tools, generative molecular models, and LLM reasoning to optimize drug molecular structures and enhance their binding activity against specific targets.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Optimization for Protein Target Binding

> **Global Rule — Optimization History**
>
> Maintain a running record of all optimization attempts throughout the workflow. Each time step 2 is executed (including retries), append the result. When re-entering step 2, the FULL history must be included so the LLM can avoid repeating failed strategies.

---

## step 1 — Baseline Evaluation & Binding Analysis

### 1.1 Binding Activity Evaluation
Utilize **molclaw-boltz2-affinity** and **molclaw-quickvina-docking** to evaluate binding between the source molecule (ligand) and target protein (receptor).

Record the baseline metrics:
| Metric | Value |
|--------|-------|
| QuickVina docking score (kcal/mol) | ... |
| Boltz2 affinity_pred_value (log10(IC50) μM) | ... |
| Boltz2 affinity_probability_binary | ... |

### 1.2 Interaction Analysis
Convert the Boltz2 complex structure and analyze protein-ligand interactions:

```python
# Convert CIF to PDB
response = await client.session.call_tool(
    "convert_complex_cif_to_pdb",
    arguments={"cif_file_path": complex_cif_file}
)
complex_pdb_path = client.parse_result(response)["output_file"]

# Analyze interactions
response = await client.session.call_tool(
    "analyze_protein_ligand_interactions",
    arguments={
        "complex_file": complex_pdb_path,
        "ligand_identifier": "auto"
    }
)
interaction_data = client.parse_result(response)
interactions = interaction_data["interactions"]       # H-bonds, hydrophobic, pi-stacking, etc.
pocket_summary = interaction_data["summary"]           # contacted residues, pocket composition
clashes = interaction_data["clashes"]                  # steric clashes to resolve
```

From the interaction data, identify:
- **Key interactions to preserve**: Strong H-bonds and salt bridges that anchor the ligand — these must NOT be disrupted by modifications
- **Weak or missing interactions**: Residues within contact range but forming only weak interactions — opportunities to strengthen
- **Steric clashes**: Ligand atoms too close to protein residues — must be resolved
- **Pocket composition**: Hydrophobic vs. polar character of the surrounding residues — guides what type of modifications to attempt

### 1.3 Source Molecule Property Profiling
Calculate precise molecular properties (do NOT rely on LLM estimation):

```python
smiles_list = [source_smiles]

# Option A: Comprehensive ADMET (preferred — one call covers everything)
response = await client.session.call_tool(
    "pred_mol_admet",
    arguments={"smiles_list": smiles_list}
)
admet_data = client.parse_result(response)

# Option B: Individual property calls if only drug-likeness needed
# calculate_mol_basic_info → MW
# calculate_mol_hydrophobicity → LogP
# calculate_mol_hbond → HBD, HBA
# calculate_mol_structure_complexity → rotatable bonds, rings, Fsp3
# calculate_mol_drug_chemistry → QED, Lipinski violations
```

### 1.4 Structural Analysis Report
Based on the above data, generate a report covering:
- **Baseline scores** from 1.1
- **Interaction profile** from 1.2: list key H-bonds (residue, distance, strength), hydrophobic contacts, pi-stacking, salt bridges, and any clashes
- **Property profile** from 1.3 (exact values from tools)
- **Modification site candidates** (2-4 positions): for each, state:
  - Which interaction data motivates this choice (e.g., "no H-bond to nearby ASP189", "clash with VAL138", "uncontacted polar residue SER195")
  - Which strategy from step 2 could apply
- **Existing concerns**: Lipinski violations, ADMET red flags, structural alerts

---

## step 2 — Dual-Track Molecule Generation

Execute **both tracks** to maximize the chance of finding improved molecules.

### Track A: LLM-Guided Design

Based on the Structural Analysis Report from step 1, the optimization_history (if any), and the following prompt, design 1-2 optimized molecules.

---

**Role**: Expert medicinal chemist specializing in structure-based lead optimization.

**Available Information**:
- Source molecule SMILES and exact property profile from step 1
- Protein-ligand interaction data from step 1: specific residue contacts, H-bonds, hydrophobic contacts, clashes
- Baseline binding scores (Vina, Boltz2)
- Protein target identity (use your knowledge of this target if available)
- Optimization history from previous attempts (if any)

**Strategy Options** — choose 1-2 modifications from:
- **Strategy A — Fill unoccupied space**: Extend toward residues in the pocket that are NOT currently contacted (identified from interaction data). Add small groups (-CH₃, -F, -Cl, -CF₃, -OH, cyclopropyl) directed at these residues.
- **Strategy B — Enhance H-bond capability**: Add or reposition H-bond donors/acceptors to target specific nearby polar/charged residues identified in interaction data (benzene→pyridine, -CH₂-→-NH-, -CH₃→-OH).
- **Strategy C — Improve hydrophobic contacts**: Strengthen hydrophobic interactions with specific nonpolar residues identified in interaction data.
- **Strategy D — Resolve steric clashes**: Trim or replace groups flagged as clashing in interaction data.
- **Strategy E — Rigidify flexible regions**: Reduce rotatable bonds by cyclization to decrease entropic penalty, especially for flexible linkers not involved in key interactions.
- **Strategy F — Bioisosteric scaffold modification**: Replace ring systems or functional groups to alter electronic/size/H-bond properties while maintaining the overall binding mode.

**Critical Rule**: Every modification MUST cite specific interaction data from step 1 — which residue, which interaction type, what distance. Modifications without interaction-based justification are not allowed.

**Hard Constraints**:
- MW ≤ 600 Da, LogP ≤ 6.0, HBD ≤ 7, HBA ≤ 12, Rotatable bonds ≤ 12
- No PAINS substructures (rhodanines, quinones, catechols, hydroxyphenyl hydrazones)
- No toxic motifs (nitro-aromatics, anilines, hydrazines)
- Preserve stereochemistry markers (`@`, `@@`, `/`, `\`) unless directly modifying that center
- Do NOT repeat any strategy recorded as failed in optimization_history
- Do NOT disrupt interactions marked as "strong" in the interaction data unless replacing with a stronger one

**SMILES Generation Rules**:
- Make only 1-2 changes at a time
- For fused ring systems: ONE change only, insert via parentheses `()` within ring path
- Never append atoms outside ring closure digits
- Verify ring closures matched, valence correct, parentheses balanced

**Output Format**:
```json
{
  "Analysis": "Key findings from step 1: scores, key interactions, clashes, property issues",
  "InteractionTarget": "Which specific residue(s) and interaction(s) this modification targets, citing data from step 1 (e.g., 'ASP189 currently at 4.1Å with weak H-bond, aim to strengthen to <3.0Å')",
  "Strategy": "Which strategy (A-F), targeting which modification site",
  "Modification": "Exact structural change at atom/group level",
  "Rationale": "Why this change should improve the targeted interaction",
  "Final Target Molecule": "Valid SMILES string",
  "Confidence": "High/Medium/Low"
}
```

---

### Track B: REINVENT Generative Sampling

Use generative models to produce a diverse set of candidate molecules:

```python
# Primary: MMP-style local modifications (best for lead optimization)
response = await client.session.call_tool(
    "reinvent_mol2mol_sampling",
    arguments={
        "smiles": source_smiles,
        "n": 20,
        "min_similarity": 0.55,
        "prior_type": "mmp",
        "lipinski": True,
        "filter_preset": "default"
    }
)
mmp_candidates = client.parse_result(response)["output_smiles_list"]

# Secondary: High-similarity conservative exploration
response = await client.session.call_tool(
    "reinvent_mol2mol_sampling",
    arguments={
        "smiles": source_smiles,
        "n": 10,
        "min_similarity": 0.65,
        "prior_type": "high_similarity",
        "lipinski": True,
        "filter_preset": "default"
    }
)
highsim_candidates = client.parse_result(response)["output_smiles_list"]
```

Combine all candidates: LLM-designed molecules from Track A + REINVENT molecules from Track B.

**Optional Track C: RL Property Optimization (when ADMET improvement is also a goal).** If the task requires simultaneous improvement of binding AND physicochemical properties (e.g., "improve binding and reduce CYP3A4 liability"), use `reinvent_similarity_optimization` to generate candidates optimized for specific property ranges while maintaining similarity to the source:

```python
response = await client.session.call_tool(
    "reinvent_similarity_optimization",
    arguments={
        "target_smiles": source_smiles,
        "similarity_weight": 0.5,
        "fp_radius": 2,
        "qed_weight": 0.2,
        "mmp_weight": 0.0,
        "mw_weight": 0.1, "mw_low": 300, "mw_high": 500,
        "logp_weight": 0.1, "logp_low": 1, "logp_high": 3,
        "tpsa_weight": 0.1, "tpsa_low": 60, "tpsa_high": 130,
        "max_steps": 100
    }
)
rl_candidates = client.parse_result(response)["output_smiles_list"]
all_candidates = llm_designed + mmp_candidates + highsim_candidates + rl_candidates
```

Note: RL-optimized candidates still require docking and interaction analysis validation — RL scoring is property-based, not structure-based.

---

## step 3 — Validation & Property Filtering

### 3.1 SMILES Validity Check
```python
all_candidates = llm_designed + mmp_candidates + highsim_candidates
response = await client.session.call_tool(
    "is_valid_smiles",
    arguments={"smiles_list": all_candidates}
)
valid_results = client.parse_result(response)["valid_res"]
valid_smiles = [r["smiles"] for r in valid_results if r["is_valid"]]
```

If any LLM-designed molecule is invalid:
- Record the invalid SMILES and error in optimization_history
- Analyze root cause (ring closure? valence? aromaticity?)
- Re-execute Track A of step 2 with the error context. Do NOT retry the same SMILES editing pattern.

### 3.2 Similarity Filter
```python
response = await client.session.call_tool(
    "calculate_smiles_similarity",
    arguments={
        "target_smiles": source_smiles,
        "candidate_smiles_list": valid_smiles
    }
)
sim_results = client.parse_result(response)["similarities"]
# Keep molecules with similarity 0.4-0.95 (not too different, not identical)
filtered_smiles = [r["smiles"] for r in sim_results if 0.4 <= r["score"] <= 0.95]
```

### 3.3 Drug-likeness & ADMET Filter
```python
# Quick drug-likeness check
response = await client.session.call_tool(
    "calculate_mol_drug_chemistry",
    arguments={"smiles_list": filtered_smiles}
)
drugchem = client.parse_result(response)["metrics"]
# Remove molecules with Lipinski violations > 1
druglike_smiles = [m["smiles"] for m in drugchem if m["lipinski_rule_of_5_violations"] <= 1]

# Full ADMET for final candidates (optional but recommended)
response = await client.session.call_tool(
    "pred_mol_admet",
    arguments={"smiles_list": druglike_smiles}
)
admet_results = client.parse_result(response)
# Flag and remove candidates with severe toxicity (ClinTox > 0.7, hERG > 0.7)
```

Molecules passing all filters proceed to step 4.

---

## step 4 — Binding Evaluation & Selection

### 4.1 Batch Binding Evaluation
Evaluate all filtered candidates using **molclaw-boltz2-affinity** and **molclaw-quickvina-docking**.

### 4.2 Ranking
Rank all evaluated candidates:
- **Primary**: QuickVina score (more negative = better)
- **Secondary**: Boltz2 affinity_pred_value (lower log10(IC50) = more potent)
- **Constraint**: Must pass drug-likeness filters from step 3

Present results as a comparison table:
| Rank | SMILES | Source | Vina (kcal/mol) | Δ Vina | Boltz2 pred_value | Δ Boltz2 | Similarity | QED |
|------|--------|--------|-----------------|--------|-------------------|----------|------------|-----|
| 0 | (source) | baseline | ... | — | ... | — | 1.0 | ... |
| 1 | ... | LLM / MMP / HighSim | ... | ... | ... | ... | ... | ... |
| ... | | | | | | | | |

### 4.3 Success Criteria
The optimization is **successful** if the top-ranked molecule achieves EITHER:
- QuickVina improvement ≥ 0.5 kcal/mol vs. source, OR
- Boltz2 affinity_pred_value meaningful improvement vs. source

If successful → proceed to 4.5 (final output).

### 4.4 If Improvement is Insufficient

**Interaction-based root-cause analysis for top candidates:**
For the top-3 candidates, run interaction analysis to compare with the source molecule:

```python
for candidate_smiles in top3_smiles:
    # Run Boltz2 → get complex_cif_file
    # Convert CIF → PDB
    # Run analyze_protein_ligand_interactions
    # Compare interaction profile with source molecule's interaction profile from step 1
```

Analyze:
1. **Interaction comparison**: Did the intended new interaction actually form? Did existing strong interactions break?
2. **Score divergence**: Vina improved but Boltz2 worsened (or vice versa) → binding mode may have shifted
3. **REINVENT diversity**: Were generated candidates too conservative (all very similar to source) or too diverse (lost key interactions)?
4. **Clash analysis**: Did modifications resolve old clashes or introduce new ones?

**Record analysis in optimization_history**, then re-execute step 2 with:
- Full optimization_history
- Root-cause findings with specific interaction data
- For Track A: different strategy type + different modification site + interaction evidence for new approach
- For Track B: different REINVENT prior_type (e.g., if `mmp` was used, try `scaffold` or `medium_similarity`)

### 4.5 Retry Limit
- **Maximum 2 retries** (3 total rounds). Each round already evaluates ~30 molecules (LLM + REINVENT), so 3 rounds covers ~90 candidates — sufficient exploration.
- If no candidate meets success criteria after all rounds:
  1. Report the **best molecule across all rounds** (by Vina score, with Boltz2 as tiebreaker)
  2. Provide the complete comparison table of all evaluated molecules
  3. Attach ADMET profile comparison between source and best candidate
  4. Summarize strategies attempted, outcomes, and recommendations for next steps

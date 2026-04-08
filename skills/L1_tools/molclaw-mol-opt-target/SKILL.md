---
name: molclaw-mol-opt-target
description: Optimize drug molecular structures to enhance binding activity against specific protein targets, using binding assessment tools, interaction analysis, and LLM-guided molecular design.
license: MIT license
metadata:
    skill-author: PJLab
---

# Molecule Optimization for Protein Target Binding

## step 1 — Baseline Evaluation

Evaluate the source molecule against the target protein. Run all tools below and collect results.

### 1.1 Target protein retrieval

Use skill **molclaw-protein-sequence-retrieve** and **molclaw-protein-structure-retrieve** to obtain target protein sequence and structure, respectively.

### 1.2 Binding Activity Evaluation

Utilize **molclaw-boltz2-affinity** and **molclaw-quickvina-docking** to evaluate binding between the source molecule (ligand) and target protein (receptor).

Record the baseline metrics:

| Metric                                      | Value |
| ------------------------------------------- | ----- |
| QuickVina docking score (kcal/mol)          | ...   |
| Boltz2 affinity_pred_value (log10(IC50) μM) | ...   |
| Boltz2 affinity_probability_binary          | ...   |

### 1.3 Interaction Analysis

Convert the Boltz2 complex structure and analyze protein-ligand interactions:

```python
response = await client.session.call_tool("convert_complex_cif_to_pdb", arguments={"cif_file_path": complex_cif_file})
complex_pdb = client.parse_result(response)["output_file"]

response = await client.session.call_tool("analyze_protein_ligand_interactions", arguments={"complex_file": complex_pdb, "ligand_identifier": "auto"})
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

### 1.4 Source Molecule Property Profiling

Use skill **molclaw-admet** to calculate precise molecular properties for the source molecule  (do NOT rely on LLM estimation).

### 1.5 Structural Analysis Report

Based on the above data, generate a report covering:

- **Baseline scores** from 1.2
- **Interaction profile** from 1.3: list key H-bonds (residue, distance, strength), hydrophobic contacts, pi-stacking, salt bridges, and any clashes
- **Property profile** from 1.4
- **Modification site candidates** (2-4 positions): for each, state:
  - Which interaction data motivates this choice (e.g., "no H-bond to nearby ASP189", "clash with VAL138", "uncontacted polar residue SER195")
  - Which strategy from step 2 could apply
- **Existing concerns**: Lipinski violations, ADMET red flags, structural alerts

## step 2 — Generate Optimized Molecules

Based on the Structural Analysis Report from step 1, design **1-3 optimized molecules**. Every modification MUST cite a specific residue and interaction from step 1.

**Generation approach — LLM design + REINVENT supplement:**
- **Primary:** LLM-guided design (1-3 molecules per round) based on interaction analysis
- **Supplement:** If LLM designs produce invalid SMILES repeatedly, or if more diversity is needed, use `reinvent_mol2mol_sampling` with `prior_type="scaffold_generic"` and `n=10-15` to generate additional candidates. Filter these by scaffold preservation and similarity, then dock all valid molecules.
- **For ADMET-focused optimization:** If step 1 reveals ADMET deficiencies alongside binding targets, use `reinvent_similarity_optimization` to generate candidates optimized for specific property ranges (QED, LogP, TPSA), then evaluate binding via docking.

**Rules:**
- Each molecule: only 1-2 structural changes from source
- For fused/polycyclic rings: ONE change only, insert substituents via `()` within the SMILES ring path, never append atoms after ring closure digits
- Do not disrupt strong interactions identified in step 1
- Do not introduce PAINS substructures or known toxicophores
- Preserve stereochemistry markers (`@`, `@@`, `/`, `\`) unless directly modifying that center
- If retrying: do NOT repeat any previously failed strategy. Use a different modification site or approach.

**Output per molecule:**
```json
{
  "InteractionTarget": "Which residue/interaction this targets, citing step 1 data",
  "Modification": "Exact structural change",
  "SMILES": "optimized molecule SMILES",
  "Confidence": "High/Medium/Low"
}
```

**Example:**
Source `c1ccc(-c2ccc(NC(=O)C)cc2)cc1`, Vina -6.8. Step 1 shows ASP189 at 4.1Å with no H-bond; terminal phenyl has only weak hydrophobic contacts with LEU134.
```json
{
  "InteractionTarget": "ASP189 at 4.1Å, currently no H-bond. Adding pyridine N as H-bond acceptor.",
  "Modification": "Replace terminal benzene with pyridine: c1ccccc1 → c1ccncc1",
  "SMILES": "c1ccnc(-c2ccc(NC(=O)C)cc2)c1",
  "Confidence": "High"
}
```

## step 3 — Validate & Filter

```python
# 1. Validity check
response = await client.session.call_tool("is_valid_smiles", arguments={"smiles_list": candidate_smiles_list})
valid = [r["smiles"] for r in client.parse_result(response)["valid_res"] if r["is_valid"]]
# If an LLM-designed molecule is invalid: note the error, regenerate in step 2 with a simpler edit. Do NOT retry the same SMILES pattern.

# 2. Drug-likeness filter
response = await client.session.call_tool("calculate_mol_drug_chemistry", arguments={"smiles_list": valid})
passed = [m["smiles"] for m in client.parse_result(response)["metrics"] if m["lipinski_rule_of_5_violations"] <= 1]

# 3. Similarity filter
response = await client.session.call_tool("calculate_smiles_similarity", arguments={"target_smiles": source_smiles, "candidate_smiles_list": passed})
final = [r["smiles"] for r in client.parse_result(response)["similarities"] if 0.4 <= r["score"] <= 0.95]
```

## step 4 — Evaluate & Iterate

Evaluate all filtered candidates with skill **molclaw-boltz2-affinity** and **molclaw-quickvina-docking**. Compare against source:

| SMILES | Vina | Δ Vina | Boltz2 pred_value | Δ Boltz2 |
|--------|------|--------|-------------------|----------|

**Success:** Vina improves ≥ 0.5 kcal/mol OR Boltz2 affinity_pred_value meaningfully improves → report best molecule. Done.

**Insufficient improvement:** Record what was tried and the scores. Return to step 2 with a different modification site and strategy. Remember all previous attempts — do not repeat failed approaches.

**Retry limit:** Maximum 3 retries (4 total rounds). If no molecule meets success criteria after all rounds, report the best-performing molecule across all attempts with a comparison table and ADMET profile (`pred_mol_admet`).
---

## ⚠ Computation-First Principle (L3 Principle 13)

**ALL values in baseline evaluation and optimization rationale MUST come from tool calls performed in this session.** Do NOT fill in values from LLM training knowledge. CORRECT: "ADMET-AI predicts CYP3A4 prob=0.72; the methoxyethoxy group is a likely O-demethylation site (agent analysis based on tool output)." WRONG: "CYP3A4 inhibition is likely due to the methoxyethoxy group" (without first confirming from ADMET-AI).

Each molecular modification MUST cite specific computed data (docking scores, interaction residues, ADMET values) as the basis. Literature-derived rationale must be explicitly labeled.

## ⚠ Mandatory File Downloads (L3 Principles 14-15)

At each evaluation round, download: Boltz-2 complex CIF files, docking pose PDBQT files, interaction analysis images, and ADMET result JSON files. These are Category A outputs.

## ⚠ Data Integrity in Optimization Trajectory (L3 Principle 11)

Every number in the comparison table (Vina score, Boltz2 value, QED, ADMET) must be the exact value returned by the tool call — never rounded, estimated, or recalled from memory. Record the tool return value directly.

## ⚠ Residue Numbering (L3 Principle 17)

When interaction analysis reports residue IDs from Boltz-2 predicted structures, apply residue numbering mapping before interpreting which pocket residues are involved. See `molclaw-residue-mapper`.

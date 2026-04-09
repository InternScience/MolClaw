---
name: molclaw-peptide-protein-binder-design
description: >
  Design peptides and protein binders targeting a specific protein. Uses EvoBind for de novo
  peptide design, ProteinMPNN for sequence optimization, Chroma for protein binder scaffold
  generation, and multi-layer independent validation.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Section 6.3 (Protein and peptide design strategy),
      L3 Principle 4 (Iterative design), Principle 5 (Three questions per round),
      L3 Principle 9 (Independent validation),
      L3 Principle 11 (Count-Before-Report — verify design counts and validation scores),
      L3 Principle 14 (Mandatory structure file collection — download Chai-1 complexes, HDOCK outputs),
      L3 Principle 15 (Mandatory image file collection — download ProLIF interaction plots),
      L3 Principle 17 (Residue numbering reconciliation — map interface residues to task reference)
---

# Peptide and Protein Binder Design Workflow

## Applicability

**Use this skill when:** Designing peptides or protein binders that must bind a specific target protein at a defined site.

**Do NOT use this skill when:** Generating peptide sequences without a specific binding target (use Skill 4 Mode E); improving a protein's own stability/solubility without binding requirements (use Skill 10).

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Target protein structure | Skill 1 `prepared_pdb` | Yes |
| Target protein sequence | Skill 1 `fasta_path` | Yes (for EvoBind) |
| Binding site residues | User or Skill 1 pocket detection | Recommended |
| Numbering scheme info | Skill 1 `numbering_scheme` | Required (for residue mapping) |

## Scene Classification

**Scene A: De novo targeted peptide design (8–20 residues).** Core tool: `evobind_tool`.

**Scene B: Known peptide optimization.** Core tools: `proteinmpnn_tool` + `pepinvent_peptide_sampling_by_peptide`.

**Scene C: Protein binder design (> 50 residues).** Core tools: `chroma_toolkit` → `proteinmpnn_tool`.

## Residue Numbering Pre-Check (L3 Principle 17 — Execute Before Any Design)

**If the task specifies target binding site residues by number:** Immediately determine which numbering scheme those numbers use (usually UniProt or literature), and establish the mapping to the structure's numbering scheme. Record in `run_log.md`. All subsequent references to binding site residues must use the structure's numbering when calling tools, and the task's numbering when reporting results.

## Scene A: EvoBind Peptide Design

### Step 1: Prepare Target FASTA
Extract the target protein sequence from Skill 1 output. Write to a FASTA file.

### Step 2: Define Binding Region
`target_residues` defines where the peptide should bind. Sources (in priority order):
- User-specified residue range (highest priority) — **translate to structure numbering if needed**
- PPI interface hotspot residues (from Skill 6 per-residue decomposition)
- fpocket/P2Rank pocket residue list
- `"all"` — search the full surface (slower)

### Step 3: Execute EvoBind

| Parameter | Conservative | Standard (default) | Aggressive |
|-----------|-------------|-------------------|------------|
| `peptide_length` | 8–10 | 12 | 15–20 |
| `num_designs` | 5 | 10 | 20 |
| `num_iterations` | 50 | 100 | 200 |
| `cyclic` | False | False | True |

### Step 4: Initial Screening

Sort by ipTM: > 0.8 = high confidence; 0.6–0.8 = moderate; < 0.6 = low. Select candidates with ipTM > 0.6.

**⚠ COUNT GATE (L3 Principle 11):** Verify the actual number of designs returned:
```
EvoBind output verification:
- Requested: num_designs = 20
- Actual designs returned: [count from output file]
- Designs with ipTM > 0.6: [count]
```

## Scene C: Protein Binder Design (Full Sub-Workflow)

### Step C1: Generate Binder Scaffold with Chroma
Call `chroma_toolkit` to generate protein backbones. `num_samples`: 5–10 scaffolds.

**Post-generation download (L3 Principle 14):** Download ALL generated scaffold PDB files.

### Step C2: Design Sequence with ProteinMPNN
For each scaffold, call `proteinmpnn_tool`:
- `chains_to_design`: binder chain only (fix target chain)
- `model_name`: "v_48_020"
- `use_soluble`: True
- `num_seq_per_target`: 3–5
- `sampling_temp`: "0.1 0.2"

### Step C3: Proceed to validation (same pipeline as below)

## Multi-Layer Validation (All Scenes)

### Validation Layer 1: Chai-1 Independent Structure Prediction (L3 Principle 9)

**Why this is mandatory:** EvoBind's ipTM is a design score, not an independent prediction.

Call `chai1_predict` with `mode="sequence"`, providing both target and designed sequences:
```
seq="TARGET_SEQUENCE,DESIGNED_SEQUENCE"
name="Target,Binder"
samples=5
```

**Evaluation:**
- Chai-1 ipTM > 0.7 → validation passed
- Chai-1 ipTM 0.5–0.7 → marginal
- Chai-1 ipTM < 0.5 → validation failed; redesign

### Mandatory Chai-1 Structure Download (L3 Principle 14 — CRITICAL)

**Download the predicted complex structure** from Chai-1 output:
```python
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": chai1_result["output_structure"]}
)
# Save as stepNN_chai1_complex.pdb/cif
```
**This is a Category A file — essential for downstream ProLIF analysis, user verification, and visualization.**

### Validation Layer 2: HDOCK Docking Verification

If both target 3D structure and binder/peptide monomer structure are available:
- Call `hdock_tool` for protein-peptide/protein docking
- Evaluate HDOCK score (more negative = better)

### Mandatory HDOCK Structure Download (L3 Principle 14)

**Download the HDOCK docked complex PDB:**
```python
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": hdock_result["output_complex"]}
)
# Save as stepNN_hdock_complex.pdb
```

### Validation Layer 3: ProLIF Interface Interaction Analysis

Call `prolif_pdb` on the validated complex structure (Chai-1 or HDOCK output).

**Residue Numbering Mapping for ProLIF (L3 Principle 17):**
Before interpreting ProLIF results, map residue IDs from the complex structure's numbering to the task's reference scheme. The Chai-1 predicted complex uses sequential numbering starting from 1 — this is NOT UniProt numbering.

**ProLIF Evaluation:**
- Target: 3–8 interface hydrogen bonds for a good peptide binder
- Check: peptide contacts the originally specified `target_residues` (using mapped numbering)
- Identify anchor interactions to preserve in optimization

### Mandatory ProLIF Image Download (L3 Principle 15)

Download ALL ProLIF visualization outputs (interaction heatmap, frequency barplot).

### Validation Layer 4: Sequence Property Assessment

Call `calculate_protein_sequence_properties`:
- Instability index < 40 → likely stable
- GRAVY: negative → better solubility

**Peptide-specific qualitative assessment (labeled as Category 2 — agent analysis, not tool computation):**
- Protease susceptibility: peptides rich in Arg/Lys are more susceptible to trypsin-like proteases
- Membrane permeability: cyclic peptides with N-methylation have better permeability
- Immunogenicity: longer peptides (>15 residues) have higher immunogenicity risk

Label these as "qualitative assessment based on sequence features (agent analysis)" — not computational predictions.

## Iteration Protocol (L3 Principles 4–6)

### Before each round, answer three questions (L3 Principle 5):
1. **What needs improvement?** Cite verified data: "Round 1 best peptide has Chai-1 ipTM of only 0.55 (verified from tool return); need stronger interface complementarity."
2. **What strategy?** "Increase peptide length by 3 residues; switch to cyclic=True."
3. **How to measure?** "Chai-1 ipTM > 0.7; HDOCK score < −200."

### Iteration schedule:

**Round 1 (Exploration):** EvoBind with `num_designs=20, num_iterations=50`. Select ipTM > 0.6. Chai-1 validation on these.
- **⚠ Verify actual design count from output file.**
- **Download all Chai-1 complex structures.**

**Round 2 (Focused optimization):** For best Round 1 candidate(s):
- ProteinMPNN sequence optimization: fix key interface residues (identified by ProLIF in Round 1, with mapped numbering)
- Try `cyclic=True` if Round 1 used linear
- **⚠ Verify design count. Download structures.**

**Round 3 (Fine-tuning):** Adjust peptide length; refine target_residues based on Round 2 ProLIF data (mapped); try `use_soluble=True` + `omit_aas="CMX"`.
- **⚠ Verify counts. Download structures and images.**

**Convergence:** Stop when Chai-1 ipTM > 0.7 for at least one candidate; or when ipTM has not improved for 2 rounds; or after 4 rounds maximum.

### Round-Level Verification (L3 Principle 12 Checkpoint B)

Before writing any round summary:
```
### Round N Verification
- Designs generated: [verified count from file]
- ipTM scores: [verified from tool returns]
- Chai-1 validation ipTM: [verified from tool return]
- Structure files downloaded: [list]
- Image files downloaded: [list]
- All data verified: ✅
```

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| All EvoBind designs ipTM < 0.5 | Challenging target surface | Increase length to 15–20; try cyclic; try different target_residues |
| Chai-1 places peptide at wrong site | Sequence ambiguous about location | Redesign with more iterations |
| HDOCK gives very weak scores | Peptide doesn't fold alone | Expected; rely more on Chai-1 ipTM |
| ProLIF residue IDs don't match task | Numbering mismatch | **Execute residue mapping before interpreting** |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after EvoBind design:**
- [ ] Design count verified from output file (not from requested count)
- [ ] ipTM scores recorded from actual tool returns

**CHECKPOINT after each validation layer:**
- [ ] Chai-1 complex structure downloaded and verified
- [ ] HDOCK complex structure downloaded and verified
- [ ] ProLIF images downloaded
- [ ] Residue numbering mapping applied for ProLIF interpretation

**CHECKPOINT before final report:**
- [ ] All structure files accounted for in file inventory
- [ ] All validation scores file-verified
- [ ] Residue mapping table included in report
- [ ] Peptide stability assessment labeled as qualitative/agent analysis

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Top candidates | CSV: sequence, ipTM, Chai1_ipTM, HDOCK_score, ProLIF_summary | Report | **A — MUST download** |
| Chai-1 complex structures | PDB/CIF per candidate | Skill 6, user verification | **A — MUST download** |
| HDOCK complex structures | PDB per candidate | User verification | **A — MUST download** |
| ProLIF images | PNG/SVG | Report | **A — MUST download** |
| Iteration trajectory | Table: round, strategy, best_ipTM, verified counts | Report | B — record in log |
| Residue mapping table | CSV | Report | **A — MUST download** |

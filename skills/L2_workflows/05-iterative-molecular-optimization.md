---
name: molclaw-iterative-molecular-optimization
description: >
  Target-directed multi-round iterative molecular optimization. Integrates tool-based
  computation with LLM chemical reasoning in a closed-loop design cycle. Core implementation
  of L3 Chapter 2 iterative methodology.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Chapter 2 in its entirety (Principles 4–8),
      L3 Principle 11 (Count-Before-Report — verify all evaluation scores against tool returns),
      L3 Principle 13 (Computation-first — design rationale must cite tool data, not LLM training knowledge),
      L3 Principle 14 (Mandatory structure file collection — download Boltz-2 CIF, docking poses),
      L3 Principle 15 (Mandatory image file collection — download interaction analysis images),
      L3 Principle 17 (Residue numbering reconciliation — map interaction residues to task reference scheme)
---

# Iterative Molecular Optimization Workflow

## Applicability

**Use this skill when:** The user has clear optimization targets (improve binding affinity, improve QED, reduce toxicity, enhance selectivity, achieve dual-target activity, etc.), AND either (a) a specific starting molecule is provided, OR (b) a starting molecule will be acquired via Skill 4 (de novo generation) or literature/database retrieval as a preparatory step before entering the iterative loop.

**Do NOT use this skill when:** The user needs to explore chemical space broadly without a defined optimization target (use Skill 4); or the task is single-point evaluation without optimization (use Skill 3 or Skill 2).

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Starting molecule SMILES | User | Yes |
| Target protein structure | Skill 1 `prepared_pdb` | Scene A only |
| Protein sequence | Skill 1 `fasta_path` | Scene A only |
| Numbering scheme info | Skill 1 `numbering_scheme` | Scene A (for interaction analysis) |
| Optimization target(s) | User specification | Yes |

## Scene Classification

**Scene A: Binding affinity optimization.** Goal: enhance binding to a specific protein target. Core evidence: docking modes, interaction fingerprints, Boltz-2 affinity.

**Scene B: Physicochemical property optimization.** Goal: improve QED, LogP, solubility, ADMET profile, etc. Core evidence: RDKit properties, ADMET-AI predictions.

**Scene C: Multi-objective optimization (two or more conflicting targets).** Goal: simultaneously improve multiple properties that tend to trade off against each other. Core evidence: both Scene A and Scene B evaluation tools, with explicit Pareto trade-off tracking.

**Scene D: Multi-target simultaneous optimization.** Goal: achieve binding thresholds on TWO OR MORE distinct target proteins simultaneously. Core evidence: independent docking scores per target, per-target interaction fingerprints. Scene D inherits Scene C's Pareto logic but adds multi-target-specific protocols:
- **Independent target preparation:** Each target goes through Skill 1 independently, producing separate `prepared_pdb`, `numbering_scheme`, and pocket parameters.
- **Per-target docking parameter locking:** Maintain a SEPARATE locked parameter set for each target (see "Multi-Target Docking Parameter Locking" section below).
- **Unified evaluation matrix:** Step 1 evaluates each candidate against ALL targets. The assessment table has one score column per target.
- **Bottleneck-first strategy:** In Step 2, prioritize the target where the current best molecule performs worst relative to its threshold. Examine interaction fingerprints at THAT target to identify optimization opportunities, while cross-checking that proposed modifications do not disrupt interactions at the other target(s).
- **Cross-target interaction comparison:** When using interaction-visualizer, run it independently per target (with target-specific `--resid_offset`) and compare partner_site CSVs: modification candidates are ligand atoms that are low-interaction at the bottleneck target but NOT high-interaction (anchor) at other targets.
- **Scene D success criteria:** ALL targets reach their respective thresholds simultaneously, OR the cross-target Pareto frontier is reached (documented quantitatively with per-target scores).

All scenes share the same four-step iterative loop but differ in evaluation metrics.

## Iterative Loop Architecture

Each round consists of four steps forming an **Evaluate → Diagnose → Design → Verify** closed loop.

### Step 1: Baseline Assessment (Round 1) / Current State Assessment (Round 2+)

**Scene A evaluation:**
1. Call `molecule_docking_quickvina_fullprocess` — record baseline docking score
   - **Checkpoint A:** Score must be negative. If positive, execute progressive box enlargement (25→30→40→50 Å).
   - **Download** docking pose file (PDBQT) via `server_file_to_base64` → local save.
2. Call `pred_binding_affinity_boltz2` — record binding probability and predicted affinity
   - **Download** complex CIF file (`complex_cif_file` field) — Category A.
3. **Interaction analysis** — choose based on availability and needs:
   - **Option A (MCP):** Convert Boltz-2 CIF to PDB, then call `analyze_protein_ligand_interactions` — map all interactions.
   - **Option B (local, preferred when 2D diagram or partner_site CSV needed, or when MCP unavailable):** Run `molclaw-interaction-visualizer`:
     ```bash
     python molclaw_interaction_visualizer.py \
         --receptor prepared.pdb --ligand docking_pose.sdf \
         --mode ligand --out_dir viz_out \
         --resid_offset <offset> --score <vina_score> \
         --residue_roles_json roles.json --title "Target–Seed"
     ```
     Parse `summary_*.json` → `top_residues` (anchor interactions) + `hot_partner_sites` (modification targets).
   - **Download** all interaction visualization images — Category A (L3 Principle 15).
4. Call `pred_mol_admet` — full ADMET profile

**Computation-first rule (L3 Principle 13):** ALL values in this assessment — docking scores, interaction fingerprints, ADMET predictions — MUST come from tool calls performed in this session. Do NOT fill in values from LLM training knowledge (e.g., "the IC₅₀ of erlotinib is approximately 2 nM" without a tool call is forbidden). If literature comparison is needed, clearly label it: "⚠️ LITERATURE VALUE: ..."

From the interaction data, identify:
- **Anchor interactions** (strong H-bonds, salt bridges) — must preserve during modification
- **Optimization opportunities** (residues within contact range but forming only weak contacts)
- **Steric clashes** — sites where modification could relieve strain
- **Pocket character** — hydrophobic vs. polar regions

**Partner site diagnosis (when using interaction-visualizer):** Parse `*_partner_site.csv` to directly identify:
- **Ligand atoms to preserve:** high interaction count → critical pharmacophore points that anchor the ligand
- **Ligand atoms to modify:** low or zero interaction count → safe optimization candidates
This output directly informs modification site selection in Step 2 below.

**Residue Numbering Mapping (L3 Principle 17 — execute if task references specific residues):**
Before interpreting interaction results, check whether the analysis structure's numbering matches the task's reference scheme. If not, build the mapping table (see Skill 1 numbering scheme info). All interaction residue IDs in the assessment must be translated to the task's reference scheme before drawing conclusions.

**Scene B evaluation:**
1. Call `pred_mol_admet` — full property profile
2. Focus on the user-specified target properties
3. Identify which molecular features (functional groups, ring systems) are likely responsible for the problematic property values

**Scene B generation strategy — mol2mol sampling + filtering:** When the optimization targets can be expressed as property ranges, use `reinvent_mol2mol_sampling` with appropriate `prior_type` and `min_similarity` to generate structurally similar candidates, then filter using `calculate_mol_drug_chemistry` and `pred_mol_admet` to select molecules meeting the target property ranges. LLM-guided design should be used as a supplement for modifications that require chemical reasoning beyond what sampling captures (e.g., bioisosteric replacements, metabolic soft-spot removal). See L1 skill `molclaw-mol2mol-sampling` for prior type selection guide.

**Computation-first rule for Scene B:** Property analysis must cite specific tool-computed values, not general LLM knowledge about drug chemistry. CORRECT: "ADMET-AI predicts CYP3A4 inhibition probability = 0.72; the methoxyethoxy group is a known O-demethylation substrate (agent analysis based on structural inspection of the tool output)." WRONG: "CYP3A4 inhibition is likely due to the methoxyethoxy group" (without first confirming the CYP3A4 probability from the tool).

**Reference thresholds for Scene B success (when user does not specify):**

| Property | Meaningful improvement threshold |
|----------|--------------------------------|
| QED | Δ ≥ +0.1 |
| LogP | Change ≥ 0.5 in desired direction |
| MW | Change ≥ 30 Da in desired direction |
| CYP inhibition probability | Δ ≤ −0.15 |
| hERG inhibition probability | Δ ≤ −0.15 |

**Scene C evaluation (multi-objective):**

Run BOTH Scene A and Scene B evaluation pipelines in full. Then additionally:

1. **Classify modification sites by objective impact.** For each modifiable position on the molecule, determine whether it primarily affects Objective 1 (e.g., binding — positions inside the pocket) or Objective 2 (e.g., solubility — solvent-exposed positions) or both.

2. **Establish the current Pareto status.** Record both objectives' values. Determine whether the current molecule is dominated by any previous round's best molecule.

3. **Define the priority objective for this round.** In early rounds, prioritize whichever objective is further from its target.

4. **ADMET Deterioration Alarm (Scene C mandatory).** After computing ADMET profiles, compare ALL endpoints against the baseline values — not only those flagged as problematic at baseline. Flag any endpoint where: absolute increase exceeds 0.15 (for probability endpoints in [0,1]), OR relative increase exceeds 100% from baseline, regardless of whether the agent's current optimization strategy targets that endpoint. Record flagged endpoints in `run_log.md` with: `⚠ ADMET ALARM: [endpoint] changed from [baseline] to [current] (+[absolute]/[relative]%).` This prevents the "unmonitored endpoint" blind spot observed in QED optimization benchmarks.

**Scene C success criteria:**
- Both objectives reach their user-specified thresholds simultaneously; OR
- The molecule reaches the Pareto frontier, in which case report the Pareto frontier explicitly.

**Scene C design strategy — the "anchor-then-optimize" approach:**
1. Identify non-overlapping modification sites: find positions where changes affect only one objective. Modify these first.
2. For overlapping sites: lock in the modifications that improved the priority objective first, then fine-tune secondary sites.
3. Accept Pareto trade-offs: if no modification improves both, select the molecule with the smallest loss in the secondary objective for the largest gain in the primary. Document the trade-off quantitatively.
4. Never sacrifice more than the user-specified threshold on either objective unless the user explicitly permits it.

### Step 2: LLM-Guided Molecular Design

Based on Step 1's analysis, design 1–3 optimized molecules. This step leverages the LLM's chemical reasoning as a generative component.

**Design rules:**
- Modify only 1–2 sites per molecule per round (avoid multi-variable changes that prevent attribution)
- For fused/polycyclic systems, modify only 1 site
- NEVER break anchor interactions identified in Step 1
- NEVER introduce known PAINS substructures or toxic pharmacophores
- Preserve stereochemistry marks (`@`, `@@`, `/`, `\\`) unless directly modifying that chiral center
- If this is a retry within the same round: do NOT repeat a previously failed strategy
- **If the task requires preserving a core scaffold:** All modifications must be on substituents/side chains, never on the core ring system. Verify the scaffold is preserved in the designed SMILES before proceeding to Step 3.

**REINVENT-assisted generation (alternative to LLM design):** When the task requires generating multiple derivatives from a seed molecule (e.g., "produce 5 derivatives per round"), LLM-guided design alone may be insufficient. In such cases, use REINVENT mol2mol generation (`reinvent_mol2mol_sampling`) as the primary generation engine:

| Task requirement | Recommended approach |
|-----------------|---------------------|
| "Generate N derivatives" (N ≥ 3) | REINVENT mol2mol as primary generator; LLM design as supplement if needed |
| "Design 1–2 optimized molecules" | LLM design as primary; REINVENT as fallback for invalid SMILES |
| "Retain core scaffold + generate variants" | REINVENT with `prior_type="scaffold_generic"`, followed by scaffold verification (see L2-04 Post-Generation step 3) |
| "Only modify R-groups" | REINVENT R-group sampling (`libinvent_rgroup_sampling_by_scaffold`) |
| "Improve QED / LogP / solubility / ADMET" (explicit property targets) | REINVENT `reinvent_mol2mol_sampling` with property-aware filtering — generate candidates with appropriate prior_type, then filter using `calculate_mol_drug_chemistry` and `pred_mol_admet` to select molecules meeting target ranges; use LLM design for fine-tuning |
| Multiple seeds from previous round (e.g., Top 5) | Call `reinvent_mol2mol_sampling` sequentially for each seed molecule |

**When using REINVENT in iterative optimization:**
- Set `smiles` = current round's seed molecule (see Seed Update Rule in Step 4)
- Set `n` = 2× the required number (to account for filtering losses)
- Apply the scaffold-constraint-aware prior selection table from L2-04
- After generation, run the full Post-Generation Processing pipeline from L2-04 (validity → count gate → scaffold check → dedup → property filter)

**Computation-first rule for design rationale (L3 Principle 13):** Each design MUST cite specific computed data from Step 1 as the basis for the proposed modification. CORRECT: "Interaction visualizer shows no interaction at Leu718 (UniProt numbering, rec_resid_mapped=718); adding a methyl group at C3 may form a hydrophobic contact." WRONG: "Based on known EGFR binding mode, we should add a hydrophobic group" (this is LLM knowledge, not a tool-computed observation).

**Exploration–exploitation schedule (L3 Principle 6):**

| Round | Strategy | Modification scope |
|-------|----------|-------------------|
| 1–2 | Exploration | Diverse modifications: try different functional groups, ring substitutions, bioisosteric replacements |
| 3–4 | Exploitation | Focused: refine the best modification sites found in earlier rounds, fine-tune substituents |
| 5+ | Convergence | Minimal: peripheral group tweaks on the best candidate only |

**Each design must include:**
- Target residue/interaction being addressed (citing Step 1 tool-computed data, with residue numbering scheme specified)
- Specific structural change description
- Optimized SMILES
- Confidence assessment (high/medium/low)

### Step 3: Validation and Filtering

1. **SMILES validity:** Call `is_valid_smiles`. If invalid, analyze the error pattern, then return to Step 2 with a simpler modification. **Maximum 3 validity retries per round.** If all 3 fail, switch to REINVENT `mol2mol_sampling` with `high_similarity` prior as a fallback generator.

2. **Scaffold preservation check (if task requires it):** Verify that the core scaffold specified by the task is present in each candidate molecule. Remove molecules that broke the scaffold. If ALL candidates broke the scaffold, regenerate with more conservative parameters (higher `min_similarity`, `prior_type="scaffold"`). See L2-04 Post-Generation Processing step 3 for the detailed protocol.

3. **Drug-likeness check:** Call `calculate_mol_drug_chemistry`. Accept Lipinski violations ≤ 1 (unless the starting molecule itself violates Lipinski, in which case preserve or improve).

4. **Similarity check:** Call `calculate_morgan_fingerprint_similarity` against the starting molecule. Acceptable range: 0.4–0.95. Below 0.4 = too different to attribute improvement; above 0.95 = trivially similar.

### Step 4: Assessment and Iteration Decision

Re-run Step 1's full evaluation on validated candidates. Compare against baseline AND the previous round's best.

**⚠ Data Integrity Check (L3 Principle 11):** Before writing any comparison table, verify each value against the actual tool return:

```
## Round N Assessment Verification
| Metric | Baseline (verified) | Previous best (verified) | This round (verified) | Source |
|--------|-------|--------|--------|--------|
| Docking score | −6.2 (from step01_docking.pdbqt) | −7.1 (from round01_best_docking.pdbqt) | −7.8 (from round02_docking.pdbqt) | QuickVina |
| QED | 0.38 (from tool return) | 0.42 (from tool return) | 0.51 (from tool return) | RDKit |
| CYP3A4 prob | 0.72 (from tool return) | 0.65 (from tool return) | 0.43 (from tool return) | ADMET-AI |
```

**Structure file downloads for this round (L3 Principle 14):** Download docking pose files and Boltz-2 complex CIF for each candidate evaluated. Download all interaction-visualizer/ProLIF images generated.

**Scene A success criteria:** Docking score improvement ≥ 0.5 kcal/mol; OR Boltz-2 affinity improvement is significant; AND no critical ADMET property worsened.

**Scene B success criteria:** Target property reaches user-specified threshold; OR meets the reference thresholds table above; AND no other property entered the red-flag zone.

**Scene C success criteria:** Both objectives reach thresholds simultaneously; OR the Pareto frontier is reached (documented quantitatively).

**Decision logic:**

```
IF success criteria met (or task-specific termination condition — see Global Target Tracker):
    → Report best molecule. Done.
ELIF current round number < max_rounds:
    → Answer L3 Principle 5's three questions:
      1. What specifically failed this round? (cite VERIFIED data)
      2. What different strategy will Round N+1 use? (must differ from this round)
      3. What is the success criterion for Round N+1?
    → Update seed molecule (see Seed Update Rule below)
    → Return to Step 1 with new strategy and new seed
ELSE (max rounds reached):
    → Report global best molecule across ALL rounds
    → Include complete optimization trajectory
```

### Post-Termination Experiential Learning Check (L3 Principle 25)

After reporting the final result and before closing the task, evaluate whether the optimization trajectory revealed novel patterns warranting skill crystallization:

- Did a novel failure-recovery strategy emerge during the optimization that is NOT in this workflow's "Common Failures & Recovery" table? → Trigger T2 may be active.
- Did a non-standard strategy produce superior results compared to the exploration–exploitation schedule (Principle 6)? → Trigger T4 may be active.
- Did a tool fail systematically under specific input conditions (e.g., REINVENT producing zero molecules at low seed Tanimoto)? → Trigger T5 may be active.
- Proceed to L3 Principle 25.5 (Mandatory Post-Execution Self-Assessment) to formally evaluate all triggers.

### Seed Molecule Update Rule

**After each round's evaluation, explicitly determine the seed molecule for the next round:**

- **Default rule:** The seed for Round N+1 is the molecule with the best (lowest docking / highest QED / best target metric) score from Round N, regardless of whether it met the overall success criteria.
- **Alternative (task-specified):** If the task defines a different seed selection rule (e.g., "always use the globally best molecule"), follow the task's rule.

**Record in `run_log.md`:**
```
### Round N → Round N+1 Seed Update
- Round N best molecule: [SMILES]
- Round N best score: [value] (verified from tool return)
- This molecule becomes the seed for Round N+1
- Generation parameters for Round N+1: [prior_type, min_similarity, etc.]
```

**In Step 2 (LLM-Guided Design or REINVENT generation) of Round N+1:** Use the new seed as the starting molecule. If using REINVENT mol2mol, set `smiles` = new seed SMILES. If using LLM design, base modifications on the new seed's structure and evaluation data.

### Global Target Tracker (for tasks with cumulative termination conditions)

**When the task defines termination based on cumulative results across rounds** (e.g., "stop when ≥ 2 molecules across all rounds meet ΔScore ≤ −2.0"), maintain a global tracker in `run_log.md`:

**Single-target tracker:**

```
## Global Target Tracker
| Round | Molecule SMILES | Score | ΔScore (vs baseline) | Target Met? |
|-------|----------------|-------|---------------------|-------------|
| 1 | [SMILES_1] | −8.5 | −1.3 | No |
| 1 | [SMILES_2] | −9.1 | −1.9 | No |
| 2 | [SMILES_3] | −9.5 | −2.3 | ✅ Yes |
| 3 | [SMILES_4] | −9.8 | −2.6 | ✅ Yes |

Cumulative target-met count: 2 → TERMINATION CONDITION MET
```

**Multi-target tracker (Scene D):**

```
## Multi-Target Global Tracker
| Round | Molecule SMILES | T1 Score | T2 Score | T1 Met? | T2 Met? | ALL Met? |
|-------|----------------|----------|----------|---------|---------|---------|
| 1 | [SMILES_1] | −7.5 | −6.8 | No | No | No |
| 2 | [SMILES_2] | −8.7 | −7.2 | ✅ | No | No |
| 3 | [SMILES_3] | −8.9 | −8.6 | ✅ | ✅ | ✅ Yes |

Cumulative ALL-Met count: 1 → [check against task threshold]
```

**Update this tracker after EACH round.** Check the cumulative count against the task's termination condition before proceeding to the next round. The tracker is maintained incrementally — do not reconstruct it from scratch at the end.

### Docking Parameter Locking (for iterative docking tasks)

**When the task requires that docking parameters remain constant across all rounds:**

After the baseline docking (Round 0 or Step 1 in Round 1), record the exact parameters in `run_log.md` as "Locked Docking Parameters." In ALL subsequent rounds, retrieve and reuse these exact parameters.

**Single-target tasks (Scene A/B/C):**

```
## Locked Docking Parameters (established in baseline docking)
- center_x: [value]   center_y: [value]   center_z: [value]
- size_x: [value]     size_y: [value]     size_z: [value]
- Source: [co-crystal ligand centroid / fpocket detection / user-specified]
- Rule: Reuse these in EVERY subsequent round. Do NOT re-detect pocket.
```

**Multi-target tasks (Scene D):** Record one locked parameter set PER TARGET:

```
## Locked Docking Parameters
### Target 1: [name] ([PDB ID])
- center_x: [val]  center_y: [val]  center_z: [val]
- size_x: [val]    size_y: [val]    size_z: [val]
- Source: [co-crystal / fpocket / user]
### Target 2: [name] ([PDB ID])
- center_x: [val]  center_y: [val]  center_z: [val]
- size_x: [val]    size_y: [val]    size_z: [val]
- Source: [co-crystal / fpocket / user]
Rule: Reuse EACH target's parameters in EVERY subsequent round.
```

⚠ Do NOT use Target 1's pocket parameters for Target 2, even if both are kinases. Each target has its own pocket geometry.

**⚠ Do NOT re-run pocket detection in subsequent rounds.** The pocket does not change between rounds — only the ligand changes. Re-running pocket detection risks inconsistency (different pocket center in different rounds), which would make ΔScore comparisons unreliable.

**Maximum iteration rounds:** 5 (default). However, if the task specifies a different limit (e.g., 15 rounds), follow the task's limit. If the best molecule has not improved for 2 consecutive rounds (L3 Principle 7 convergence stop), stop early regardless of round count unless the task prohibits early stopping.

<!-- NEW: Optional LR SAR-informed optimization -->
### Optional: SAR-Informed Optimization Direction (if LR tools are available)

When optimization stagnates (< 10% improvement in the primary metric over 2 consecutive rounds), literature search can provide new design direction:

1. Search PubMed: `"[target name] SAR structure-activity"` (retmax=10)
2. Extract key SAR insights: which functional groups improve potency, which cause toxicity, known pharmacophore features
3. Use insights to inform REINVENT seed selection or SMILES fg-editor modifications in the next round
4. Record: `[LR-INFORMED DESIGN] SAR literature guided Round N seed selection: [rationale with PMID]`

This is a principled use of Category 3 information to GUIDE computational design choices, not to replace computation. The computational results of the next round remain Category 1. If LR tools are not available, rely on computational analysis of the optimization trajectory to select new design directions.

## Iteration Record Requirements (L3 Principle 8)

Each round must save:
- Generated SMILES with all evaluation scores (file-verified)
- Strategy chosen and rationale (citing previous round's verified data — not generic statements)
- Delta of key metrics vs. previous round (computed from verified values)
- Cumulative global best molecule (may be from any round, not just the current one)

**Final report must include an optimization trajectory table (all values file-verified, L3 Principle 11):**

| Round | SMILES | Docking (kcal/mol) | QED | LogP | Key ADMET | Strategy | Outcome | Source Files |
|-------|--------|-------------------|-----|------|-----------|----------|---------|-------------|
| 0 (baseline) | [start] | −6.2 | 0.38 | 4.8 | CYP3A4=0.72 | — | — | step01_baseline_docking.pdbqt |
| 1 | [mol1] | −7.1 | 0.42 | 4.1 | CYP3A4=0.65 | Replace OMe with F | Improved | round01_docking.pdbqt |
| 2 | [mol2] | −7.8 | 0.51 | 3.5 | CYP3A4=0.43 | Ester→amide | Improved | round02_docking.pdbqt |

**Multi-target optimization trajectory table (Scene D):**

| Round | SMILES | T1 Dock | T2 Dock | QED | ADMET Flags | Strategy | Bottleneck | Source Files |
|-------|--------|---------|---------|-----|-------------|----------|------------|-------------|
| 0 | [seed] | −6.2 | −5.8 | 0.38 | CYP3A4=0.72 | — | T2 | step01_T1.pdbqt, step01_T2.pdbqt |
| 1 | [mol1] | −6.5 | −7.1 | 0.42 | OK | Improve T2 hinge H-bond | T1 | round01_T1.pdbqt, round01_T2.pdbqt |
| 2 | [mol2] | −8.1 | −7.8 | 0.51 | OK | Improve T1 hydrophobic | T2 | round02_T1.pdbqt, round02_T2.pdbqt |

The "Bottleneck" column records which target was prioritized in the NEXT round's design strategy — this is the primary evidence of adaptive strategy.

**The "Source Files" column ensures traceability of every reported value.**

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| LLM designs invalid SMILES 3 times in a row | Complex starting molecule; LLM struggles with SMILES syntax | Switch to REINVENT `mol2mol_sampling` with `high_similarity` prior |
| Docking score improves but ADMET worsens | Optimization inadvertently introduced metabolic liability | Next round explicitly targets ADMET improvement while constraining docking score not to worsen |
| No improvement after 3 rounds | Molecule may be near local optimum | Try a larger structural change (scaffold hop via Skill 4 Mode B with `scaffold_generic`); or declare Pareto frontier reached |
| Interaction residue IDs don't match task description | Numbering scheme mismatch (wrong `--resid_offset` or unmapped ProLIF output) | Recompute offset via `residue_mapper.py`; re-run interaction-visualizer with correct `--resid_offset` (L3 Principle 17) |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after Step 1 (evaluation):**
- [ ] All evaluation scores recorded from actual tool returns (not from memory)
- [ ] Docking score is negative (if positive, progressive box enlargement attempted)
- [ ] Structure files (docking pose, Boltz-2 CIF) downloaded and verified
- [ ] Interaction images downloaded
- [ ] If interaction-visualizer used: summary JSON parsed, partner_site.csv reviewed for modification candidates
- [ ] If task references specific residues, numbering mapping applied

**CHECKPOINT after Step 2 (design):**
- [ ] Each design cites specific computed data from Step 1 (not LLM training knowledge)
- [ ] No round repeats a previously failed strategy

**CHECKPOINT after Step 4 (assessment):**
- [ ] All comparison values verified against tool returns
- [ ] Optimization trajectory table uses only verified values
- [ ] Structure files for new candidates downloaded
- [ ] Three questions answered before next round (if continuing)

**CHECKPOINT before final report (L3 Principle 12 Checkpoint C):**
- [ ] Every number in the trajectory table traced to a source file
- [ ] All structure files and images accounted for in file inventory
- [ ] Global best molecule has been fully evaluated with verified metrics

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Best optimized molecule | SMILES + full property profile | Skill 6 (free energy), Report | B — record in log |
| Optimization trajectory | Table with Source Files column | Report | B — record in log |
| All round data | Per-round evaluation files | Archive | **A — MUST download** |
| Docking pose files | PDBQT per round | Skill 6, Skill 8, Archive | **A — MUST download** |
| Boltz-2 complex CIF | CIF per round | Archive, user verification | **A — MUST download** |
| Interaction images | PNG per round | Report | **A — MUST download** |
| Interaction-visualizer CSV + JSON (if used) | CSV, JSON per round | Agent decision loop, SAR analysis | **A — MUST download** |
| Residue mapping table | CSV (if built) | Report | **A — MUST download** |

---
name: molclaw-generative-molecular-design
description: >
  Generative molecular design using REINVENT4: de novo generation, mol-to-mol transformation,
  scaffold R-group exploration, linker design, and peptide generation. Includes full iteration
  protocol aligned with L3 methodology.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 4 (All design tasks should be iterative), Principle 5 (Three questions per round),
      L3 Principle 6 (Exploration-exploitation), Principle 7 (Convergence), Principle 8 (Iteration records),
      L3 Principle 11 (Count-Before-Report — verify generated molecule counts against actual output files),
      L3 Principle 13 (Computation-first — generation strategies must be grounded in tool data, not LLM intuition),
      L3 Principle 14 (Mandatory structure file collection — download generated molecule SDFs)
---

# Generative Molecular Design Workflow

## Applicability

**Use this skill when:** The user needs new molecular structures — de novo generation, molecular optimization, scaffold exploration, fragment linking, or peptide design.

**Do NOT use this skill when:** The user has a specific molecule and clear optimization targets (use Skill 5 for target-directed iterative optimization); the task is peptide-protein binding design against a specific target (use Skill 9).

**Boundary with Skill 5:** This skill generates diverse candidates from chemical space. Skill 5 takes a specific molecule and iteratively optimizes it toward defined targets. If the user says "optimize this molecule's QED," use Skill 5. If the user says "generate molecules similar to this lead," use this skill.

**Targeted generation without a starting molecule:** If the user wants "molecules that bind EGFR" but provides no starting molecule, first check if known inhibitors exist (search literature/ChEMBL). If found, use Mode B with a known inhibitor as the starting point. If not, use Mode A for de novo generation followed by docking (Skill 2) to filter.

## Prerequisites

No hard dependency. Commonly combined with: Skill 3 (property filtering of generated molecules), Skill 2 (docking validation), Skill 5 (iterative optimization of best candidates).

## Mode Selection Decision Tree

| User input | Recommended mode | Tool |
|-----------|-----------------|------|
| No starting molecule, needs a library | **Mode A: De novo** | `reinvent_denovo_sampling` |
| Has a starting molecule, wants variants | **Mode B: Mol-to-mol** | `reinvent_mol2mol_sampling` (single) or `batch_reinvent_mol2mol_sampling` (multiple seeds) |
| Has a core scaffold with marked R-groups `[*:1]` | **Mode C: R-group sampling** | `libinvent_rgroup_sampling_by_scaffold` or `libinvent_rgroup_sampling_by_scaffold_name` (12 predefined scaffolds) |
| Has two fragment warheads, needs a linker | **Mode D: Linker** | `linkinvent_linker_sampling_by_warheads` or `linkinvent_linker_sampling_by_warhead_pair_name` (9 predefined pairs) |
| Needs peptide sequences | **Mode E: Peptide** | `pepinvent_peptide_sampling_by_peptide`, `pepinvent_peptide_sampling_by_template` (10 templates), or `get_pepinvent_info` (query options) |
| Has a starting molecule + explicit property targets (QED, MW, LogP, TPSA ranges) | **Mode F: RL similarity optimization** | `reinvent_similarity_optimization` |
| Has a scaffold + explicit property targets for R-groups | **Mode G: RL R-group optimization** | `libinvent_rgroup_optimization` |

### Mode F & G: RL Optimization vs Sampling — When to Choose

| Criterion | Use Sampling (Modes A-E) | Use RL Optimization (Modes F-G) |
|-----------|--------------------------|--------------------------------|
| Property targets | Vague or none ("generate analogs") | Explicit ranges ("QED > 0.7, LogP 1-3") |
| Speed requirement | Need results in seconds | Can wait minutes |
| Diversity goal | Maximum structural diversity | Property-optimized set |
| Scaffold control | Need scaffold_generic/scaffold priors | Free optimization (Mode F) or scaffold-fixed (Mode G) |
| Typical use | Library building, exploration | Lead optimization, ADMET improvement |

**Mode F usage pattern (reinvent_similarity_optimization):** Set `similarity_weight` to control how close to the target molecule; set `qed_weight`, `mw_weight`, `logp_weight`, `tpsa_weight` with specific `_low`/`_high` ranges to guide the RL. See L1 skill `molclaw-similarity-optimization` for weight recipes.

**Mode G usage pattern (libinvent_rgroup_optimization):** Requires a `.smi` scaffold file. Supports all Mode F weights PLUS R-group-specific constraints (`rgroup_mw_weight/min/max`, `rgroup_rings_weight/min/max`). See L1 skill `molclaw-rgroup-optimization`.

### Mode B: `prior_type` Selection Guide

| Stage | `prior_type` | `min_similarity` | Use case |
|-------|-------------|-------------------|----------|
| Hit discovery (broad) | `similarity` | 0.3–0.5 | Explore wide chemical space |
| Hit-to-lead | `medium_similarity` | 0.5–0.6 | Balanced exploration |
| Lead optimization | `high_similarity` | 0.7–0.8 | Conservative improvement |
| Scaffold preservation | `scaffold` / `scaffold_generic` | 0.5–0.6 | Preserve core structure |
| Local modification | `mmp` | 0.7–0.9 | Matched molecular pair style |

Default when user has no preference: `similarity` with `min_similarity=0.6`.

**Scaffold-constraint-aware prior selection:** When the task requires retaining a specific core scaffold:

| Task constraint | Recommended prior_type | min_similarity | Rationale |
|----------------|----------------------|----------------|-----------|
| "Retain core scaffold" / "keep ring system" | `scaffold_generic` | 0.5–0.6 | Preserves generic ring topology while allowing substituent variation |
| "Keep exact scaffold including substitution pattern" | `scaffold` | 0.6–0.7 | Strict scaffold SMILES matching |
| "Only modify R-groups at specified positions" | Use **Mode C (R-group)** instead | — | Gives explicit control over modification sites |
| "Maintain overall shape similarity" | `high_similarity` | 0.7–0.8 | Does not guarantee specific substructure retention |
| "Local modifications only (MMP-style)" | `mmp` | 0.7–0.9 | Minimal structural changes |

**⚠ Important:** `scaffold_generic` and `scaffold` priors provide the strongest scaffold retention but are still probabilistic — not all generated molecules are guaranteed to contain the scaffold. Always run the **scaffold preservation check** (Post-Generation Processing step 3) when scaffold retention is required.

### Mode D: Linker Length Guide

| Application | Recommended `min_atoms`–`max_atoms` | Rationale |
|------------|-------------------------------------|-----------| 
| Fragment merging | 1–5 | Short direct connection |
| Bivalent ligand | 3–8 | Moderate flexibility |
| PROTAC (CRBN-based) | 6–12 | Shorter linkers preferred |
| PROTAC (VHL-based) | 8–15 | Longer linkers often needed |

### Parameter Configuration

**Generation count `n`:** Set to 1.5–2× the target number of valid molecules (REINVENT's output includes some invalid/duplicate SMILES). Exploration: 30–50; library building: 100–200; large-scale: 500+.

**`filter_preset`:** `none` (no filter), `minimal` (remove chemically unreasonable), `default` (standard chemical filters), `strict` (stringent), `druglike` (de novo only).

## Post-Generation Processing

Regardless of mode, all generated molecules pass through this pipeline:

1. **Validate:** `is_valid_smiles` on each output. Record invalid count.

2. **⚠ COUNT GATE — Verify Actual Generation Count (L3 Principle 11 — CRITICAL):**

   This is where data fabrication most commonly occurs. After generation, IMMEDIATELY open the output file and programmatically count the entries:

   ```python
   # For JSON output:
   import json
   data = json.load(open("round01_generated_mols_raw.json"))
   actual_count = len(data)
   
   # For SMI output:
   with open("round01_generated_mols.smi") as f:
       actual_count = sum(1 for line in f if line.strip())
   
   # For multiple output files, count each and sum:
   total_raw = count_file_1 + count_file_2 + ...
   ```

   Record in `run_log.md`:
   ```
   Generation output verification:
   - Requested: n = 50 molecules
   - Output file: round01_generated_mols_raw.json
   - Verification command: python3 -c "import json; print(len(json.load(open('round01_generated_mols_raw.json'))))"
   - Actual count: 37 molecules
   - Valid after is_valid_smiles: 33 molecules
   - Discrepancy: Requested 50, got 37 raw (74%), 33 valid (66%)
   ```

   **If the actual count differs from the requested count:** Report the ACTUAL count. "Generated 33 valid molecules (requested 50; 37 returned by REINVENT, 4 failed SMILES validity check)" is CORRECT. "Generated 50 molecules" when only 33 valid ones exist is FABRICATION.

   **Retry threshold:** If valid count < 70% of requested count, consider retrying with adjusted parameters (lower `filter_preset`, increase `n` to 2× target, adjust `min_similarity`). If valid count ≥ 70%, proceed with available molecules.

   **Small batch supplement rule (n ≤ 10):** When the requested number is small (≤ 10), the 70% threshold is too lenient. Instead: require at least `n - 1` valid molecules. If fewer pass, retry with increased `n` (set to 2× original) or adjusted parameters. Up to 2 retry attempts before proceeding with available molecules.

3. **Scaffold preservation check (when task requires retaining a core scaffold):**

   When the task specifies that a core scaffold must be preserved (e.g., "retain quinazoline core," "keep the benzimidazole ring system"), verify after generation that each molecule actually contains the required substructure.

   **Implementation — LLM-assisted scaffold verification:**
   For each generated SMILES, the agent must examine the molecular structure and determine whether the specified core scaffold is present. Use the following reasoning protocol:
   - Identify the core scaffold SMARTS/SMILES pattern (e.g., quinazoline = `c1ccc2ncnc(*)c2c1` or equivalent)
   - For each generated molecule, check whether the scaffold substructure is contained
   - Mark molecules as "scaffold_preserved" or "scaffold_broken"
   - Remove scaffold_broken molecules from the candidate list
   - Record: "Scaffold check: X molecules checked → Y preserved scaffold → Z broke scaffold (removed)"

   **If too many molecules break the scaffold:** Switch generation strategy:
   - From `prior_type="similarity"` → try `"scaffold_generic"` or `"scaffold"` (stronger preservation)
   - From `mol2mol` → try `rgroup_sampling` if a scaffold SMILES with R-group markers can be constructed
   - Increase `min_similarity` to 0.7+ (more conservative generation)

   **⚠ COUNT GATE after scaffold check:** Count molecules passing both validity AND scaffold checks.

4. **Deduplicate:** String-level dedup. For strict dedup, compare canonical SMILES via `calculate_mol_basic_info`.

   **⚠ COUNT GATE after dedup:** Count unique molecules. Record: "Before dedup: 33 → After dedup: 28 unique molecules."

4. **Property analysis and filtering:** Pass to Skill 3. Filtering stringency by mode:
   - De novo → Standard or Strict
   - Mol-to-mol → Lenient
   - R-group / Linker → Standard
   - Peptide → Lenient or None (Lipinski is not applicable to peptides)

   **⚠ COUNT GATE after filtering:** Record count that passed Skill 3 filters (from Skill 3's verified output).

5. **Diversity check:** Compute pairwise similarity for a random sample (10–20 molecules) using `calculate_morgan_fingerprint_similarity`. If median Tanimoto > 0.85, diversity is too low — adjust parameters (lower `min_similarity`, switch `prior_type`, increase temperature) and regenerate.

6. **Relationship to starting molecule (Mode B/C):** Compute similarity of each generated molecule to the starting molecule. Group into: high similarity (>0.7), moderate (0.4–0.7), low (<0.4).

### Post-Generation File Download (L3 Principle 14)

Download ALL generated molecule files (raw JSON/SMI, filtered CSV/SMI) to the local workspace. These are Category A files — essential for user verification and downstream processing.

If any generation step produces SDF files (3D structures), download those as well.

## Iteration Protocol (L3 Principles 4–8)

Generative design is rarely complete in one round. Follow this structured iteration:

### Round 1: Exploration (L3 Principle 6 — early rounds prioritize breadth)
- Use broad parameters: `min_similarity` = 0.4–0.5 (Mode B), `filter_preset` = "default"
- Generate 30–50 molecules
- Evaluate with Skill 3 (properties) and optionally Skill 2 (quick docking of top candidates)
- **Record (L3 Principle 8):** all generated SMILES + property/docking results + strategy used
- **⚠ Verify all counts from actual files before writing round summary (L3 Principle 12 Checkpoint B)**

### Before Round 2, answer three questions (L3 Principle 5):
1. **What needs improvement?** Cite Round 1 data: "Top 5 molecules all have QED < 0.4 and LogP > 5; need better drug-likeness." (Cite the actual verified values from Round 1 output files.)
2. **What strategy will be used?** "Switch to `high_similarity` prior with the best Round 1 molecule as the new starting point; increase `min_similarity` to 0.6." (Strategy must differ from Round 1 if Round 1 failed.)
3. **How will improvement be measured?** "At least 3 molecules with QED > 0.5 and LogP < 4.5."

### Round 2: Focused Generation
- Use tighter parameters based on Round 1 analysis
- Start from the best Round 1 molecule(s)
- Generate 15–25 molecules
- Full Skill 3 evaluation; dock top 10 with Skill 2
- **⚠ COUNT GATE: Verify all molecule counts from actual output files**

### Round 3+: Convergence (L3 Principle 6 — later rounds prioritize refinement)
- High similarity constraints: `min_similarity` ≥ 0.7
- Generate 5–15 molecules focused on specific modifications
- Full evaluation pipeline
- **⚠ COUNT GATE: Verify all molecule counts from actual output files**

### Convergence Criteria (L3 Principle 7)
Stop iterating when any of these is met:
- **Target met:** Generated molecules satisfy all user-defined criteria
- **Convergence:** Best molecule's key metrics changed < 5% for two consecutive rounds
- **Pareto frontier:** Improving one metric consistently degrades another
- **Budget:** Maximum 4 generation rounds reached

### Round-Level Verification (L3 Principle 12 Checkpoint B — MANDATORY)

**Before writing ANY round summary**, re-read ALL output files from that round and verify:

```
### Round N Data Verification
- Output file: round{N}_generated_mols.json
- Molecules generated (verified from file): X (requested: Y)
- Valid SMILES (verified from validation): X₁
- After dedup (verified): X₂
- After Skill 3 filtering (verified from filtered output): X₃
- Docked successfully (if applicable, verified): X₄
- Top molecules selected: [list with verified scores]
- All counts verified: ✅ / Discrepancy found: [details]
```

### Iteration Record Requirements (L3 Principle 8)
For each round, save and report:
- All generated SMILES with their filtering/docking/ADMET results
- Strategy chosen and its rationale (citing previous round's verified data)
- Best molecule this round vs. previous round vs. global best
- Parameter settings used
- **Verified molecule counts at each stage (generated → valid → filtered → docked → selected)**

Final report must include an **optimization trajectory table** showing how the best molecule's key metrics evolved across rounds. **All counts and scores in this table must be file-verified (L3 Principle 11).**

| Round | Requested | Generated (verified) | Valid (verified) | Filtered (verified) | Best SMILES | Best Score | Strategy |
|-------|-----------|---------------------|-----------------|--------------------|----|----|----|
| 1 | 50 | 37 | 33 | 22 | [SMILES] | −7.2 | Broad exploration |
| 2 | 25 | 21 | 19 | 14 | [SMILES] | −8.1 | Focused on best R1 |

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| Very few valid molecules generated (<10% of n) | `filter_preset` too strict; starting molecule too complex | Lower filter to `minimal`; simplify starting molecule; increase n |
| All generated molecules extremely similar (Tanimoto >0.9) | `min_similarity` too high; `sampling_temp` too low | Lower similarity constraint; try different `prior_type` |
| No improvement across 2 rounds | Wrong chemical space region; wrong mode | Switch mode (e.g., from mol2mol to R-group); try a different starting molecule; consider switching to RL optimization (Mode F/G) |
| Mode C scaffold parsing fails | SMILES attachment point notation `[*:1]` incorrect | Verify scaffold SMILES; try `libinvent_rgroup_sampling_by_scaffold_name` with a built-in scaffold |
| Reported count doesn't match file | Memory-based counting instead of file-based | **Re-open the output file, re-count programmatically, correct the report** |
| Property targets not met after filtering | Sampling generates random molecules, post-filtering is lossy | Switch to Mode F (`reinvent_similarity_optimization`) for property-directed generation |
| Multiple seeds need derivatives simultaneously | Sequential mol2mol calls are slow | Use `batch_reinvent_mol2mol_sampling` with smiles_list |
| User says a scaffold name (e.g., "pyrimidine") without providing SMILES | User expects predefined scaffold support | Use `libinvent_rgroup_sampling_by_scaffold_name` or `linkinvent_linker_sampling_by_warhead_pair_name` |
| Need to know available peptide templates | Agent unsure which templates exist | Call `get_pepinvent_info('templates')` before peptide generation |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after each generation call:**
- [ ] Output file exists and is non-empty
- [ ] Actual molecule count verified from file (not from memory or requested count)
- [ ] If count < 70% of requested, retry decision recorded
- [ ] Generation output files downloaded to local workspace

**CHECKPOINT before each round summary:**
- [ ] All counts (generated → valid → filtered → selected) verified from actual files
- [ ] Round summary uses ONLY verified counts, never requested counts
- [ ] Strategy for next round cites specific verified data from this round

**CHECKPOINT before final report:**
- [ ] Optimization trajectory table uses ONLY file-verified counts and scores
- [ ] All generated molecule files downloaded locally
- [ ] Global best molecule identified with verified metrics

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Generated molecules (filtered) | CSV: SMILES, similarity_to_start, QED, MW, LogP, ADMET_flags, round_number | Skills 2, 5 | **A — MUST download** |
| Generation summary | Markdown: mode, parameters, per-round verified statistics | Report | B — record in log |
| Iteration trajectory | Table: round, verified counts, best_SMILES, key_metrics | Report | B — record in log |
| Raw generation files | JSON/SMI files per round | Archive | **A — MUST download** |

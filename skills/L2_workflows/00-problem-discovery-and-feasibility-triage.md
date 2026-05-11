---
name: molclaw-problem-discovery-and-feasibility-triage
description: >
  Meta-workflow for autonomous scientific problem discovery and optional closed-loop
  execution. Invoked when the user issues an open-ended task such as "find N scientifically
  valuable problems your toolkit can solve", "execute a complete closed-loop scientific
  discovery", or any request whose deliverable is a set of candidate problems rather than
  the execution of a specific one. Supports two modes: (1) discovery-only — produce ranked
  candidates for user selection; (2) closed-loop — discover, validate novelty against
  literature, lock experimental benchmarks, auto-execute the top candidate, validate results
  against experiment, and crystallize. This workflow operationalizes L3 Chapter 8 Principle 23
  (Capability Landscape Mapping and Problem Feasibility Assessment) as a reproducible
  step-by-step procedure.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 1.0
    methodology-ref: >
      L3 Chapter 8 Supplement Principle 23 in its entirety (23.1 Tool Capability
      Inventory, 23.1a Data Flow Connectivity Map, 23.2 Feasibility Classification,
      23.3 Problem Discovery Protocol with scientific value heuristics),
      Principle 26.4 (Boundary-Aware Problem Recommendation),
      L3 Principle 1 (Understand Before Acting — extended to meta-level of problem selection),
      L3 Principle 11 (Count-Before-Report — applied to candidate enumeration),
      L3 Principle 20 (Honest Annotation of Uncertainty — applied to recommendation)
---

# Problem Discovery and Feasibility Triage Meta-Workflow

## Applicability

**Use this workflow when:** The user's task is open-ended problem discovery rather than execution of a specific task. Typical forms include:
- "Given your available tools, identify N scientifically valuable computational problems you can solve."
- "What novel drug discovery workflows can be composed from your current toolkit that are not yet covered by existing L2 skills?"
- "Survey your capability space and recommend a research agenda."
- "Propose problems involving [capability domain X] that are tractable with current tools."
- "Execute a complete closed-loop scientific discovery." *(closed-loop mode — see Phase 0.2)*
- "Autonomously discover a problem, solve it, and validate against literature." *(closed-loop mode)*

The common signature is: the deliverable is a SET OF CANDIDATE PROBLEMS with their feasibility and value, OR a complete closed-loop cycle from discovery through execution and validation.

**Do NOT use this workflow when:**
- The user has specified a concrete target, ligand, or deliverable — that is an execution task (proceed to ordinary Phase 0 skill reading).
- The user has proposed a specific problem and asked the agent to solve it — if no existing L2 covers the task, invoke L2-13 (Draft Workflow Authoring) instead.
- The user is asking for meta-commentary on the toolkit without requiring problem formulation (e.g., "list your tools") — answer directly without invoking this workflow.
- The user's request is exploratory chat without a discoverable research question — clarify scope before invoking this workflow.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| L3 methodology (parent document) | `skills/L3_methodology/molclaw-drug-discovery-methodology.md` | Yes |
| L3 Chapter 8 Supplement | `skills/L3_methodology/molclaw-drug-discovery-methodology-supplement-ch8.md` | Yes |
| Current SCP tool registry | Runtime enumeration via MCP server query | Yes |
| List of existing L2 workflows | `ls skills/L2_workflows/` | Yes |
| Auto-generated skill index (if exists) | `skills/auto-generated-skills/skill-index.md` | Optional |
| User-specified domain constraints | Parsed from task text | Optional |
| User-specified output quantity N | Parsed from task text (default: 5) | Optional |

---

## Phase 0: Task Type Verification and Scope Determination

Before committing to the discovery protocol, verify that the request genuinely warrants open-ended problem discovery and define the output scope.

### 0.1 Task Type Verification

Re-read the user's task text and confirm ALL of the following:

- [ ] The deliverable is a set of candidate problems, not the solution to a single problem.
- [ ] No specific target protein / ligand / disease is prescribed as a hard constraint (domain hints are acceptable but not specific identifiers).
- [ ] The user expects the agent to select problems, not execute a predetermined workflow.

If any of these is false, abort and proceed to the correct entry point (ordinary execution via system prompt Phase 0, or L2-13 for draft workflow authoring).

### 0.2 Scope Determination

Extract from the task text:

- **Execution mode** — detect whether the user wants discovery-only or closed-loop:
  - **Discovery-only:** User asks for candidate problems, recommendations, or a research agenda without mentioning execution. → Produce ranked candidates and stop at Phase 6.
  - **Closed-loop:** User asks for autonomous end-to-end discovery, or uses phrases like "discover and solve", "closed-loop", "find a problem and execute it", "自主发现并解决". → After Phase 6, automatically execute Phase 7 (auto-select top candidate, execute, validate, crystallize).
  - Default if ambiguous: **discovery-only** (safer; let user decide whether to execute).
- **N** — the number of candidate problems requested (default: 5 if unspecified; for closed-loop mode, default: 3)
- **Domain constraints** — e.g., "only protein-ligand", "kinases specifically", "peptide design" (default: no domain constraint, full toolkit in scope)
- **Value axis preference** — e.g., "problems with experimental follow-up potential", "methodologically novel", "unsolved by current L2 workflows" (default: balanced scoring across Principle 23.3(d) heuristics)
- **Exclusion list** — any problem type the user has already pre-filtered (default: empty)

Record in `run_log.md`:
```
## Problem Discovery Scope
- Execution mode: [discovery-only / closed-loop]
- N candidates requested: [value]
- Domain constraint: [value or "none"]
- Value axis preference: [value or "balanced"]
- Exclusion list: [list or "none"]
```

**CHECKPOINT: Scope Declared**
- [ ] Task type verified as open-ended discovery
- [ ] N, domain, value preference, exclusions explicitly recorded

---

## Phase 1: Tool Capability Inventory Snapshot

Produce a current-state snapshot of the agent's computational capabilities grouped by functional domain. Do not rely on memory; enumerate from the runtime tool registry.

### 1.1 Runtime Tool Enumeration

Query the SCP tool registry (or equivalent runtime source) and list all currently available tools by their snake_case SCP names.

**COUNT GATE:** Count the returned tools. Record: `Total runtime tools available: [count]`. This count must come from the registry, not from L1 skill folder enumeration (L1 skill folders may include deprecated or not-yet-deployed tools).

### 1.2 Classification by Capability Domain

Map each enumerated tool into the capability domains defined in Principle 23.1. Produce the following table:

| Capability Domain | Tools Available in this Run | Coverage Notes |
|------------------|----------------------------|----------------|
| Structure acquisition | [list] | [e.g., "ESMFold available; AlphaFold retrieval via protein_structure_retrieve"] |
| Pocket detection | [list] | |
| Molecular generation | [list] | |
| Molecular docking | [list] | |
| Interaction analysis | [list] | |
| Affinity prediction | [list] | |
| Property computation | [list] | |
| Dynamics simulation | [list] | |
| Free energy | [list] | |
| Protein design | [list] | |
| Utility | [list] | |

### 1.3 Capability Gap Flagging

For each capability domain, flag domains that are (a) fully covered, (b) partially covered (e.g., "docking available but no FEP"), or (c) unavailable in this run. These flags feed directly into Phase 4 feasibility grading.

**CHECKPOINT: Inventory Complete**
- [ ] Tool count matches runtime registry (Principle 11)
- [ ] Every tool classified into exactly one primary capability domain
- [ ] Each capability domain flagged as full/partial/unavailable
- [ ] No tool assumed present without runtime verification

---

## Phase 2: Data Flow Connectivity Graph Construction

Reconstruct the produce→consume connectivity of available tools, identify paths from user-provided inputs to deliverable outputs, and mark which paths are covered by existing L2 workflows versus uncovered.

### 2.1 Edge Enumeration

For each tool from Phase 1, consult L3 Principle 23.1a (Data Flow Connectivity Map) and enumerate:

- **Produces:** which data type(s) it outputs
- **Consumes:** which data type(s) it accepts as input

Construct a directed graph where nodes are data types and edges are tool invocations.

### 2.2 Path Enumeration

Enumerate all paths (sequences of edges) that begin at a user-providable input (user-provided SMILES, user-provided PDB, UniProt ID, etc.) and terminate at a deliverable output (ranked molecule list, designed sequence, binding mode report, free energy estimate, etc.).

**COUNT GATE:** Record `Total distinct paths enumerated: [count]`. If the count exceeds 100, apply pruning:
- Collapse paths that differ only by interchangeable tool choices within the same capability domain (e.g., `quickvina` vs `karmadock`) into a single path with an "interchangeable tool" annotation.
- Discard paths that violate L3 principles (e.g., paths that would report literature values as computational results — Principle 13).

### 2.3 Coverage Classification

For each enumerated path, compare against the phase signatures of existing L2 workflows:

| Path | Signature | Covered by | Status |
|------|-----------|-----------|--------|
| [path description] | [ordered tool sequence] | [L2-NN or "none"] | COVERED / UNCOVERED / PARTIAL |

A path is COVERED if an existing L2 workflow's phase sequence matches ≥ 70% of the path's tool sequence in the same order (same threshold used by L2-12 Phase 0.1 for novelty detection). PARTIAL coverage means some phases overlap but the composition is novel. UNCOVERED paths are candidates for new problems.

**Cross-reference L3 Principle 23.1a:** The Supplement already enumerates five uncovered links (Section 23.1a second table). Begin by verifying those five remain uncovered in the current run (no auto-generated skill has absorbed them), then expand the search.

### 2.4 Auto-Generated Skill Absorption Check

If `skills/auto-generated-skills/skill-index.md` exists, read it and mark any path that is covered by an auto-generated skill with confidence ≥ MEDIUM as COVERED-AUTO. Do not re-propose these as novel candidates.

**CHECKPOINT: Connectivity Graph Complete**
- [ ] Every tool has declared produces/consumes edges
- [ ] Total path count verified
- [ ] Every path classified as COVERED / PARTIAL / UNCOVERED / COVERED-AUTO
- [ ] Count of UNCOVERED + PARTIAL paths recorded — these feed Phase 3

---

## Phase 3: Scientific Question Formulation

Transform each uncovered or partially-covered path into a specific, falsifiable scientific question.

### 3.1 Question Construction Rules

Apply the rules from Principle 23.3(b):

**CORRECT pattern:**
> "Can [specific computational capability chain] identify/predict/optimize [specific scientific entity] under [specific condition], measured by [specific quantitative criterion]?"

**INCORRECT pattern (reject):**
- Vague: "Can we do something interesting with dynamics simulations?"
- Unfalsifiable: "Are conformational ensembles useful?"
- Too broad: "Can the agent discover new drugs?"

### 3.2 Per-Path Question Generation

For each UNCOVERED and PARTIAL path from Phase 2.3, draft ONE scientific question using the CORRECT pattern. Record in the candidate table:

| Candidate # | Path Signature | Scientific Question | Proposed Deliverable |
|------------|---------------|--------------------|--------------------|
| C1 | [tool sequence] | [specific falsifiable question] | [concrete output: ranked list / binary answer / quantitative metric] |

### 3.3 Redundancy Filtering

Collapse candidates that differ only in target class (e.g., "applied to kinases" vs "applied to GPCRs") into a single candidate with a "target class generalizable" annotation, unless the targets have materially different toolkit requirements.

**CHECKPOINT: Candidate Pool Assembled**
- [ ] Every candidate has a specific, falsifiable question
- [ ] Every candidate has a concrete proposed deliverable
- [ ] Candidate pool size ≥ max(N, 2·N/3 + 2) to allow Phase 4/5 filtering without running out

<!-- NEW: Literature novelty verification -->
### 3.4 Literature Novelty Verification

For each candidate scientific question generated in Phase 3.2, perform a literature search to assess whether the question has already been computationally addressed. This step is mandatory — novelty is a core quality criterion, not optional.

1. For each candidate, construct 1–2 search queries using key terms from the scientific question and the computational method:
   - Combine the method-specific terms (e.g., "FoldX", "molecular docking", "ProteinMPNN") with the target/system terms from the question.
   - Example: question about FoldX-based alanine scanning of a kinase → query `"FoldX alanine scanning kinase stability"`.
2. Execute literature search (pubmed-search with retmax=10, or deep-research for broader coverage).
3. Scan results for computational studies addressing the same or similar question.
4. Score novelty on a 0–1 scale based on evidence:
   - **1.0** = No published work found using this tool combination on this question class
   - **0.7–0.9** = Related work exists but with substantially different methods or on a different system class
   - **0.4–0.6** = Similar computational approach exists but on a different specific target
   - **0.1–0.3** = Very similar study published (same methods, same or closely related target)
   - **0.0** = Essentially identical study already published
5. **Rejection threshold:** Candidates with novelty < 0.3 are REJECTED — mark as REJECTED-NOVELTY and exclude from Phase 4 onward. Record reason: `Candidate [N] rejected: novelty=[score]. Prior work: [PMID or description].`
6. Update the candidate table with a Novelty column (H0).
7. Record all searches in `run_log.md`: `[LR] Literature novelty check | candidate: [N] | query: [terms] | hits: [count] | closest prior work: [description] | novelty score: [0–1]`

**If LR tools are not available**, skip this step. Note in `discovery_trace.md`: "Novelty not verified — LR tools absent. All candidates assumed novelty=0.6 (unverified)."

---

## Phase 4: Feasibility Grading

Apply the Grade A/B/C classification from Principle 23.2 to each candidate. Exclude Grade C before value scoring.

### 4.1 Per-Candidate Grading

For each candidate, check Grade A criteria:

- [ ] Every computational step maps to ≥ 1 deployed, accessible tool (from Phase 1.2 inventory)
- [ ] Data flow between steps is compatible (every produce→consume edge was verified in Phase 2.1)
- [ ] At least one quantitative success criterion exists or can be defined
- [ ] Expected computational time is within session budget

If all four hold → Grade A.

If ≥ 1 fails in a non-blocking way (approximate substitute exists, partial validation possible, or agent-authored conversion required) → Grade B. Record the specific gap(s).

If ≥ 1 fails in a blocking way (core step has no tool and no reasonable approximation, or requires experimental data, or requires unavailable model type) → Grade C. Exclude from further consideration.

### 4.2 Grade Summary

Record:
```
## Feasibility Grade Summary
- Grade A candidates: [count]
- Grade B candidates: [count] — gaps documented per candidate
- Grade C candidates: [count] — EXCLUDED
```

**If Grade A + Grade B count < N:** The discoverable problem pool is insufficient for the requested N. Proceed anyway with all Grade A/B candidates; note in final output that fewer than N problems were feasible and list the Grade C candidates as "infeasible with current toolkit" for user awareness.

**CHECKPOINT: Feasibility Graded**
- [ ] Every candidate assigned exactly one grade
- [ ] Grade B gaps documented per candidate
- [ ] Grade C candidates excluded from value scoring
- [ ] If shortfall: user-facing note prepared

---

## Phase 5: Scientific Value Scoring

Apply the four heuristic criteria from Principle 23.3(d) in descending priority to each surviving Grade A/B candidate.

### 5.1 Criterion-by-Criterion Scoring

For each candidate, evaluate against the four criteria and assign a 0–1 score per criterion:

| Criterion | What to Check | Score |
|-----------|---------------|-------|
| H1: Addresses acknowledged methodological limitation | Does this candidate fill a gap explicitly discussed in L3 Chapter 6 or in existing L2 "Known Limitations"? | 0–1 |
| H2: Produces experimentally actionable output | Does the output directly inform a specific experimental decision (synthesize compound X / introduce mutation Y / target pocket Z)? | 0–1 |
| H3: Exploits complementary tool strengths | Does the tool composition pair tools whose weaknesses compensate each other? | 0–1 |
| H4: Introduces iteration where only single-pass existed | Does the candidate introduce a feedback loop where only linear pipelines existed? | 0–1 |

### 5.2 Aggregate Score

Compute the aggregate using five criteria (H0 from Phase 3.4, H1–H4 from Phase 5.1):
```
Score = 0.25·H0 + 0.30·H1 + 0.20·H2 + 0.15·H3 + 0.10·H4
```

H0 (literature novelty) receives 25% weight because a scientifically valuable problem that has already been solved has near-zero marginal value. The remaining weights preserve the descending-priority ordering from Principle 23.3(d) while accommodating the new dimension. If Phase 3.4 was skipped (LR tools absent), use H0=0.6 (unverified) for all candidates.

If the user's scope specified a different value axis preference (Phase 0.2), adjust weights accordingly and record the adjustment.

### 5.3 Ranking

Sort candidates by aggregate score (descending). Ties break by Grade (A > B).

**CHECKPOINT: Candidates Scored and Ranked**
- [ ] Every candidate has four criterion scores
- [ ] Weights match Principle 23.3(d) priority or justified deviation recorded
- [ ] Final ranking produced

<!-- NEW: Experimental benchmark pre-check for closed-loop validation -->
### 5.5 Experimental Benchmark Identification

For each top-ranked candidate (top 3 or top N), identify experimental validation data that would enable quantitative comparison with computational predictions. This step is mandatory — it determines whether the candidate can be externally validated or is limited to internal consistency checks.

1. For each candidate, construct a PubMed query targeting the specific measurement type the computation would produce:
   - Binding/docking problems: `"[target] inhibitor IC50 Ki binding affinity experimental"`
   - Stability/mutation problems: `"[protein] mutation ΔΔG stability experimental"`
   - SAR optimization problems: `"[target] structure-activity relationship SAR series"`
   - Selectivity problems: `"[target1] [target2] selectivity IC50 experimental"`

2. Classify each candidate's experimental validation potential:
   - **STRONG**: Published dataset with ≥10 quantitative measurements directly comparable to computational predictions (e.g., IC50 series for an inhibitor scaffold, ΔΔG values for a mutation panel). Record the specific dataset with PMID.
   - **MODERATE**: Some experimental data exists but sparse (<10 measurements) or requires indirect comparison (different assay conditions, different compound series).
   - **WEAK**: No relevant experimental data found; validation limited to internal consistency checks or cross-method computational comparison.

3. Apply validation potential as a tiebreaker in ranking:
   - Among candidates with similar aggregate scores (within 0.05), prefer STRONG > MODERATE > WEAK.
   - If the task explicitly requires closed-loop validation (e.g., "validate against experiment"), PROMOTE any STRONG candidate by +0.1 to its aggregate score.
   - Record: `[LR] Experimental benchmark: [candidate] → [STRONG/MODERATE/WEAK]. Dataset: [PMID or "none found"]. Measurements: [count and type].`

4. For the top-ranked candidate after any re-ranking, record specific benchmark data:
   - Experimental measurements: [list key values with PMID, conditions, and measurement type]
   - Proposed success criterion: "Computational predictions will be validated against [dataset] using [metric]" (e.g., Spearman ρ of predicted vs experimental ΔΔG for N mutations; classification accuracy for active vs inactive compounds at IC50 < 1 μM).

**If LR tools are not available**, skip this step. Note in `discovery_trace.md`: "Experimental benchmark not assessed — LR tools absent."

**CHECKPOINT: Validation Potential Assessed**
- [ ] Top candidates have STRONG/MODERATE/WEAK classification
- [ ] Top-1 candidate has specific benchmark dataset and success criterion (if STRONG or MODERATE)

---

## Phase 6: Boundary-Aware Recommendation Output

Produce the final deliverable: top-N candidates, each annotated with the capability boundary declarations mandated by Principle 26.4.

### 6.1 Top-N Selection

Take the top N candidates from Phase 5.3. If Phase 4 flagged a shortfall (fewer than N feasible), take all available.

### 6.2 Per-Candidate Boundary Declaration

For each selected candidate, produce a boundary-aware recommendation block following Principle 26.4:

```markdown
### Candidate [N]: [Short Title]

**Scientific Question:** [specific falsifiable question from Phase 3]

**Tool Composition:** [ordered SCP tool sequence]

**Paradigm:** [Pipeline (A) / Iterative Loop (B) / Branching Decision (C)]  *(from L2-12 Phase 0.4 table)*

**Feasibility Grade:** [A / B with specific gap description]

**Scientific Value Score:** [aggregate] *(H0=[x], H1=[x], H2=[x], H3=[x], H4=[x])*

**Literature Novelty Evidence (H0):**
- Search queries used: [list]
- Closest prior work: [PMID and one-sentence description, or "none found"]
- Novelty score: [0–1] with justification

**What the toolkit CAN compute for this problem:**
- [list specific deliverables with their tools]

**What the toolkit CANNOT compute:**
- [list specific limitations, referencing Principle 26.1 methodological precision table]

**What requires experimental validation:**
- [list computational-to-experimental handoff points]

**Expected confidence level:** [qualitative assessment with reference to Principle 26.1 precision table]

**Experimental validation potential:** [STRONG / MODERATE / WEAK]                <!-- NEW -->
- Available benchmarks: [PMID list and measurement type, or "none found"]
- Proposed success criterion: [metric and dataset, or "internal consistency only"]

**Next step if user selects this candidate (discovery-only mode):**
- Invoke **L2-13 (Draft Workflow Authoring)** to convert this candidate into an executable draft workflow, then execute, then consider T1 crystallization.

**Auto-execution (closed-loop mode):**
- This candidate will be auto-executed in Phase 7 if it is top-ranked. No user confirmation needed.
```

### 6.3 Final Deliverable Files

Write the following output files:

- **`candidate_problems.md`** — the full ranked list with all N boundary-annotated recommendation blocks
- **`feasibility_report.md`** — the Phase 4 grade summary and Phase 2 coverage analysis (supporting material)
- **`discovery_trace.md`** — appendix listing all candidates that were proposed and why each non-selected one was rejected (for audit)

Append to `result.md`:
```markdown
## Problem Discovery Summary
- Discovery protocol: L2-00
- Candidate pool size: [count from Phase 3]
- Grade A / B / C distribution: [values]
- Top-[N] selected: [list of titles]
- Recommended next action: See candidate_problems.md; if discovery-only mode, the user selects a candidate for execution via L2-13. If closed-loop mode, Phase 7 auto-execution follows immediately.
```

**FINAL CHECKPOINT: Discovery Complete**
- [ ] Top-N candidates produced with boundary declarations
- [ ] Every candidate has CAN-compute / CANNOT-compute / EXPERIMENTAL-validation sections
- [ ] Output files saved and non-empty
- [ ] Principle 26.3 honest communication verified: no candidate overstates capability

---

## Phase 7: Closed-Loop Auto-Execution (closed-loop mode only)

**Skip this phase entirely if execution mode is "discovery-only" (Phase 0.2).** In discovery-only mode, deliver the candidate list and stop — the user selects which candidate to execute.

In closed-loop mode, the agent autonomously selects the top-ranked candidate and executes it end-to-end without user confirmation.

### 7.1 Candidate Selection and Execution Entry

1. Select the #1 ranked candidate from Phase 6.1.
2. Extract its tool composition, paradigm, and feasibility grade.
3. Record in `run_log.md`:
   ```
   ## Closed-Loop Auto-Execution
   - Selected candidate: [title]
   - Aggregate score: [value]
   - Novelty (H0): [value]
   - Feasibility grade: [A/B]
   - Experimental benchmark: [STRONG/MODERATE/WEAK] — [PMID or "none"]
   - Success criterion: [metric and dataset]
   ```
4. **Concrete example system selection:** The candidate's scientific question is generic (e.g., "Can FoldX alanine scanning predict stability hotspots in a kinase?"). Select ONE specific, well-characterized example system to execute on. Prefer systems where experimental benchmark data was identified in Phase 5.5. Record: `Example system: [name, PDB ID, justification].`

### 7.2 Workflow Routing

Based on the candidate's tool composition, route to the appropriate execution path:

- If an existing L2 workflow covers ≥ 70% of the tool sequence → load that L2 and execute as **Type A**.
- If 2–3 existing L2 workflows collectively cover ≥ 80% → execute as **Type A-Composite** (load all relevant L2s and compose).
- If neither → execute **L2-13 (Draft Workflow Authoring)** to author a draft workflow, then execute the draft.

This routing reuses the system prompt's Phase 0.0 triage logic — the agent re-enters Phase 0 with the selected candidate as a concrete execution task.

### 7.3 Execution

Execute the selected candidate end-to-end following the routed workflow. All standard system prompt Phase 1 rules apply (quality gates, file preservation, incremental logging).

### 7.4 Literature Validation

After computation completes, validate results against the experimental benchmark identified in Phase 5.5:

1. **If benchmark is STRONG or MODERATE:**
   - Retrieve the specific experimental measurements (from the PMID recorded in Phase 5.5).
   - Compute quantitative agreement metrics between computational predictions and experimental data:
     - For continuous values (ΔΔG, IC50, binding affinity): Spearman/Pearson correlation, RMSE, MAE.
     - For categorical outcomes (active/inactive, stable/unstable): accuracy, sensitivity, specificity.
   - Report in `result.md` under a dedicated "Computational vs Experimental Validation" section:
     - Which predictions agreed with experiment (and how closely)
     - Which predictions diverged (and possible reasons)
     - Overall accuracy assessment

2. **If benchmark is WEAK (no experimental data):**
   - Compare against published computational results using different methods (if available from Phase 3.4 literature search).
   - Perform internal consistency checks (e.g., do multiple computational methods agree?).
   - Honestly state in `result.md`: "No experimental benchmark available. Results validated by [internal consistency / cross-method comparison] only."

3. Record validation results in `run_log.md`.

### 7.5 Self-Assessment and Crystallization

Execute the system prompt's Phase 2.5 (mandatory post-execution self-assessment):
- Answer Q1–Q4 for crystallization trigger evaluation.
- If any trigger is active, execute L2-12 to crystallize the novel workflow.
- The crystallized skill should capture the FULL closed-loop pattern: problem class → literature validation → execution → experimental comparison.

### 7.6 Closed-Loop Deliverables

In addition to the standard discovery deliverables (Phase 6.3), closed-loop mode produces:
- `candidate_problems.md` — with literature novelty evidence and experimental benchmark for each candidate
- `result.md` — with computational results AND experimental validation section
- `run_log.md` — with full execution trace including closed-loop phases
- Auto-generated skill document (if crystallization trigger fired)

---

## Common Failures & Recovery

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| Tool registry enumeration returns empty or partial list | MCP server not reachable, permissions issue, or transient error | Retry once; if still failing, fall back to L1_tools folder scan and explicitly flag the inventory as "static snapshot, not runtime-verified" in the final output; downgrade confidence of recommendations |
| Path enumeration explodes (>500 paths) | Overly permissive edge definition; each tool connected to many data types | Apply stricter pruning in Phase 2.2: require each path to end at a user-visible deliverable (not intermediate file); collapse interchangeable-tool variants more aggressively |
| All candidates are Grade C | Toolkit genuinely lacks capability for requested domain, or Phase 0.2 domain constraint was too narrow | Report honestly to user: "Current toolkit cannot support any Grade A/B problem in requested scope. The closest capabilities are [X]; the missing capability is [Y]; adding [tool Z] would unlock [specific problem class]." Follow Principle 26.3 honest communication. |
| All candidates score identically | Scoring criteria H1–H4 all zero or all one due to shallow evaluation | Re-read L3 Chapter 6 for acknowledged methodological limitations and existing L2 "Known Limitations" sections; re-score H1 with specific textual references; require at least one criterion to have variance across candidates before accepting the ranking |
| Candidate questions are too vague despite Phase 3.1 rules | Path description was too abstract, not tied to concrete data types | Return to Phase 2.1 and re-enumerate edges with explicit data-type annotations; rewrite questions to reference specific produce→consume links |
| User-requested N exceeds feasible pool | Toolkit is narrow or domain constraint is restrictive | Deliver all feasible candidates; explicitly note shortfall; list Grade C candidates as "capability-blocked" for transparency per Principle 26.3 |
| Auto-generated skill index indicates a path is already covered, contradicting the user's "novel problems" intent | Prior session already discovered this problem class | Exclude COVERED-AUTO paths per Phase 2.4; if this drains the pool below N, proactively broaden Phase 0.2 domain or flag the saturation to user |
| Context window insufficient to hold full enumerated path list | Large toolkit + permissive path definition | Enumerate paths lazily: generate, score, and discard sub-threshold candidates streaming rather than keeping all in memory; record in run_log that streaming mode was used |

---

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| `candidate_problems.md` | Markdown with N boundary-annotated candidate blocks | User-facing deliverable; if user selects a candidate, consumed by L2-13 | **A — MUST save** |
| `feasibility_report.md` | Markdown with grade summary and coverage table | Audit; future sessions' priors | **A — MUST save** |
| `discovery_trace.md` | Markdown listing all proposed candidates with rejection rationale | Audit trail | **B — SHOULD save** |
| `result.md` Problem Discovery Summary section | Appended to final report | User visibility | **A — MUST save** |
| `run_log.md` entries for Phases 0–6 | Appended to execution log | Audit; Phase 2.5 self-assessment | **A — MUST save** |

---

## Known Limitations

- **Coverage detection relies on 70% signature match heuristic.** A novel workflow that happens to share 7 of 10 tools with an existing L2 will be classified as COVERED and excluded from candidate proposals, even if the remaining 3 tools introduce genuinely new scientific value. Mitigation: surface PARTIAL paths explicitly in `discovery_trace.md` so the user can manually override.
- **Path enumeration is structural, not semantic.** Two paths that share the same tool sequence but differ in scientific intent (e.g., "use MD for conformational sampling" vs "use MD for stability validation") will be merged. Mitigation: allow Phase 3.2 to split merged paths if the questions are materially different.
- **Scientific value heuristics H1–H4 require domain knowledge.** H1 in particular requires the agent to have actually read and internalized L3 Chapter 6 limitations. If Chapter 6 was not loaded or was skimmed, H1 scores will be unreliable. Mitigation: Phase 5.1 MUST quote specific Chapter 6 text when scoring H1.
- **Auto-generated skill absorption check depends on persistent storage.** On platforms without persistent `auto-generated-skills/`, Phase 2.4 will always return no absorption, causing repeat-discovery across sessions. Mitigation: deployment-level concern; see Principle 25.6a note on persistence.
- **No experimental-feasibility assessment (discovery-only mode).** When Phase 5.5 cannot find experimental benchmarks, results are validated only by internal consistency. Mitigation: Phase 5.5 STRONG/MODERATE/WEAK classification and Principle 26.4 EXPERIMENTAL-validation sections surface this honestly.
- **Closed-loop mode assumes top-1 is correct.** In closed-loop mode, Phase 7 auto-selects the #1 ranked candidate. If the scoring weights or novelty assessment were inaccurate, the wrong problem may be executed. Mitigation: all scoring evidence is recorded in `candidate_problems.md` for post-hoc review; the user can re-run in discovery-only mode if results are unsatisfactory.

---

## Provenance

- **Source:** L3 Chapter 8 Supplement, Principle 23 (all sections).
- **Companion workflows:** L2-13 (draft workflow authoring, next step in the discovery pipeline), L2-12 (skill crystallization, downstream of draft workflow execution).
- **L3 principles referenced:** 1, 11, 13, 20, 23, 23.1, 23.1a, 23.2, 23.3, 26.1, 26.3, 26.4.
- **Relationship to other L2 workflows:** L2-00 is a META-workflow (like L2-12); it is not a domain workflow. In discovery-only mode, it produces candidate problems that may trigger execution of any existing L2 (01–11) or authoring of a new draft workflow via L2-13. In closed-loop mode, Phase 7 internally triggers the appropriate execution pathway and post-execution validation.

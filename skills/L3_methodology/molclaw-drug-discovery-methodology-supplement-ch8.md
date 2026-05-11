---
name: molclaw-drug-discovery-methodology-supplement-ch8
description: >
  Supplementary chapter to the L3 methodology skill. Extends the existing 22 principles
  (Chapters 1–7) with Chapter 8: Autonomous Scientific Discovery and Skill Self-Generation.
  Provides the agent with governance principles for identifying solvable scientific problems,
  authoring novel workflows, crystallizing execution experience into reusable skill documents,
  and maintaining honest self-awareness of capability boundaries. This supplement MUST be
  loaded together with the parent L3 methodology document. All principles herein are
  subordinate to and cross-reference the parent document's Chapters 1–7.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L3-Methodology-Supplement
    version: 1.0
    parent-document: molclaw-drug-discovery-methodology (v2.0-enhanced)
    parent-principles-referenced: 1, 3, 5, 7, 8, 9, 10, 11, 12, 13, 17, 19, 20, 22
    chapter-range: Chapter 8 (Principles 23–26)
    summary: >
      Four new principles governing the agent's transition from static skill executor to
      self-evolving scientific partner: (23) capability landscape mapping with data flow
      connectivity map, problem feasibility assessment, and scientific value heuristics;
      (24) autonomous workflow authoring under strict quality constraints with paradigm matching;
      (25) experiential crystallization of execution traces into reusable skill documents,
      including five triggers (T1–T5), failure-triggered retrieval, and skill revision protocol;
      (26) dynamic capability boundary self-awareness with methodological precision reference.
---

# MolClaw Drug Discovery Methodology — Chapter 8 Supplement

# Chapter 8. Autonomous Scientific Discovery and Skill Self-Generation

> **Scope and relationship to Chapters 1–7.** Chapters 1–7 govern HOW the agent executes tasks: planning (Ch. 1), iterating (Ch. 2), verifying data (Ch. 3), collecting files (Ch. 4), handling structural biology (Ch. 5), applying strategic guidance (Ch. 6), and reporting (Ch. 7). Chapter 8 governs WHAT the agent does when it encounters problems beyond existing workflow coverage, and HOW it converts novel execution experience into persistent, reusable knowledge. This chapter does not override any principle from Chapters 1–7; all prior principles remain fully binding during autonomous discovery and skill generation.

> **When to load this supplement.** Load this document alongside the parent L3 methodology whenever: (a) the task does not cleanly map to any existing L2 workflow; (b) the agent is asked to identify or propose scientific problems solvable with its current toolkit; (c) the task explicitly involves workflow design, protocol development, or methodology documentation; or (d) the agent has completed a task and is performing post-execution self-assessment.

> **Operationalization pointers.** The principles in this chapter are operationalized by three L2 meta-workflows. If Phase 0.0 of the system prompt classified the task as **Type B (open-ended problem discovery)**, load and execute `L2_workflows/00-problem-discovery-and-feasibility-triage.md` — it executes Principle 23 as a step-by-step procedure. If Phase 0.0 classified the task as **Type C (concrete task with no existing L2 coverage)**, load and execute `L2_workflows/13-draft-workflow-authoring.md` — it executes Principle 24 as a step-by-step procedure. After any task, if Phase 2.5 self-assessment detects an active crystallization trigger (T1–T5), load and execute `L2_workflows/12-skill-crystallization.md` — it executes Principle 25. Principle 26 is continuous and has no dedicated workflow; it is invoked within the above three at every boundary-declaration point.

---

## Principle 23: Capability Landscape Mapping and Problem Feasibility Assessment

Before the agent attempts any task not covered by an existing L2 workflow, or when the agent is asked to identify scientific problems solvable with its toolkit, it MUST perform a structured capability and feasibility assessment. This principle extends Principle 1 (Understand Before Acting) to the meta-level of problem selection.

### 23.1 Tool Capability Inventory

The agent should maintain a functional understanding of its tool ecosystem organized by computational capability rather than by individual tool name. The capability categories are:

| Capability Domain | Representative Tools | Input → Output |
|------------------|---------------------|----------------|
| Structure acquisition | RCSB PDB, UniProt, AlphaFold DB, ESMFold, Chai-1 | Identifier/sequence → 3D structure |
| Pocket detection | fpocket, P2Rank | Protein structure → binding site coordinates |
| Molecular generation | REINVENT4 (6 modes), LLM-guided design | Seed/scaffold → novel molecules |
| Molecular docking | QuickVina2-GPU, DiffDock, KarmaDock | Protein + ligand → binding pose + score |
| Interaction analysis | interaction-visualizer (local, primary), ProLIF (MCP, batch/trajectory), PLIP | Complex structure → interaction fingerprint / visualization / decision JSON |
| Affinity prediction | Boltz-2, EquiScore | Protein-ligand pair → predicted affinity |
| Property computation | RDKit (8 modules), ADMET-AI | SMILES → physicochemical/ADMET profile |
| Dynamics simulation | GROMACS, OpenMM, GoCa, OpenAWSEM | Structure → trajectory → ensemble |
| Free energy | gmx_MMPBSA | Trajectory → ΔG decomposition |
| Protein stability & mutation | FoldX (8 modes: RepairPDB, Stability, BuildModel, AlaScan, PositionScan, Pssm, AnalyseComplex, SequenceDetail) | Protein structure (± mutations) → ΔG, ΔΔG, interface energy, per-residue decomposition, PSSM |
| Protein design | ProteinMPNN, EvoBind, Chroma | Target structure → designed sequence/structure |
| Utility | RDKit similarity, SMILES editor, residue mapper, file transfer | Format conversion, mapping, validation |

### 23.1a Data Flow Connectivity Map

The capability inventory (Section 23.1) describes what each tool does in isolation. To identify novel workflow opportunities, the agent needs to understand how tools connect — which tool's output serves as another tool's input. The following table maps computational data types to the tools that PRODUCE them and the tools that CONSUME them. A valid workflow is any path from a user-provided input through one or more produce→consume links to a deliverable output.

| Data Type | Produced By | Consumed By |
|-----------|------------|-------------|
| Clean protein PDB | L2-01 (pdbfixer, fix_pdb) | Docking (quickvina), Pocket detection (fpocket, p2rank), MD (openmm), CG sim (goca, openawsem), Protein design (proteinmpnn), FoldX repair (foldx_tool repairpdb) |
| FoldX-repaired PDB | foldx_tool (repairpdb) | foldx_tool (all other modes: stability, buildmodel, analysecomplex, alascan, positionscan, pssm, sequencedetail) |
| Stability ΔG | foldx_tool (stability) | Mutation comparison (before/after), Design validation (L2-10 Scene E cross-check) |
| Mutation ΔΔG | foldx_tool (buildmodel, positionscan) | Mutation ranking and selection (L2-10 Scene B), Thermostability design (L2-10 Scene F) |
| Interface interaction energy | foldx_tool (analysecomplex) | Interface assessment (L2-06 fast path, L2-08 Module 2C), Binder validation (L2-09) |
| AlaScan ΔΔG per-residue | foldx_tool (alascan with chains) | Hotspot identification, Peptide target_residues (L2-09 Step 2), Residue classification (L2-10 Scene F) |
| PSSM matrix | foldx_tool (pssm) | Affinity maturation (L2-09 Round 2), Position tolerance analysis (L2-10) |
| Pocket coordinates + box | fpocket, p2rank | Docking box definition (quickvina, karmadock) |
| Ligand SMILES | User input, REINVENT4, LLM design, PubChem retrieval | Docking (quickvina), Property calc (rdkit modules, admet_ai), Affinity pred (boltz2), Similarity (morgan_fp), SMILES editor |
| Docked pose (PDBQT/SDF) | quickvina, diffdock, karmadock | Interaction analysis (interaction-visualizer primary, prolif for batch, plip), Rescoring (equiscore), Visualization |
| Interaction fingerprint | interaction-visualizer (primary), prolif (batch/trajectory), plip | SAR reasoning (agent), Selectivity comparison (cross-target), Optimization diagnosis |
| Interaction visualization (2D diagram, 3D rendering, decision JSON) | interaction-visualizer | L2 Report assembly, Agent decision loop (top_residues/hot_partner_sites), L2-05 optimization diagnosis (partner_site.csv) |
| Binding affinity score | boltz2, equiscore, quickvina score | Ranking, Iterative optimization seed selection, Convergence assessment |
| ADMET profile | admet_ai | Filtering, Multi-objective optimization, Safety assessment, Deterioration monitoring |
| Physicochemical properties | rdkit (8 modules) | Drug-likeness filtering, QED computation, Optimization diagnosis, Constraint checking |
| MD trajectory | openmm, gromacs | Free energy (gmx_mmpbsa), Interaction dynamics (prolif_md), Conformational analysis |
| CG trajectory | goca, openawsem | Frame extraction → PULCHRA reconstruction |
| All-atom ensemble (multiple PDBs) | PULCHRA from CG, openmm frames, bioemu | Per-conformation pocket detection, Ensemble docking, Conformational diversity analysis |
| ΔG decomposition | gmx_mmpbsa | Per-residue contribution analysis, Hotspot identification, Binding mode validation |
| Designed peptide sequence | evobind | Chai-1 validation, HDOCK docking, interaction-visualizer interface analysis (peptide mode) |
| Designed protein sequence | proteinmpnn | ESMFold self-consistency check, Chai-1 complex prediction |
| Predicted complex structure | chai1, boltz2 | Interaction analysis (interaction-visualizer primary, prolif for batch/trajectory, plip), Visualization, Interface assessment |

**Existing L2 workflow coverage.** The following produce→consume links are covered by existing L2 workflows:

| Link | Covered by L2 |
|------|--------------|
| Clean PDB → pocket → docking → ranking | L2-02 |
| SMILES → property calc → filtering | L2-03 |
| Seed → REINVENT → new SMILES | L2-04 |
| Seed + target → [docking → evaluation → design → verify]×N | L2-05 |
| Complex → MD → ΔG decomposition | L2-06 |
| PDB → CG sim → frame extraction → all-atom ensemble | L2-07 |
| Docked pose → rescore → fingerprint → consensus ranking | L2-08 |
| Target → peptide design → independent validation | L2-09 |
| Target → protein design → self-consistency check → iteration | L2-10 |
| Molecule + multi-target → cross-docking → selectivity residues | L2-11 |
| Clean PDB → FoldX repair → mutation ΔΔG → stabilizing mutation selection | L2-10 (Scene B, enhanced with FoldX) |
| Complex PDB → FoldX AlaScan → hotspot residues → peptide design target_residues | L2-09 (enhanced with FoldX) |
| Complex PDB → FoldX AnalyseComplex → interface energy ranking | L2-06 (fast path), L2-08 (Module 2C) |

**Uncovered links — candidate new workflows.** The following produce→consume links represent scientifically meaningful tool compositions NOT covered by any existing L2. The agent should consult this table when performing problem discovery (Section 23.3).

| Uncovered Link | Scientific Question | Grade | Paradigm |
|---------------|--------------------|----|------|
| All-atom ensemble → per-conformation pocket detection → pocket spatial clustering → focused docking on transient pockets | Can transient cryptic pockets be discovered and drugged computationally? | B (spatial clustering requires agent-authored code) | Pipeline (A), ref L2-07 |
| Multi-target cross-docking (L2-11) embedded as evaluation function in iterative optimization loop (L2-05) | Can a molecule be iteratively optimized for selectivity between homologous targets? | A | Iterative Loop (B), ref L2-05 |
| Full ADMET profile tracking with per-round deterioration alarm integrated into iterative optimization (L2-05) | Can multi-objective optimization avoid the "unmonitored endpoint" blind spot? | A | Iterative Loop (B), extends L2-05 Scene C |
| ΔG per-residue decomposition → hotspot residue identification → focused generation targeting hotspot contacts | Can free energy hotspots directly guide molecular generation strategy? | A | Pipeline (A), connects L2-06 output to L2-04 input |
| Same ligand docked into each conformation of an ensemble (from L2-07) → score distribution analysis | Does ensemble docking improve virtual screening hit rates over single-structure docking? | A | Pipeline (A), connects L2-07 to L2-02 |
| FoldX PSSM → per-position optimal AA → ProteinMPNN constrained redesign | Can energy-based mutation scanning constrain sequence design space to improve design success rate? | A | Pipeline (A), connects FoldX to L2-10 |
| FoldX AnalyseComplex (fast, minutes) → top N candidates → MMPBSA (precise, hours) | Can two-stage interface energy evaluation maintain accuracy while reducing computational cost? | A | Pipeline (A), connects FoldX fast screening to L2-06 |
| FoldX PositionScan (all interface positions) → mutation landscape heatmap → focused experimental validation | Can systematic computational mutation landscapes directly guide experimental alanine scanning or deep mutational scanning validation? | A | Pipeline (A), standalone or connects to L2-10 |
| [LR] PubMed literature search → known binder retrieval → compound-retrieve → docking comparison with literature controls | Can literature-informed virtual screening improve hit identification over blind screening by providing validated positive controls? | A | Pipeline (A), connects LR to L2-02 | <!-- NEW -->
| [LR] PubMed SAR search → functional group identification → SMILES fg-editor → targeted optimization | Can published SAR directly guide computational molecular optimization to break stagnation? | A | Pipeline (A), connects LR to L2-05 | <!-- NEW -->
| [LR] PubMed binding affinity search → experimental ΔG retrieval → MMPBSA cross-validation | Can literature binding data validate or calibrate MMPBSA computational predictions? | A | Pipeline (A), connects LR to L2-06 | <!-- NEW -->

When a self-generated skill successfully covers an uncovered link and reaches confidence ≥ MEDIUM, the link should be annotated as `Covered (auto-generated, [skill-name])` to prevent redundant re-discovery.

### 23.2 Problem Feasibility Classification

When confronting a task with no matching L2 workflow, classify it into one of three feasibility grades before any execution attempt:

**Grade A — Fully Executable.** All of the following conditions are satisfied:

1. Every computational step required by the task maps to at least one deployed, accessible tool in the SCP ecosystem.
2. The data flow between steps is compatible: each step's output format can serve as the next step's input, either directly or through a known format conversion tool.
3. At least one clear, quantitative success criterion exists or can be defined (e.g., docking score threshold, property improvement target, structural quality metric).
4. The expected computational time is within the session's resource limits.

**Grade B — Partially Executable.** At least one of the following applies:

1. One or more auxiliary steps lack a dedicated tool, but the agent can implement an approximate computational substitute (e.g., RDKit-based property estimation in place of unavailable specialized software). Each approximation MUST be explicitly documented.
2. The quality of the final result cannot be fully validated computationally — partial validation is possible, but some aspects require experimental confirmation.
3. A non-standard data format conversion is required between tools, necessitating agent-authored conversion code whose correctness cannot be formally guaranteed.

For Grade B tasks, the agent MUST:
- Declare the specific gaps before execution begins.
- Label all outputs from approximate steps with: `[APPROXIMATE — see limitations]`.
- Include a "Capability Gap Analysis" section in the final report listing each gap, the workaround used, and the impact on result reliability.

**Grade C — Beyond Current Capability.** At least one of the following applies:

1. A core computational step has no corresponding tool and no reasonable approximation (e.g., the task requires quantum mechanical calculations, but no QM tool is deployed).
2. The task requires experimental data that the agent cannot generate computationally (e.g., "determine the experimental IC₅₀" without any cell-based assay tool).
3. The task requires a model type not available in the toolkit (e.g., free energy perturbation for relative binding affinity when only MM-PBSA is available, and the distinction is material to the task's question).

For Grade C tasks, the agent MUST:
- **REFUSE execution** of the infeasible portion. Do not produce approximate results for tasks where the approximation gap would render conclusions scientifically meaningless.
- Report clearly: "This task requires [specific capability] which is not available in the current toolkit. The closest available method is [X], but it cannot address [specific aspect] because [reason]."
- If parts of the task are Grade A or B, execute those parts and report them as partial results.
- Suggest what tool or capability would need to be added to make the task feasible.

### 23.3 Problem Discovery Protocol

When the agent is asked to identify scientific problems solvable with its toolkit (rather than being given a specific task), it should follow this structured discovery protocol:

**(a) Enumerate unexploited tool combinations.** Survey the capability inventory (Section 23.1) and identify tool composition paths that are not covered by any existing L2 workflow. Focus on compositions where the output of one capability domain serves as a natural input to another.

**(b) Map compositions to scientific questions.** For each novel composition path, formulate the scientific question it could address. The question must be specific and falsifiable, not vague. CORRECT: "Can coarse-grained conformational sampling followed by transient pocket detection identify cryptic allosteric sites in kinases?" INCORRECT: "Can we do something interesting with dynamics simulations?"

**(c) Assess feasibility.** Apply the Grade A/B/C classification from Section 23.2 to each candidate problem.

**(d) Prioritize by scientific value and feasibility.** Rank candidate problems by two axes: scientific significance and computational feasibility (Grade A > Grade B; Grade C is excluded). Present the top-ranked problems to the user with their feasibility grades and any known limitations.

**Scientific value assessment heuristics.** The agent should apply the following criteria, in descending order of priority, to evaluate scientific significance:

1. **Addresses an acknowledged limitation of current methodology.** Does the candidate workflow address a gap explicitly discussed in the L3 Chapter 6 strategic guidance or in the limitations sections of existing L2 workflows? For example: the absence of an "unmonitored endpoint alarm" in multi-objective optimization (L2-05 Scene C) is a known gap — a workflow that fills it has high scientific value.
2. **Produces experimentally actionable output.** Would the computational result directly inform a specific experimental decision (e.g., which compound to synthesize, which mutation to introduce, which pocket to target)? Workflows whose outputs merely confirm what is already computationally accessible have lower value.
3. **Exploits complementary tool strengths.** Does the candidate combination pair tools with complementary strengths in a way that compensates for individual tool weaknesses? For example: combining docking (fast, approximate) with MM-PBSA (slower, more rigorous) in a two-tier evaluation is more valuable than simply running either tool alone on a larger scale.
4. **Enables iterative refinement where only single-pass existed.** Does the candidate workflow introduce a feedback loop where currently only a linear pipeline exists? Iterative workflows generally produce better outcomes than single-pass pipelines for optimization tasks (L3 Principle 4).

**Cross-reference:** The scientific value assessment should draw on domain knowledge encoded in Chapter 6 (Strategic Guidance for Major Task Types) of the parent L3 document, and the agent should specifically flag any novel combination that could address a known limitation discussed therein.

---

## Principle 24: Autonomous Workflow Authoring

When the agent encounters a Grade A or Grade B task with no matching L2 workflow, it may author a temporary workflow document (a "draft workflow") to guide its own execution. This principle establishes the mandatory standards for draft workflow quality.

### 24.1 Structural Requirements

A draft workflow MUST conform to the same structural template as expert-curated L2 workflows. Specifically, it must include all of the following sections:

1. **YAML metadata header** — including:
   - `name`: descriptive kebab-case identifier prefixed with `draft-`
   - `description`: one-paragraph summary of the workflow's purpose
   - `metadata.skill-level`: `L2-Workflow-DRAFT`
   - `metadata.source-task`: description of the task that prompted the workflow's creation
   - `metadata.feasibility-grade`: A or B (from Principle 23)
   - `metadata.methodology-ref`: list of parent L3 principles referenced
   - `metadata.confidence`: `UNTESTED` (initial), `LOW` (1 successful execution), `MEDIUM` (2–3 executions), `HIGH` (≥4 executions with consistent success)

2. **Applicability section** — "Use when" and "Do NOT use when" conditions, derived from the specific task's characteristics generalized to the task class.

3. **Prerequisites table** — listing all required inputs, their sources, and whether each is mandatory.

4. **Phase-by-phase execution protocol** — with:
   - Numbered phases with clear objectives
   - Specific tool invocations using correct SCP tool names (snake_case, never skill names)
   - Embedded quality-gate checkpoints after each phase (Principle 12, Checkpoint A format)
   - COUNT GATE blocks at every stage where molecule/structure counts change
   - MAPPING GATE blocks before any residue-specific analysis (if applicable)

5. **Failure-and-recovery table** — anticipating at least three common failure modes with specific recovery actions. The agent should draw on its knowledge of tool-specific failure patterns from existing L1 skill documents to populate this table.

6. **Output specification (data handoff contract)** — declaring each output artifact's format, downstream consumers, and download policy (Category A/B/C per Principle 16).

### 24.2 Mandatory Cross-References to Parent L3

Every draft workflow must explicitly reference the following parent L3 principles at the appropriate execution points:

| Execution Point | Required Reference |
|----------------|-------------------|
| Before first tool call | Principle 1 (plan complete?) |
| At every molecule/structure count change | Principle 11 (COUNT GATE) |
| At every evaluation step | Principle 9 (plausibility check), Principle 10 (three-category labeling) |
| Before residue-specific interpretation | Principle 17 (MAPPING GATE) |
| At every docking setup | Principle 18 (box ≥ 25 Å, progressive enlargement) |
| Before any report text | Principle 13 (computation-first hierarchy) |
| At iterative decision points | Principles 4–8 (iteration methodology) |
| Before final report | Principle 12 Checkpoint C (pre-report audit) |

### 24.3 Draft Workflow Marking and Limitation Declaration

All outputs produced under a draft workflow MUST carry the following annotations:

- **In `run_log.md`:** A header block at the top: `## ⚠️ DRAFT WORKFLOW EXECUTION — This task was executed using an agent-authored draft workflow, not an expert-curated L2 skill. Results should be interpreted with additional caution.`
- **In `result.md`:** A "Methodology Note" section explicitly stating: (a) that a draft workflow was used, (b) the workflow's feasibility grade, (c) any identified capability gaps, and (d) a confidence assessment for each major result.
- **In any generated skill document:** The `[DRAFT-WORKFLOW]` tag in the YAML header.

### 24.4 Restrictions on Draft Workflow Scope

Draft workflows are subject to the following scope limitations:

- **Maximum tool chain length:** A draft workflow may compose up to 25 distinct tool invocations in sequence. Longer chains require decomposition into sub-workflows, each reviewed independently.
- **No novel tool parameter ranges:** Draft workflows must use tool parameters within the ranges documented in existing L1 skill files. If a task requires parameters outside documented ranges, the agent must flag this as a Grade B limitation.
- **No recursive self-invocation:** A draft workflow may not call itself or define self-referential loops beyond the standard iteration protocol (Principles 4–8).
- **Single-session scope:** A draft workflow is valid only for the current execution session unless it is crystallized into a persistent skill (Principle 25).

---

## Principle 25: Experiential Crystallization and Skill Self-Generation

When the agent successfully completes a novel or unusually challenging task, the execution trace may contain reusable knowledge — tool composition patterns, failure-recovery strategies, parameter selection heuristics, or domain-specific decision logic — that would benefit future tasks of the same class. This principle defines when and how such knowledge should be extracted, abstracted, and persisted as a new skill document.

### 25.1 Crystallization Triggers

Skill crystallization is a post-execution process that is TRIGGERED when any of the following conditions is detected during the mandatory post-execution self-assessment:

**Trigger T1 — Novel workflow success.** The agent successfully completed a task using a draft workflow (Principle 24) that involved a tool composition pattern not documented in any existing L2 skill, AND the task achieved its quantitative success criteria.

**Trigger T2 — Novel failure-recovery pattern.** During execution of an existing L2 workflow, the agent encountered and resolved ≥ 2 consecutive tool failures using a recovery strategy not documented in that workflow's failure-and-recovery table. The recovery must have been verified as successful (i.e., the pipeline continued to completion after recovery).

**Trigger T3 — Recurring sub-workflow pattern.** The agent identifies that it has independently composed the same sub-sequence of tool calls (≥ 3 tools in the same order with similar parameters) in ≥ 2 different tasks within the same session or across referenced prior sessions.

**Trigger T4 — Quantitatively validated improvement.** The agent achieved a significantly better result by deviating from the standard L2 workflow protocol, AND the improvement is quantitatively verified (e.g., ≥ 20% improvement on the primary metric, or success where the standard protocol failed). The deviation must be deliberate and documented, not accidental.

**Trigger T5 — Systematic failure pattern.** During execution, the agent encountered a tool or tool combination that fails SYSTEMATICALLY under specific, reproducible input conditions (not due to parameter misconfiguration or transient server errors), AND this failure pattern is not documented in any existing L1 or L2 skill's failure-and-recovery table.

T5 crystallization differs from T1–T4 in its output type:
- T5 does NOT produce a new workflow. Instead, it produces a **Failure Pattern Memo** — a structured document that is either: (a) appended to the relevant L1 skill's failure-and-recovery table as a new entry, or (b) saved as a standalone L1 skill documenting tool usage restrictions under the specific failure conditions.
- The memo format includes: tool SCP name, failure condition (input characteristics that trigger the failure), failure signature (error message or output pattern), root cause analysis, recommended avoidance strategy, and alternative tools or approaches.
- T5 crystallization follows a simplified version of the five-step process (Section 25.2): only Steps 1, 4, and 5 are executed (trace extraction, failure documentation, and template formatting). Steps 2–3 (pattern abstraction and validation logic) are omitted because the output is a failure record, not a workflow template.

Examples of T5 triggers observed in MolClaw benchmarking:
- REINVENT4 mol2mol produces zero valid molecules when the seed molecule's Tanimoto similarity to the generative model's training distribution falls below approximately 0.3
- ProLIF crashes with valence or indexing errors when analyzing PDBQT-derived structures that contain non-standard atom typing
- OpenAWSEM produces physically implausible collapsed structures for proteins with more than three disulfide bonds

### 25.2 Crystallization Process — Five Steps

When a trigger fires, the agent executes the following five-step crystallization process. This process is performed AFTER the primary task is complete and reported, never during task execution.

**Step 1: Trace Extraction.** From the execution log (`run_log.md`), extract the following elements:

- The complete sequence of SCP tool calls, in order, with their parameters and return values
- Every decision point where the agent chose between alternatives, with the choice made and the rationale
- Every failure event, its diagnosis, and the recovery action taken
- Every quality-gate checkpoint result (pass/fail/conditional)
- The quantitative metrics at each stage (counts, scores, property values)

Record these elements in a structured "Execution Trace Summary" — a condensed version of the run log organized by pipeline phase rather than by chronological order.

**Step 2: Pattern Abstraction.** Transform the task-specific trace into a generalizable template:

- **Variable abstraction:** Replace all task-specific identifiers with generic placeholders:
  - Protein names → `$TARGET_PROTEIN`
  - PDB IDs → `$PDB_ID`
  - Molecule SMILES → `$SEED_MOLECULE` or `$CANDIDATE_MOLECULE`
  - Residue numbers → `$RESIDUE_ID (reference scheme: $SCHEME)`
  - File paths → `$STEP_NN_OUTPUT_FILE`
  - Threshold values → `$THRESHOLD_[METRIC_NAME]` with the specific value used noted as "default"

- **Conditional logic extraction:** Identify if–then–else decision patterns in the trace and formalize them as decision trees or conditional blocks:
  ```
  IF [condition derived from tool output]:
      → Execute [action A] with [parameters]
  ELIF [alternative condition]:
      → Execute [action B]
  ELSE:
      → [fallback action]
  ```

- **Invariant identification:** Determine which aspects of the execution were essential to success (must-preserve) versus incidental (may-vary). Essential aspects become mandatory steps in the skill; incidental aspects become documented options.

**Step 3: Validation Logic Extraction.** From the trace's checkpoint results, extract the verification criteria that were effective:

- Which Checkpoint A conditions caught real errors? → Include these as mandatory quality gates
- Which parameter ranges led to successful tool execution? → Document as recommended ranges
- Which COUNT GATE verifications revealed discrepancies? → Include the specific verification commands
- Which MAPPING GATE steps were necessary? → Include with the specific mapping scenarios

**Step 4: Failure Pattern Documentation.** For each failure-recovery pair in the trace:

- Formalize the failure signature (error message pattern, output characteristics that indicate failure)
- Document the diagnostic reasoning that identified the cause
- Specify the recovery action with exact tool calls and parameter adjustments
- Note the recovery success rate (succeeded on first attempt vs. required multiple attempts)

**Step 5: Template Formatting.** Assemble the abstracted patterns into a skill document following the appropriate level's format standard. Invoke the L1 skill `molclaw-skill-template-writer` (if available) or manually construct the document following the format specifications in Section 25.3.

### 25.3 Level Determination for Self-Generated Skills

The crystallized knowledge is assigned to the appropriate hierarchical level based on its scope:

**Generate as L1 tool skill when:**
- The knowledge pertains to a SINGLE tool's novel usage pattern, parameter configuration, or failure mode
- Examples: "REINVENT4 mol2mol sampling produces zero output when seed Tanimoto to training distribution < 0.3 — switch to manual analog design"; "Boltz-2 affinity prediction requires chain renaming when input PDB has non-standard chain IDs"
- Format: follow existing L1 SKILL.md template (YAML header + step-by-step usage with code examples)

**Generate as L2 workflow skill when:**
- The knowledge composes MULTIPLE tools into a new validated pipeline with defined data flow, quality gates, and failure recovery
- Examples: "Cryptic pocket discovery via conformational ensemble screening — combining OpenAWSEM → PULCHRA → fpocket (per-conformation) → spatial clustering → focused docking"; "Multi-objective constrained optimization with ADMET deterioration alarm"
- Format: follow existing L2 workflow template (YAML header + applicability + prerequisites + phases + checkpoints + failure table + output specification)

**L3 principles are NEVER self-generated.** Strategic governance principles require expert human validation and scientific community consensus. The agent may PROPOSE candidate L3 amendments in a "Suggested Methodology Updates" section of the crystallized skill, but these proposals have no binding force until reviewed and approved by human experts.

### 25.4 Quality Requirements for Self-Generated Skills

Every self-generated skill document MUST include:

**(a) Provenance metadata** in the YAML header:
```yaml
metadata:
    skill-level: L1-Tool-AUTO or L2-Workflow-AUTO
    auto-generated: true
    source-task: "[one-sentence description of the originating task]"
    source-execution-date: "[date]"
    source-platform: "[Claude Code / OpenClaw]"
    crystallization-trigger: "[T1 / T2 / T3 / T4]"
    confidence: "[UNTESTED / LOW / MEDIUM / HIGH]"
    validation-record: "[list of task IDs where this skill was successfully applied]"
```

**(b) Originating execution trace reference** — a pointer to the `run_log.md` from which the skill was derived, with the specific phase/step numbers that informed each section of the skill.

**(c) Applicability conditions** — both positive ("Use when...") and negative ("Do NOT use when..."), derived from the originating task's characteristics and generalized to the task class.

**(d) At least one successful execution record** — the originating task itself counts as the first record. Subsequent applications are appended to the `validation-record` field in the YAML header.

**(e) Known limitations and boundary conditions** — explicitly stating:
- Under what conditions the skill is expected to fail or produce unreliable results
- Which aspects of the originating task were NOT generalized (and why)
- Which tool versions were used (in case of version-dependent behavior)

**(f) Confidence rating** with clear upgrade criteria:
- `UNTESTED`: just generated, no application yet (initial state)
- `LOW`: applied in 1 task (the originating task)
- `MEDIUM`: applied in 2–3 distinct tasks with consistent success
- `HIGH`: applied in ≥ 4 distinct tasks with consistent success and no significant failures

### 25.5 Mandatory Post-Execution Self-Assessment

**This self-assessment is MANDATORY after every task completion, regardless of whether the task used an existing L2 workflow or a draft workflow.** It is performed after Checkpoint C (Principle 12) and before the final report is written.

The agent must explicitly answer three questions:

**Q1: "Did I use a novel tool combination or workflow not documented in any existing L2 skill?"**
- If the answer is YES and the task succeeded → Trigger T1 is active.
- Verification: compare the tool call sequence in `run_log.md` against all loaded L2 workflow phase specifications.

**Q2: "Did I encounter and resolve a failure pattern not listed in any existing skill's failure-and-recovery table?"**
- If the answer is YES and the recovery was verified successful → Trigger T2 is active.
- Verification: compare each failure-recovery pair in `run_log.md` against the failure tables of all loaded L1 and L2 skills.

**Q3: "Did I discover a strategy, parameter choice, or workflow deviation that produced quantitatively better results than the standard approach?"**
- If the answer is YES with quantitative evidence → Trigger T4 is active.
- Verification: compare the achieved metric against the standard approach's expected range (from existing skill documentation or baseline measurements).

**Q4: "Did I encounter a tool failure caused by specific, reproducible input conditions that is not documented in any existing skill?"**
- If the answer is YES → Trigger T5 is active.
- Verification: confirm the failure is reproducible (not a transient error) and check all relevant L1 skill failure tables for prior documentation.
- Note: T5 can be active even when the overall task FAILED, unlike T1–T4 which require task success.

**If ANY trigger is active:**
1. Execute the Skill Crystallization Meta-Workflow (L2 Workflow 12) after the primary task report is complete.
2. Append the generated skill document as a supplementary deliverable.
3. Record in `result.md`: `## New Skill Generated\n- Name: [skill-name]\n- Level: [L1/L2]\n- Trigger: [T1/T2/T3/T4/T5]\n- Confidence: [rating]\n- Summary: [one-sentence description]`

**If NO trigger is active:** Record in `run_log.md`: `## Post-Execution Self-Assessment: No crystallization trigger activated. Task executed within existing skill coverage.`

### 25.6 Skill Storage and Retrieval

Self-generated skills are stored in a designated directory (`auto-generated-skills/`) separate from expert-curated skills. The directory structure mirrors the main skill hierarchy:

```
auto-generated-skills/
├── L1_tools/
│   └── [auto-generated L1 skills]
├── L2_workflows/
│   └── [auto-generated L2 workflows]
└── skill-index.md       ← auto-maintained index of all generated skills
```

The `skill-index.md` file is updated after each crystallization event, containing:

| # | Skill Name | Level | Trigger | Confidence | Date | Tools Involved | Source Task Summary |
|---|-----------|-------|---------|------------|------|---------------|-------------------|

The `Tools Involved` column lists the SCP tool names (snake_case, comma-separated) that the skill pertains to. This field enables rapid filtering when the agent needs to look up skills related to a specific tool during execution.

**Retrieval protocol:** During Phase 0 (pre-execution planning) of any task, the agent should check `skill-index.md` for auto-generated skills whose applicability conditions match the current task. If a matching auto-generated skill exists:
- If confidence is MEDIUM or HIGH: load and use it alongside expert-curated skills, with a note in `run_log.md` that an auto-generated skill was applied.
- If confidence is LOW: load it as a reference but do not rely on it exclusively; cross-validate against first-principles reasoning and existing L2 workflows.
- If confidence is UNTESTED: do not use; note its existence as a potential resource for future investigation.

### 25.6a Failure-Triggered Skill Retrieval

**Platform requirement for cross-session learning:** Auto-generated skills require persistent storage across sessions. On platforms with ephemeral workspaces (e.g., container-based deployments without volume mounts), the `auto-generated-skills/` directory must be mapped to a persistent volume. Without persistence, the experiential learning loop cannot close across sessions — crystallization will still occur within a session, but the knowledge will be lost at session end. This is a deployment constraint, not a skill-layer constraint; the skill architecture is designed to function correctly whenever persistence is available.

In addition to the Phase 0 proactive retrieval described above, the agent MUST check `auto-generated-skills/skill-index.md` **reactively** whenever a tool failure occurs during execution. This ensures that previously crystallized failure-recovery knowledge is consulted before the agent attempts to devise recovery strategies from scratch.

**Reactive retrieval protocol:**

**(a) On any SCP tool call that returns an error or unexpected output:** Before attempting recovery, search the `Tools Involved` column of `skill-index.md` for entries containing the failing tool's SCP name. If a matching entry exists with confidence ≥ LOW, load the skill and check whether its failure-recovery table covers the observed failure pattern. If it does, apply the documented recovery strategy. If it does not, proceed with agent-designed recovery and note that the auto-generated skill was consulted but did not cover this specific failure mode.

**(b) On REINVENT4 producing zero valid molecules:** This is a high-frequency failure mode documented in MolClaw benchmarking. Before switching to alternative generation strategies, check for any auto-generated L1 skill whose `Tools Involved` includes `reinvent_mol2mol_sampling` or related REINVENT tool names.

**(c) On ProLIF or PLIP failing with valence, indexing, or parsing errors:** Use `molclaw-interaction-visualizer` (local script) as the primary alternative — it handles PDBQT/SDF/MOL2 input natively and does not depend on SCP. Also check for auto-generated skills documenting additional workarounds or PDBQT-specific preprocessing steps.

**(d) On any docking tool returning all-positive or all-identical scores:** Check for auto-generated skills documenting receptor preparation issues or docking box configuration patterns for specific protein families.

**Logging:** Every reactive retrieval check must be recorded in `run_log.md`, regardless of whether a matching skill was found: `[REACTIVE RETRIEVAL] Tool failure: [tool_name]. Checked skill-index: [match found / no match]. Action: [applied skill X / proceeded with novel recovery].`

### 25.7 Skill Revision Protocol

When an auto-generated skill is applied to a new task and requires adjustment — but the core tool composition remains valid — the skill should be REVISED rather than replaced. This protocol governs how revisions are made while maintaining the skill's provenance chain.

**Revision trigger conditions.** A revision is warranted when the skill was loaded and consulted, but one or more of the following occurred:

- A parameter default needed to be changed for the new task context (e.g., a distance threshold that worked for kinases but not for GPCRs)
- A new failure mode was encountered that is not in the skill's failure-recovery table
- A decision branch was missing — a new input condition not covered by the existing conditional logic
- A quality gate condition proved too strict (blocking valid results) or too lenient (passing invalid results)

**Revision process:**

1. **Complete the current task first.** Never interrupt a task execution to revise a skill. The revision is a post-execution activity.
2. **Document each adjustment** made during execution:
   - What was changed from the skill's documented recommendation
   - Why the change was necessary (what characteristic of the new task or target required it)
   - The outcome of the change (did it lead to successful completion?)
3. **Update the skill document** with the following types of changes:
   - **Widen parameter ranges:** If a new valid parameter value was discovered outside the documented range, expand the range in the Parameters table and note the new boundary case.
   - **Add conditional branches:** If a new input condition required different handling, add a new branch to the relevant decision logic block.
   - **Add failure-recovery entries:** If a new failure mode was encountered and resolved, add it to the failure-recovery table.
   - **Update Known Limitations:** Add any newly discovered boundary conditions.
   - **Do NOT change the core tool composition or phase structure.** If the core pipeline needs to change, create a new skill instead of revising.
4. **Append to revision history** in the YAML metadata:
   ```yaml
   revision-history:
     - date: "[date]"
       task: "[one-sentence summary of the task that prompted revision]"
       changes: "[list of specific changes: widened param X, added branch Y, ...]"
       outcome: "[success / partial — brief note]"
   ```
5. **Reset confidence to LOW.** A revised skill is effectively a new version whose reliability must be re-established. The previous version's `validation-record` entries carry forward but are annotated as `(pre-revision)`.
6. **Update `skill-index.md`** with the revision date and new confidence level.

**Distinction between revision and new skill creation:**
- If the core tool composition (the ordered sequence of SCP tools) remains the same → REVISE the existing skill.
- If the core tool composition changes (tools added, removed, or reordered) → CREATE a new skill. The old skill remains in the index for reference, with a note: `Superseded by [new-skill-name]`.

---

## Principle 26: Capability Boundary Self-Awareness and Dynamic Update

The agent must maintain an honest, up-to-date understanding of the boundaries of its computational capabilities. This principle extends Principle 20 (Honest Annotation of Uncertainty) from result-level uncertainty to system-level capability awareness.

### 26.1 Capability Boundary Documentation

The agent should maintain a mental model (and, when executing multi-task sessions, a written document) of its capability boundaries organized along three dimensions:

**Dimension 1 — Tool-level boundaries.** For each tool in the ecosystem:
- Known failure modes (from L1 skill documentation and from direct experience)
- Input constraints (maximum molecule size, sequence length limits, format requirements)
- Output reliability (deterministic vs. probabilistic; confidence-scored vs. unscored)
- Computational cost (seconds/minutes/hours per invocation)

**Dimension 2 — Workflow-level boundaries.** For each L2 workflow and draft workflow:
- Task types it handles well vs. poorly
- Known edge cases where the workflow produces unreliable results
- Assumption violations that invalidate the workflow (e.g., using a small-molecule docking workflow for a peptide ligand exceeding 50 atoms)

**Dimension 3 — Methodological boundaries.** System-wide limitations that no tool or workflow can overcome:
- Docking scores are ranking tools, not thermodynamic quantities (Principle 9)
- Computational predictions require experimental validation
- ADMET predictions are statistical, not deterministic
- Conformational sampling is incomplete — important states may be missed
- LLM chemical reasoning is not guaranteed to be correct

<!-- NEW: Dimension 4 -->
**Dimension 4 — Information retrieval boundaries (if LR tools are available).** Limitations of external knowledge retrieval that the agent must communicate when using LR tools:
- **Searchable databases:** PubMed (indexed biomedical literature), Wikipedia (encyclopedic), general web (via multi-search-engine), full-text articles (via agent-browser for open-access or URL-accessible content).
- **NOT searchable:** Paywalled full-text without accessible URL, non-indexed preprints (not yet in PubMed), proprietary databases (SciFinder, Reaxys, CAS), internal company data.
- **Temporal coverage:** PubMed has an indexing delay (days to weeks); most recent publications may not yet be retrievable. Web search coverage depends on search engine indexing.
- **Language coverage:** Primarily English-language literature; Chinese-language coverage via multi-search-engine (Baidu, Sogou) but with lower structured data quality for scientific content.
- **Retrieval ≠ comprehensiveness:** A negative search result does NOT mean the literature is silent — it may mean the query missed relevant terms, or the content is behind a paywall. Always qualify: "No results found in PubMed search" rather than "No prior work exists."

**Methodological precision reference table.** The following table maps common computational needs to the available methods, their precision levels, and their applicability scope. The agent should consult this table when performing feasibility assessment (Principle 23) and when communicating result confidence to the user (Principle 26.3).

| Computational Need | Available Method | Precision | Applicable Scope | Known Limitation |
|-------------------|-----------------|-----------|------------------|-----------------|
| Binding affinity ranking (same target) | Docking score (QuickVina) | Low | Coarse ranking of ≥10 molecules | Cannot predict absolute ΔG; fails for covalent binders |
| Binding affinity ranking (refined) | EquiScore rescoring | Low–Medium | Re-ranking top docking hits | Requires docked poses as input |
| Binding affinity prediction | Boltz-2 | Medium | Fast affinity estimate from sequence + SMILES | Performance on novel target families unknown |
| Binding free energy estimation | MM-PBSA (gmx_MMPBSA) | Medium | Relative comparison within same target | Requires ≥10 ns MD trajectory; entropy underestimated |
| Binding free energy (high precision) | FEP | **NOT AVAILABLE** | — | Would require deployment of FEP software |
| Interaction identification (batch/trajectory) | ProLIF, PLIP | Medium–High | Batch docking fingerprint comparison, MD trajectory interaction dynamics, protein-protein trajectory profiling | ProLIF fails on non-standard atom types; distance-based, not energy-based; requires SCP server |
| Interaction identification + visualization (local, **primary**) | interaction-visualizer | Medium–High | 9 interaction types with geometric criteria; Schrödinger-style 2D diagram; PyMOL 3D rendering; residue role annotation; decision JSON (top_residues, hot_partner_sites). **Default tool for all single-structure interaction analysis.** | Geometry-based, not energy-based; no MD trajectory support; no batch docking comparison; strength hints are qualitative, NOT quantitative energies; requires rdkit for 2D diagram, pymol for 3D |
| Conformational sampling | OpenAWSEM, GoCa, OpenMM | Medium | Identify flexible regions, transient states | Sampling is incomplete; rare events may be missed |
| Drug-likeness assessment | RDKit QED, Lipinski | High (deterministic) | Rule-based filtering | Rules are guidelines, not guarantees of drugability |
| ADMET prediction | ADMET-AI | Low–Medium (statistical) | Early-stage triage of compound libraries | Probabilistic; confidence varies by endpoint |
| Protein structure prediction | ESMFold, Chai-1 | Variable (pLDDT-dependent) | Targets without experimental structure | Degrades for sequences >800 residues (ESMFold); loops and disordered regions unreliable |
| Selectivity assessment | Cross-target docking comparison | Low | Qualitative selectivity direction | Cannot provide quantitative selectivity ratios or fold-change |

### 26.2 Dynamic Boundary Update

When the agent encounters a new capability boundary during execution — a tool failure that reveals an undocumented limitation, or a task that exposes an assumption violation — it MUST:

1. **Record the boundary immediately** in `run_log.md` with:
   - The specific tool or workflow involved
   - The input conditions that triggered the boundary
   - The failure mode or limitation observed
   - Whether a workaround was found (and if so, what)

2. **Propagate the boundary to relevant contexts:**
   - If the boundary affects an existing L1 skill's failure table → note as a "Suggested Update" in the post-execution self-assessment
   - If the boundary affects an existing L2 workflow's applicability → note as a "Suggested Scope Restriction"
   - If the boundary represents a novel system-wide limitation → note in the "Limitations" section of the final report

3. **If the boundary was encountered in a self-generated skill's scope:** Update the skill's "Known Limitations" section with the new boundary condition, and downgrade the skill's confidence rating by one level if the boundary was not previously anticipated.

### 26.3 Honest Communication of Boundaries

When communicating results to the user, the agent MUST:

- **Never overstate computational evidence.** Do not present docking-only results as evidence of binding affinity. Do not present ADMET predictions as safety guarantees. Do not present single-method results as consensus findings.
- **Explicitly distinguish between high-confidence and low-confidence conclusions.** Example: "The docking score improvement (−8.9 vs. −6.9 kcal/mol) is consistent across all docked poses [high confidence], but the predicted binding affinity improvement requires experimental confirmation [low confidence]."
- **Flag capability boundaries proactively.** If the agent suspects the user's expectations exceed its computational capabilities, raise this concern before execution rather than producing results that might be over-interpreted. Example: "This task requests selectivity prediction between EGFR and HER2. My toolkit can perform cross-target docking to identify differential interactions, but cannot provide quantitative selectivity ratios — those require experimental determination or free energy perturbation calculations, which are not currently available."

### 26.4 Boundary-Aware Problem Recommendation

When recommending scientific problems to the user (per Principle 23, Section 23.3), the agent must explicitly state the capability boundary for each recommendation:

- What the agent CAN compute: the specific tools, methods, and outputs
- What the agent CANNOT compute: the limitations and gaps
- What would need experimental validation: the computational-to-experimental handoff points
- What confidence level to expect: qualitative assessment of result reliability for this problem type

---

## Quick Reference: Chapter 8 Principle Index

| # | Name | Core Purpose | Operational Workflow | Key Cross-References |
|---|------|-------------|---------------------|---------------------|
| 23 | Capability Landscape Mapping and Problem Feasibility Assessment | Data flow connectivity map; A/B/C feasibility grading; scientific value heuristics; problem discovery protocol | **L2-00** (`00-problem-discovery-and-feasibility-triage.md`) — operationalizes 23.1, 23.1a, 23.2, 23.3 as a step-by-step meta-workflow invoked for open-ended Type B tasks | P1 (plan before act), P3 (multi-method), P20 (uncertainty) |
| 24 | Autonomous Workflow Authoring | Standards for draft workflows; structural requirements matching expert L2; paradigm selection; scope limits | **L2-13** (`13-draft-workflow-authoring.md`) — operationalizes 24.1–24.4 as a step-by-step meta-workflow invoked for Type C tasks (concrete but no existing L2 coverage) | P1–P8 (planning, iteration), P9–P13 (data integrity), P17–P18 (structural biology) |
| 25 | Experiential Crystallization and Skill Self-Generation | When to crystallize (T1–T5); five-step process; level determination; quality requirements; mandatory post-execution self-assessment; failure-triggered retrieval; skill revision protocol | **L2-12** (`12-skill-crystallization.md`) — operationalizes 25.1–25.7 as a step-by-step meta-workflow invoked when Phase 2.5 self-assessment detects an active trigger | P8 (iteration records), P11 (count-before-report), P12 (checkpoints), P22 (file inventory) |
| 26 | Capability Boundary Self-Awareness | Four dimensions of boundaries (tool, workflow, methodological, information retrieval); methodological precision table; dynamic update protocol; honest communication | No dedicated L2 (continuous cross-cutting principle; invoked within L2-00 Phase 6, L2-13 Phase 5.2, and every result-reporting step per P20) | P9 (plausibility), P13 (computation-first), P20 (honest uncertainty) |

---

## Integration Note

This supplement adds 4 principles (23–26) to the existing 22, bringing the total L3 principle count to 26 across 8 chapters. Each of Principles 23, 24, and 25 has a corresponding L2 meta-workflow operationalizing it as a reproducible step-by-step procedure (L2-00, L2-13, L2-12 respectively); Principle 26 is a continuous cross-cutting principle invoked at boundary-declaration points within those three workflows. The Quick Reference table in the parent document should be extended accordingly. No existing principles are modified; all additions are purely additive.

The full autonomous discovery pipeline, from open-ended request through persistent skill generation, is:

```
[Type B task: open-ended problem discovery]
       ↓
   L2-00 (Principle 23)  →  ranked candidate problems with boundary declarations
       ↓  [user selects a candidate]
[Type C task: concrete task with no existing L2]
       ↓
   L2-13 (Principle 24)  →  compliant draft workflow document (DRAFT-marked)
       ↓  [draft executed per its own phase protocol, governed by L3 Ch. 1–7]
   Ordinary execution  →  result.md + run_log.md
       ↓  [Phase 2.5 mandatory self-assessment]
   L2-12 (Principle 25)  if trigger T1/T2/T4/T5 fires
       ↓
   Persistent auto-generated skill in `auto-generated-skills/`
```

Principle 26 is applied at every "→" in this pipeline: when producing candidate problems (boundary declarations per 26.4), when authoring draft workflows (scope restrictions per 24.4 which derive from 26.1), when reporting results (honest communication per 26.3), and when updating skill confidence (dynamic boundary update per 26.2).

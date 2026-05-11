---
name: molclaw-skill-crystallization
description: >
  Meta-workflow for extracting reusable skill documents from successful execution traces.
  Invoked when crystallization triggers (L3 Chapter 8, Principle 25, T1–T4) are detected
  during the mandatory post-execution self-assessment. This workflow operates AFTER the
  primary task is complete and reported, transforming execution experience into persistent,
  composable skill knowledge. Output: a formatted L1 or L2 skill document stored in the
  auto-generated-skills directory.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 1.0
    methodology-ref: >
      L3 Chapter 8 Supplement in its entirety (Principles 23–26),
      L3 Principle 8 (Complete Iteration Records — source material for crystallization),
      L3 Principle 10 (Three-Category Distinction — maintain provenance in generated skills),
      L3 Principle 11 (Count-Before-Report — verify all statistics in generated skills),
      L3 Principle 12 (Three-Checkpoint Self-Audit — transfer checkpoint logic to generated skills),
      L3 Principle 22 (File Inventory — trace provenance chain for generated skills)
---

# Skill Crystallization Meta-Workflow

## Applicability

**Use this workflow when:** A crystallization trigger (T1, T2, T3, T4, or T5 — defined in L3 Principle 25.1) has been activated during the post-execution self-assessment of a completed task. The primary task's report (`result.md`) and execution log (`run_log.md`) must already be finalized before this workflow begins. For T5 (systematic failure pattern), the primary task may have failed — T5 is the only trigger that does not require task success.

**Do NOT use this workflow when:**
- The primary task has not yet been completed — crystallization is always a post-execution activity, never a mid-execution interruption.
- The primary task failed to achieve its success criteria — failed workflows should not be crystallized into skills (though failure patterns should be documented in existing skills' failure-recovery tables via the T2 mechanism, which applies only when the recovery succeeded).
- The agent is uncertain whether a trigger has fired — refer to the three-question self-assessment protocol in Principle 25.5 to resolve ambiguity before invoking this workflow.
- The execution trace reveals only trivial variations of an existing workflow (e.g., using the same L2 workflow with different input parameters). Such cases represent normal skill usage, not novel knowledge.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Completed `run_log.md` | Primary task execution | Yes |
| Completed `result.md` | Primary task execution | Yes |
| Activated trigger ID (T1/T2/T3/T4) | Post-execution self-assessment | Yes |
| Tool call history with parameters and returns | Execution environment log | Yes |
| Existing L1/L2 skill documents (for novelty verification) | Skill library | Yes |
| All output files from the primary task | File inventory | Yes (for provenance) |

## Phase 0: Trigger Validation and Scope Determination

Before beginning the crystallization process, verify that the trigger is genuine and determine the scope of the skill to be generated.

### Phase 0 Fast Track (skip 0.1–0.4, proceed directly to Phase 1)

If ALL of the following are true, skip Phase 0.1–0.4 and proceed directly to Phase 1:
- The task was classified as Type C or Type A-Composite in Phase 0.0 triage
- The task achieved its quantitative success criteria
- The trigger being evaluated is T1 (novel workflow)

Rationale: Type C / A-Composite classification already confirmed that no single L2 covers the task at ≥ 70%. Re-verifying this at crystallization time is redundant. The scope determination (0.2–0.4) can be performed inline during Phase 1 without a separate phase. When using the fast track, record: `Phase 0 Fast Track: eligible (Type [C/A-Composite], task succeeded, T1 trigger). Proceeding to Phase 1.`

For all other cases (T2, T4, T5 triggers, or when the fast track conditions are not met), execute Phase 0.1–0.4 in full.

### 0.1 Trigger Verification

Re-examine the trigger condition with deliberate skepticism:

**For T1 (novel workflow success):**
- Verify that the tool composition sequence is genuinely novel — search all loaded L2 workflow documents for any sub-sequence matching ≥ 70% of the tools used, in the same order.
- Verify that the task achieved its quantitative success criteria — re-check the success metric from `result.md`.
- If the sequence matches an existing workflow with only minor parameter changes → trigger is INVALID. Do not proceed.

**For T2 (novel failure-recovery):**
- Verify that the recovery strategy is not already documented — check the failure-recovery tables of all L1 and L2 skills involved in the task.
- Verify that the recovery was successful — confirm the pipeline completed after the recovery.
- If the recovery was a generic retry (same tool, same parameters) → trigger is INVALID.

**For T3 (recurring sub-workflow):**
- Verify that the same tool sub-sequence appeared ≥ 2 times — check `run_log.md` for repeated patterns.
- Verify the repetitions were in different task contexts (not just loop iterations within the same task).
- If the pattern is a standard iteration loop already covered by L3 Principles 4–8 → trigger is INVALID.

**For T4 (quantitatively validated improvement):**
- Verify the improvement is quantitative and non-trivial — ≥ 20% on the primary metric, or success where standard approach failed.
- Verify the deviation was deliberate and documented, not accidental.
- Verify the improvement is reproducible in principle (not due to stochastic variation).

**For T5 (systematic failure pattern):**
- Verify the failure is systematic, not transient — it must be reproducible under the same input conditions, not a one-time server error or timeout.
- Verify the failure is not already documented — check the failure-recovery tables of all L1 skills for the involved tool.
- Verify the failure condition is characterizable — the agent can describe what input properties trigger the failure (e.g., "seed Tanimoto < 0.3" or "protein with > 3 disulfide bonds"), not just "it sometimes fails."
- If the failure was caused by incorrect parameter usage on the agent's part → trigger is INVALID (this is operator error, not a tool limitation).
- **T5-specific scope:** T5 crystallization follows a simplified path through this workflow — only Phases 1.3, 1.4 (failure-related extraction) and Phase 3 (document assembly as Failure Pattern Memo) are required. Phases 1.1–1.2 (full trace mining) and Phase 2 (pattern abstraction) may be skipped.

**CHECKPOINT: Trigger Validation**
- [ ] Trigger condition re-examined with skepticism
- [ ] Novelty confirmed (not a minor variant of existing skill)
- [ ] Task success confirmed (not required for T5)
- [ ] Decision recorded: PROCEED / ABORT with reason

If the trigger is invalid, record in `run_log.md`: `## Skill Crystallization: Trigger [TN] re-evaluated and found INVALID. Reason: [explanation]. No skill generated.` and stop.

### 0.2 Target Level Determination

Based on the scope of the novel knowledge, determine the target skill level:

| Novel Knowledge Scope | Target Level | Indicator |
|----------------------|-------------|-----------|
| Single tool: new usage pattern, parameter range, or failure mode | L1 | The novelty involves only one SCP tool name in the trace |
| Multi-tool pipeline: new tool composition with data flow | L2 | The novelty involves ≥ 2 SCP tools composed in sequence |
| Single tool + domain-specific decision logic | L1 (composite) | One tool but with conditional logic for parameter selection |
| Cross-workflow integration pattern | L2 | The novelty connects outputs of one existing L2 workflow to inputs of another |

Record the decision: `Target skill level: [L1/L2]. Rationale: [explanation based on indicator].`

### 0.3 Novelty Scope Boundary

Define precisely which portions of the execution trace contain novel knowledge and which are standard operations covered by existing skills:

- Mark each phase in the trace as NOVEL (to be crystallized) or STANDARD (reference existing skill).
- For STANDARD phases, the generated skill should reference the existing skill by name rather than duplicating its content.
- For NOVEL phases, all detail must be captured in the crystallization.

Record the scope: `Novel phases: [list]. Standard phases (reference only): [list].`

### 0.4 Workflow Paradigm Matching (L2 target only)

If the target level is L2, the agent must identify which structural paradigm the novel workflow follows by examining the execution trace. This determines which existing L2 workflow to use as a structural skeleton for Phase 3 (Document Assembly), ensuring the auto-generated skill inherits the proven organizational patterns of expert-curated workflows.

| Trace Characteristic | Paradigm | Reference L2 | Template Skeleton |
|---------------------|----------|-------------|-------------------|
| Linear data flow: tools execute in strict sequence, each tool's output feeds the next, no tool group is invoked more than once | **Pipeline (A)** | L2-01 (protein prep), L2-07 (conformational sampling), L2-08 (post-docking evaluation) | Sequential phases with strict dependencies; one CHECKPOINT per phase |
| Same tool group invoked ≥ 2 rounds: each round has seed/state update, strategy adaptation based on prior results, and convergence check | **Iterative Loop (B)** | L2-05 (iterative optimization), L2-10 (protein design validation) | Evaluate→Diagnose→Design→Verify cycle; seed update rule; global tracker; convergence criteria |
| Input-dependent routing: execution path branches based on task characteristics, input properties, or intermediate results | **Branching Decision (C)** | L2-02 (docking screening by library size), L2-04 (generative design by mode) | Decision tree entry point; scene/mode classification; scene-specific sub-protocols |

**Usage in Phase 3:** Copy the matched reference L2's section ordering, checkpoint placement pattern, iteration record format, and output specification structure. Replace the reference L2's tool-specific content with the novel workflow's abstracted content from Phase 2. Retain the reference L2's quality gate types (COUNT GATE placement, MAPPING GATE placement) at structurally equivalent positions.

**Mixed paradigm:** If the trace combines paradigms (e.g., a Pipeline phase followed by an Iterative Loop phase), select the dominant paradigm for overall structure and embed the secondary paradigm within a single phase. Example: a cryptic pocket discovery workflow is primarily Pipeline (A) for conformational sampling and pocket detection, but may embed a short Loop (B) for iterative focused docking on the best transient pocket. In such cases, use the Pipeline skeleton overall, with one phase internally structured as a loop referencing L2-05's cycle format.

Record the decision: `Paradigm: [A/B/C/mixed]. Reference L2: [number]. Rationale: [explanation].`

---

## Phase 1: Execution Trace Mining

Extract the raw material for crystallization from the execution log.

### 1.1 Tool Call Sequence Extraction

From `run_log.md`, extract a complete, ordered list of all SCP tool calls made during the primary task:

```
## Tool Call Sequence
| # | SCP Tool Name | Key Parameters | Return Status | Output Files | Phase |
|---|--------------|----------------|---------------|-------------|-------|
| 1 | [tool_name] | [param1=val1, ...] | [success/fail] | [file list] | [NOVEL/STD] |
| 2 | ... | ... | ... | ... | ... |
```

**COUNT GATE:** Verify the number of tool calls in this table matches the actual number in the execution log. Do not reconstruct from memory.

### 1.2 Decision Point Extraction

Identify every point in the execution where the agent made a non-trivial choice:

```
## Decision Points
| # | Decision | Alternatives Considered | Choice Made | Rationale | Outcome |
|---|----------|------------------------|-------------|-----------|---------|
| D1 | [what was decided] | [option A, option B, ...] | [chosen option] | [why] | [result] |
```

Focus on decisions in NOVEL phases. For each decision, capture:
- The information available at the time of the decision (what tool outputs informed the choice)
- The reasoning process (conditional logic, threshold comparisons, domain knowledge applied)
- Whether the decision was correct in hindsight (did it lead to the desired outcome?)

### 1.3 Failure-Recovery Pair Extraction

For each failure event in the trace:

```
## Failure-Recovery Pairs
| # | Failure Signature | Tool Involved | Diagnosis | Recovery Action | Recovery Outcome |
|---|-------------------|---------------|-----------|----------------|-----------------|
| F1 | [error msg / output pattern] | [tool_name] | [root cause] | [recovery steps] | [success/partial/fail] |
```

### 1.4 Quality Gate Results Extraction

For each checkpoint in the trace:

```
## Quality Gate Results
| # | Checkpoint Type | Condition Tested | Result | Action Taken |
|---|----------------|-----------------|--------|--------------|
| QG1 | Checkpoint A (post-tool) | [condition] | [pass/fail] | [action if fail] |
```

**CHECKPOINT: Trace Mining Complete**
- [ ] Tool call sequence verified against execution log
- [ ] All NOVEL-phase decision points captured
- [ ] All failure-recovery pairs documented
- [ ] Quality gate results extracted
- [ ] No execution detail from NOVEL phases is missing

---

## Phase 2: Pattern Abstraction and Generalization

Transform the task-specific trace into a generalizable template.

### 2.1 Variable Abstraction

Replace all task-specific values with parameterized placeholders. Apply the following substitution rules systematically:

| Task-Specific Element | Placeholder | Example |
|----------------------|-------------|---------|
| Protein name/identifier | `$TARGET_PROTEIN` | "EGFR" → `$TARGET_PROTEIN` |
| PDB ID | `$PDB_ID` | "1M17" → `$PDB_ID` |
| Molecule SMILES (starting) | `$SEED_MOLECULE` | Erlotinib SMILES → `$SEED_MOLECULE` |
| Molecule SMILES (generated) | `$CANDIDATE_MOLECULE` | any generated SMILES → `$CANDIDATE_MOLECULE` |
| Residue identifiers | `$RESIDUE_ID ($NUMBERING_SCHEME)` | "Met769 (PDB)" → `$RESIDUE_ID ($NUMBERING_SCHEME)` |
| Score thresholds | `$THRESHOLD_[METRIC]` (default: `[value_used]`) | "−8.9 kcal/mol" → `$THRESHOLD_DOCKING_SCORE (default: −8.9)` |
| File paths | `$STEP_NN_[DESCRIPTION]` | "step03_docking.pdbqt" → `$STEP_03_DOCKING_POSE` |
| Numeric counts | `$N_[DESCRIPTION]` (default: `[value_used]`) | "10 conformations" → `$N_CONFORMATIONS (default: 10)` |

**Abstraction quality check:** After substitution, verify that the workflow remains executable with any valid instantiation of the placeholders — no remaining hard-coded task-specific values should exist in the NOVEL phases.

### 2.2 Decision Logic Formalization

Convert each decision point (from Phase 1.2) into a formal conditional block:

```
### Decision: [descriptive name]
Precondition: [what must be true for this decision to arise]
IF [condition A — expressed in terms of tool outputs and $THRESHOLD values]:
    → Action: [specific tool call or workflow step]
    → Parameters: [with $PLACEHOLDER values]
    → Expected outcome: [what should happen]
ELIF [condition B]:
    → Action: [alternative]
ELSE:
    → Fallback: [default action]
    → Warning: [what to flag if fallback is reached]
```

### 2.3 Invariant vs. Variable Identification

For each element of the workflow, classify as:

- **INVARIANT (must-preserve):** Elements that were essential to the success of the task and must be retained in any future application. Examples: specific quality gate conditions, tool invocation order constraints, mandatory verification steps.
- **VARIABLE (may-adapt):** Elements that were task-specific choices and may be adjusted for different applications. Examples: threshold values, number of iterations, specific molecule generation parameters.
- **OPTIONAL (may-omit):** Elements that were present in the trace but not essential to the outcome. Examples: supplementary analyses performed for completeness, redundant verification steps.

Document these classifications in the skill template to guide future users.

**CHECKPOINT: Abstraction Complete**
- [ ] All task-specific values replaced with placeholders
- [ ] Decision logic formalized as conditional blocks
- [ ] Elements classified as INVARIANT / VARIABLE / OPTIONAL
- [ ] Abstracted workflow is executable with any valid placeholder instantiation

---

## Phase 3: Skill Document Assembly

Assemble the abstracted patterns into a formatted skill document.

### 3.1 Document Construction — L1 Target

If the target level is L1, construct the document with the following structure:

```markdown
---
name: [auto-descriptive-kebab-case-name]
description: [one-paragraph summary]
license: MIT license
metadata:
    skill-author: MolClaw-Auto
    skill-level: L1-Tool-AUTO
    auto-generated: true
    source-task: "[summary]"
    source-execution-date: "[date]"
    source-platform: "[platform]"
    crystallization-trigger: "[T1/T2/T3/T4]"
    confidence: LOW
    validation-record: ["[source-task-id]"]
---

# [Descriptive Title]

## When to Use
[Generalized applicability conditions]

## When NOT to Use
[Exclusion conditions]

## Prerequisites
[Input requirements]

## Procedure
[Step-by-step with SCP tool names, parameterized]

## Parameters
| Parameter | Default | Range | Notes |
[Table of all $PLACEHOLDER values with defaults and valid ranges]

## Quality Checks
[Extracted from Phase 1.4, generalized]

## Known Failure Modes and Recovery
| Failure | Cause | Recovery |
[Extracted from Phase 1.3, generalized]

## Known Limitations
[Boundary conditions from source task]

## Provenance
- Source execution: [task summary, date, platform]
- Trace phases crystallized: [list]
- L3 principles referenced: [list with numbers]
```

### 3.2 Document Construction — L2 Target

If the target level is L2, construct the document following the full L2 template:

```markdown
---
name: [auto-descriptive-kebab-case-name]
description: [one-paragraph summary]
license: MIT license
metadata:
    skill-author: MolClaw-Auto
    skill-level: L2-Workflow-AUTO
    auto-generated: true
    source-task: "[summary]"
    source-execution-date: "[date]"
    source-platform: "[platform]"
    crystallization-trigger: "[T1/T2/T3/T4]"
    confidence: LOW
    validation-record: ["[source-task-id]"]
    methodology-ref: >
      [L3 principles referenced, same format as expert-curated L2 skills]
---

# [Descriptive Workflow Title]

## Applicability
**Use this skill when:** [generalized from source task class]
**Do NOT use this skill when:** [exclusion conditions]

## Prerequisites
| Input | Source | Required? |
[Table of inputs with placeholder references]

## Phase-by-Phase Execution Protocol

### Phase 1: [Title]
[Steps with SCP tool calls, quality gates, COUNT GATEs, MAPPING GATEs]

### Phase 2: [Title]
[...]

[Continue for all phases]

## Common Failures & Recovery
| Failure | Likely Cause | Recovery |
[Generalized from Phase 1.3]

## Quality Gates (Active Checkpoints)
**CHECKPOINT after Phase N:**
- [ ] [condition]
[...]

## Output Specification (Data Handoff Contract)
| Output | Format | Consumed by | Download Policy |
[Table of outputs]

## Known Limitations
[Boundary conditions, Grade B gaps if any]

## Provenance
[Same as L1 provenance section]
```

### 3.3 Cross-Reference Insertion

After constructing the document, insert L3 principle cross-references at every point specified in Principle 24.2 (Mandatory Cross-References table). These cross-references should be integrated naturally into the workflow text, following the style of existing L2 workflows.

**CHECKPOINT: Document Assembly Complete**
- [ ] Document follows the correct level template (L1 or L2)
- [ ] YAML metadata complete including all auto-generation fields
- [ ] All task-specific values parameterized
- [ ] L3 cross-references inserted at all required points
- [ ] Applicability and exclusion conditions are generalizable (not task-specific)

---

## Phase 4: Self-Validation and Quality Assurance

Before finalizing the generated skill, perform a series of validation checks.

### 4.1 Structural Validation

- [ ] YAML header parses without errors (all required fields present)
- [ ] Document follows the correct template for its target level
- [ ] All SCP tool names used in the document are valid (snake_case, exist in the tool registry)
- [ ] No skill names (kebab-case) appear in tool invocation contexts
- [ ] All placeholders have documented defaults and valid ranges
- [ ] No task-specific values remain in the generalized sections

### 4.2 Logical Validation

- [ ] Decision logic is internally consistent (no contradictory conditions)
- [ ] Phase dependencies are correctly ordered (no phase references a later phase's output)
- [ ] Data flow is connected: every phase's required input is produced by a prior phase or listed in prerequisites
- [ ] Failure-recovery actions are feasible (they reference available tools and valid parameter ranges)
- [ ] Convergence is guaranteed: no execution path leads to an infinite loop

### 4.3 Provenance Validation

- [ ] Every claim in the skill document traces back to a specific section of the source `run_log.md`
- [ ] Quality gate conditions trace back to actual checkpoint results in the source execution
- [ ] Parameter defaults trace back to the actual values used in the successful execution
- [ ] Failure-recovery entries trace back to actual failure events in the source execution

### 4.4 Scientific Validation

- [ ] The workflow does not violate any L3 principle (Chapters 1–7)
- [ ] Computation-first hierarchy (Principle 13) is respected — no step asks the LLM to "estimate" a value that a tool can compute
- [ ] Anti-fabrication safeguards (Principle 11) are embedded — COUNT GATEs are present where needed
- [ ] Uncertainty is honestly communicated (Principle 20) — known limitations are documented

**CHECKPOINT: Validation Complete**
- [ ] All structural checks pass
- [ ] All logical checks pass
- [ ] All provenance checks pass
- [ ] All scientific checks pass
- [ ] Decision recorded: FINALIZE / REVISE (with specific issues)

If any check fails, return to the appropriate phase (1–3) to correct the issue before proceeding.

---

## Phase 5: Storage, Indexing, and Registration

### 5.1 File Storage

Save the generated skill document to the designated directory:

- L1 skill: `[skill_package_root]/auto-generated-skills/L1_tools/[skill-name]/SKILL.md`
- L2 workflow: `[skill_package_root]/auto-generated-skills/L2_workflows/[skill-name].md`

**Path resolution:** `[skill_package_root]` is the directory containing the `L3_methodology/`, `L2_workflows/`, and `L1_tools/` subdirectories. Determine this by navigating up from the directory of the currently loaded L3 methodology document. If the `auto-generated-skills/` directory (or its subdirectories) does not exist, create it:
```bash
mkdir -p [skill_package_root]/auto-generated-skills/L1_tools
mkdir -p [skill_package_root]/auto-generated-skills/L2_workflows
```
If `skill-index.md` does not exist, initialize it with the header row (see Section 5.2).

### 5.2 Index Update

Append an entry to `[skill_package_root]/auto-generated-skills/skill-index.md`:

```markdown
| [next #] | [skill-name] | [L1/L2] | [T1/T2/T3/T4/T5] | LOW | [date] | [comma-separated SCP tool names] | [source task summary] |
```

The `Tools Involved` column must list all SCP tool names (snake_case) that the skill pertains to, enabling rapid grep-based filtering during failure-triggered retrieval (L3 Principle 25.6a).

### 5.3 Primary Task Report Annotation

Add the following to the primary task's `result.md`:

```markdown
## Skill Self-Generation Record
- **Generated skill:** [skill-name]
- **Level:** [L1/L2]-AUTO
- **Trigger:** [T1/T2/T3/T4/T5] — [one-sentence trigger description]
- **Confidence:** LOW (first application)
- **Location:** auto-generated-skills/[path]
- **Summary:** [2–3 sentence description of what the skill captures]
```

### 5.4 Completion Verification

**FINAL CHECKPOINT:**
- [ ] Skill document saved to correct path
- [ ] Index updated
- [ ] Primary task report annotated
- [ ] File integrity verified (saved file is non-empty and parseable)
- [ ] Total crystallization process recorded in `run_log.md`

---

## Common Failures & Recovery

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| Trigger re-evaluation invalidates the trigger | The novel pattern was a minor variant of existing skill | Abort gracefully; record in log. No skill generated. |
| Abstraction produces non-executable template | Over-abstraction removed essential task-specific constraints | Re-examine invariant/variable classification; restore incorrectly abstracted constants |
| Tool name validation fails | Skill document uses a deprecated or misspelled tool name | Enumerate current tools via SCP server; correct the name |
| Data flow validation fails | Phase dependency is circular or disconnected | Re-order phases; add missing intermediate steps |
| Generated document is excessively long (> 500 lines) | Insufficient abstraction; too much trace detail retained | Decompose into multiple skills (one L2 workflow referencing new L1 skills) |
| Context window insufficient for full crystallization | Primary task consumed most of available context after a complex E2E execution | Execute **simplified crystallization**: save only YAML header (with all metadata fields), applicability conditions, core tool sequence list (ordered SCP tool names with key parameters), and failure-recovery entries. Skip full phase-by-phase protocol and detailed decision logic. Mark confidence as `UNTESTED`. Record in run_log: "Simplified crystallization due to context constraints — full elaboration deferred." The simplified output can be expanded in a future session when loaded as the primary task. |

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Generated skill document | Markdown (.md) | Future task executions; skill library | **A — MUST save** |
| Updated skill index | Markdown (.md) | Future Phase 0 skill discovery | **A — MUST save** |
| Crystallization log | Appended to run_log.md | Audit trail | **B — SHOULD save** |
| Primary task report annotation | Appended to result.md | User visibility | **A — MUST save** |

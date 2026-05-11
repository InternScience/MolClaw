---
name: molclaw-skill-template-writer
description: >
  Formats extracted execution patterns into standard MolClaw skill documents. Accepts
  structured input from the Skill Crystallization Meta-Workflow (L2-12) and outputs a
  properly formatted L1 or L2 skill document conforming to MolClaw conventions. This
  skill ensures that auto-generated skills are structurally identical to expert-curated
  skills, enabling seamless integration into the skill matching and loading pipeline.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L1-Tool
    version: 1.0
    methodology-ref: >
      L3 Chapter 8 Supplement, Principle 25 (Experiential Crystallization),
      L2-12 Phase 3 (Skill Document Assembly)
---

# Skill Template Writer

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## When to Use

Use this skill when executing Phase 3 (Skill Document Assembly) of the Skill Crystallization Meta-Workflow (L2-12). This skill provides the exact formatting templates, field specifications, and validation checklists to ensure auto-generated skill documents conform to MolClaw standards.

## When NOT to Use

- Do NOT use this skill to modify existing expert-curated skills — those require human expert review.
- Do NOT use this skill outside the crystallization workflow — it has no standalone function.
- Do NOT use this skill to generate L3 principles — L3 content requires expert validation and is never auto-generated.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Abstracted tool call sequence | L2-12 Phase 2.1 | Yes |
| Formalized decision logic | L2-12 Phase 2.2 | Yes |
| Invariant/variable classification | L2-12 Phase 2.3 | Yes |
| Failure-recovery pairs | L2-12 Phase 1.3 | Yes |
| Quality gate results | L2-12 Phase 1.4 | Yes |
| Target level (L1 or L2) | L2-12 Phase 0.2 | Yes |
| Trigger ID and source task summary | L2-12 Phase 0.1 | Yes |

## Step 1: Select Template

Based on the target level and (for L2) the workflow paradigm identified in L2-12 Phase 0.4, select the appropriate template:

| Target Level | Paradigm (from Phase 0.4) | Template | Reference Skeleton |
|-------------|--------------------------|----------|-------------------|
| L1 | — | Section A: L1 Skill Template | Any existing L1 SKILL.md |
| L1 (T5 failure memo) | — | Section A-F: Failure Pattern Memo | Existing L1 failure-recovery tables |
| L2 | Pipeline (A) | Section B-A: L2 Pipeline Template | L2-01, L2-07, L2-08 |
| L2 | Iterative Loop (B) | Section B-B: L2 Iterative Loop Template | L2-05, L2-10 |
| L2 | Branching Decision (C) | Section B-C: L2 Branching Decision Template | L2-02, L2-04 |
| L2 | Mixed | Choose dominant paradigm template; embed secondary paradigm within one phase | Combine reference skeletons |

**Key differences between L2 sub-templates:**

- **Pipeline (A):** Phases are sequential and non-repeating. Each phase has exactly one CHECKPOINT. No seed update logic, no convergence criteria, no iteration records. The output of the final phase is the deliverable.
- **Iterative Loop (B):** Must include: Evaluate→Diagnose→Design→Verify cycle structure; seed molecule/state update rule between rounds; global target tracker (if cumulative termination conditions exist); convergence criteria section (L3 Principle 7); iteration record requirements referencing L3 Principle 8; docking/evaluation parameter locking if applicable.
- **Branching Decision (C):** Must include: scene/mode classification table at the entry point; "Use when" conditions for each branch; shared prerequisites and branch-specific prerequisites; branch-specific sub-protocols that may have different tool compositions.

When writing the skill document in Step 3, copy the structural patterns (section ordering, checkpoint placement, table formats) from the identified reference L2 workflow. This ensures the auto-generated skill is structurally familiar to the agent when it is loaded in future sessions.

## Step 2: Populate YAML Header

Fill in all YAML metadata fields using the following specifications:

### YAML Field Reference

| Field | Format | Source | Example |
|-------|--------|--------|---------|
| `name` | kebab-case, prefix with context | Descriptive of function | `molclaw-cryptic-pocket-ensemble-screening` |
| `description` | One paragraph, max 3 sentences | Summarize the skill's purpose | "Discover transient binding pockets from..." |
| `license` | Fixed | Always | `MIT license` |
| `metadata.skill-author` | Fixed | Always | `MolClaw-Auto` |
| `metadata.skill-level` | Enum | Phase 0.2 decision | `L1-Tool-AUTO` or `L2-Workflow-AUTO` |
| `metadata.auto-generated` | Boolean | Always | `true` |
| `metadata.source-task` | One sentence | Source task description | "QED optimization of triazolo-benzodiazepine" |
| `metadata.source-execution-date` | ISO date | Execution date | `2026-04-01` |
| `metadata.source-platform` | String | Platform used | `Claude Code` or `OpenClaw` |
| `metadata.crystallization-trigger` | Enum | Phase 0.1 | `T1`, `T2`, `T3`, `T4`, or `T5` |
| `metadata.confidence` | Enum | Always initial | `LOW` (first generation) |
| `metadata.validation-record` | List | Source task ID | `["task-2026-04-01-001"]` |
| `metadata.methodology-ref` | Multi-line | L3 principles used | See existing L2 skills for format |

**Naming Convention for `name` field:**

- Start with `molclaw-` prefix
- Use descriptive terms reflecting the skill's function
- Keep under 60 characters
- Examples: `molclaw-reinvent-low-tanimoto-fallback`, `molclaw-cryptic-pocket-discovery`, `molclaw-multi-target-selectivity-optimization`

## Step 3: Populate Body Sections

Fill in each section of the selected template using the crystallization inputs. Follow the section-by-section instructions below.

### 3.1 Applicability Section (L2 only)

**"Use when" rules:**
- Generalize from the source task's characteristics to the task CLASS
- CORRECT: "Use when the user needs to identify transient binding pockets not visible in the crystal structure"
- INCORRECT: "Use when working with EGFR kinase domain PDB 1M17" (too specific)

**"Do NOT use when" rules:**
- List situations where this workflow is inappropriate or where an existing workflow should be used instead
- Reference existing L2 workflows by number: "Use Skill 2 instead when..."

### 3.2 Prerequisites Table

- List all required inputs
- For each input, specify: the source (user-provided, or output of another skill), whether it is required or optional
- Use placeholder format for task-specific inputs: `$TARGET_PROTEIN`, `$SEED_MOLECULE`, etc.

### 3.3 Procedure / Phase Protocol

**For L1 skills:** Write as numbered steps with clear tool invocations.

Each step must include:
- The SCP tool name (snake_case) — NEVER use skill names (kebab-case) in tool call contexts
- Required parameters with defaults from the source execution
- The expected output and how to verify it
- A quality check condition (derived from Phase 1.4 quality gates)

**For L2 workflows:** Organize into numbered phases with embedded checkpoints.

Each phase must include:
- A clear objective statement
- Specific tool calls with `call_tool("tool_name", ...)` syntax
- A CHECKPOINT block after each phase with pass/fail conditions
- COUNT GATE blocks where molecule/structure counts change
- MAPPING GATE blocks before residue-specific analysis (if applicable)
- Decision points formatted as conditional blocks (from Phase 2.2)

### 3.4 Parameters Table (recommended for all skills)

```markdown
## Parameters

| Parameter | Placeholder | Default | Valid Range | Notes |
|-----------|------------|---------|-------------|-------|
| [name] | $PLACEHOLDER | [value from source] | [range] | [when to change] |
```

### 3.5 Failure-Recovery Table

Populate from Phase 1.3 extraction, generalized:

```markdown
## Common Failures & Recovery

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| [generalized failure signature] | [root cause] | [recovery steps with tool names] |
```

**Rules for generalization:**
- Replace specific error messages with patterns: "JSON parse error" → "Output parsing failure"
- Replace specific tool versions with generic references
- Ensure recovery actions reference available tools, not task-specific workarounds

### 3.6 Quality Gates (L2 only)

```markdown
## Quality Gates (Active Checkpoints)

**CHECKPOINT after Phase N:**
- [ ] [condition from source execution, generalized]
```

### 3.7 Output Specification (L2 only)

```markdown
## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| [output name] | [format] | [downstream skill or report] | [A/B/C] |
```

### 3.8 Known Limitations

**Mandatory content:**
- Conditions under which the skill is expected to fail
- Aspects of the source task that were NOT generalized (and why)
- Tool version dependencies
- Grade B gaps (if the source task was Grade B per Principle 23)
- Computational cost estimate

### 3.9 Provenance Section

```markdown
## Provenance

- **Source execution:** [task summary], [date], [platform]
- **Crystallization trigger:** [T1/T2/T3/T4] — [description]
- **Trace phases crystallized:** [list of NOVEL phases]
- **L3 principles referenced:** [list with numbers]
- **Original execution success metric:** [metric name] = [achieved value]
```

## Step 4: Validate the Generated Document

Run through the validation checklist from L2-12 Phase 4:

**Structural checks:**
- [ ] YAML parses correctly
- [ ] All required sections present for the target level
- [ ] All SCP tool names are snake_case
- [ ] No kebab-case skill names in tool invocation contexts
- [ ] All placeholders have documented defaults

**Logical checks:**
- [ ] Phase dependencies are correctly ordered
- [ ] Data flow is connected
- [ ] Decision conditions are non-contradictory
- [ ] No infinite loops possible

**Style consistency checks:**
- [ ] Markdown heading hierarchy matches existing skills (# for title, ## for sections, ### for subsections)
- [ ] Table formatting is consistent
- [ ] Code blocks use correct syntax highlighting
- [ ] Cross-references use principle numbers (e.g., "Principle 11") not section names

## Step 5: Output the Document

Write the validated document to the appropriate path:

- L1: `auto-generated-skills/L1_tools/[skill-name]/SKILL.md`
- L2: `auto-generated-skills/L2_workflows/[skill-name].md`

Verify the file was written successfully and is non-empty.

---

## Section A: L1 Skill Template

```markdown
---
name: molclaw-[descriptive-name]
description: [1–3 sentence summary]
license: MIT license
metadata:
    skill-author: MolClaw-Auto
    skill-level: L1-Tool-AUTO
    auto-generated: true
    source-task: "[summary]"
    source-execution-date: "[date]"
    source-platform: "[platform]"
    crystallization-trigger: "[TN]"
    confidence: LOW
    validation-record: ["[task-id]"]
---

# [Descriptive Title]

## When to Use
[Generalized applicability conditions — describe the task CLASS, not the specific task]

## When NOT to Use
[Exclusion conditions — reference existing skills that should be used instead]

## Prerequisites
[What must exist before this skill can be executed]

## Procedure

### Step 1: [Action Title]
[Description with SCP tool call]
- Tool: `call_tool("[scp_tool_name]", arguments={...})`
- Expected output: [description]
- Quality check: [condition to verify before proceeding]

### Step 2: [Action Title]
[...]

[Continue for all steps]

## Parameters
| Parameter | Default | Valid Range | Notes |
|-----------|---------|-------------|-------|
| [name] | [value] | [range] | [guidance] |

## Known Failure Modes and Recovery
| Failure | Cause | Recovery |
|---------|-------|----------|
| [pattern] | [cause] | [action] |

## Known Limitations
[Boundary conditions, version dependencies, reliability notes]

## Provenance
- Source execution: [summary, date, platform]
- Crystallization trigger: [TN] — [description]
- L3 principles referenced: [numbers]
```

## Section A-F: Failure Pattern Memo Template (T5 only)

When the crystallization trigger is T5 (systematic failure pattern), use this simplified template instead of the full L1 skill template. A Failure Pattern Memo documents a tool's usage restriction, not a new capability.

```markdown
---
name: molclaw-[tool-name]-[failure-condition]-memo
description: >
  Failure pattern memo: [tool_name] fails under [condition]. Documents the failure
  signature, root cause, and recommended avoidance strategy.
license: MIT license
metadata:
    skill-author: MolClaw-Auto
    skill-level: L1-Tool-AUTO
    auto-generated: true
    memo-type: failure-pattern
    source-task: "[summary]"
    source-execution-date: "[date]"
    source-platform: "[platform]"
    crystallization-trigger: T5
    confidence: LOW
    validation-record: ["[task-id]"]
    target-skill-for-integration: "[existing L1 skill name whose failure table should incorporate this memo]"
---

# Failure Pattern Memo: [Tool Name] — [Short Failure Description]

## Affected Tool
- SCP tool name: `[snake_case_tool_name]`
- Related L1 skill: [existing skill name, e.g., molclaw-quickvina-docking]

## Failure Condition
[Precise description of the input characteristics that trigger the failure. Must be specific enough to serve as a "Do NOT use when" condition.]

| Condition Parameter | Trigger Value / Range | How to Check |
|--------------------|----------------------|-------------|
| [e.g., seed Tanimoto to training dist.] | [e.g., < 0.3] | [e.g., compute Morgan FP Tanimoto against ChEMBL drug-like set] |

## Failure Signature
[What the failure looks like: error message, empty output, nonsensical values, crash, etc.]

```
[Exact error message or output pattern, if available]
```

## Root Cause Analysis
[Why the tool fails under these conditions. Agent's diagnosis based on execution evidence.]

## Recommended Avoidance Strategy
[How to avoid triggering this failure. Options:]
1. **Pre-check:** [Condition to check before calling the tool]
2. **Alternative tool:** [If available, which tool to use instead]
3. **Parameter adjustment:** [If the failure can be avoided by changing parameters]
4. **Workflow modification:** [If the workflow should route around this tool under these conditions]

## Evidence from Source Execution
- Task: [summary]
- Failure occurred at: [which phase/step]
- Number of occurrences: [how many times in the session]
- Recovery used in source task: [what the agent did to work around it]
- Outcome of recovery: [success/partial/fail]

## Integration Recommendation
This memo should be integrated into the failure-and-recovery table of skill `[target-skill-name]` as a new entry:

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| [generalized failure signature] | [root cause] | [recommended avoidance/recovery] |
```

---

## Section B: L2 Workflow Templates (Paradigm-Specific)

Select the sub-template matching the paradigm identified in L2-12 Phase 0.4. All three sub-templates share the same YAML header structure; they differ in body organization.

### Shared L2 YAML Header (all paradigms)

```yaml
---
name: molclaw-[descriptive-name]
description: [1–3 sentence summary]
license: MIT license
metadata:
    skill-author: MolClaw-Auto
    skill-level: L2-Workflow-AUTO
    auto-generated: true
    source-task: "[summary]"
    source-execution-date: "[date]"
    source-platform: "[platform]"
    crystallization-trigger: "[TN]"
    confidence: LOW
    validation-record: ["[task-id]"]
    workflow-paradigm: "[Pipeline / Iterative Loop / Branching Decision]"
    reference-L2: "[L2-NN used as structural skeleton]"
    methodology-ref: >
      [L3 principles referenced with chapter and number]
---
```

### Section B-A: L2 Pipeline Template (Paradigm A)

Reference skeletons: L2-01 (protein preparation), L2-07 (conformational sampling), L2-08 (post-docking evaluation).

```markdown
# [Descriptive Workflow Title]

## Applicability
**Use this skill when:** [generalized task class description]
**Do NOT use this skill when:** [exclusion conditions]

## Prerequisites
| Input | Source | Required? |
|-------|--------|-----------|
| [input] | [source] | [Yes/No] |

## Phase 1: [Input Preparation / Acquisition]
[Objective: prepare all inputs for the core computation]
[Tool calls with parameters]
**CHECKPOINT after Phase 1:**
- [ ] All required input files exist and are non-empty
- [ ] Input format verified for Phase 2 compatibility

## Phase 2: [Core Computation]
[Objective: execute the primary computational step(s)]
[Tool calls]
**COUNT GATE:** [Verify output counts if applicable]
**CHECKPOINT after Phase 2:**
- [ ] Output files exist and pass plausibility checks (Principle 9)
- [ ] All structure files downloaded (Principle 14)

## Phase 3: [Analysis / Post-Processing]
[Objective: analyze outputs, generate deliverables]
[Tool calls]
**MAPPING GATE:** [If residue-specific analysis, verify numbering]
**CHECKPOINT after Phase 3:**
- [ ] Analysis results verified against source files (Principle 11)
- [ ] All images/visualizations downloaded (Principle 15)

## Phase 4: [Quality Assessment and Reporting]
[Objective: final verification and report generation]
**Checkpoint C (pre-report audit, Principle 12):**
- [ ] Data integrity verification table complete
- [ ] File inventory complete

## Common Failures & Recovery
| Failure | Likely Cause | Recovery |
|---------|-------------|----------|

## Output Specification (Data Handoff Contract)
| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|

## Known Limitations
## Provenance
```

### Section B-B: L2 Iterative Loop Template (Paradigm B)

Reference skeletons: L2-05 (iterative molecular optimization), L2-10 (protein sequence design validation).

```markdown
# [Descriptive Workflow Title]

## Applicability
**Use this skill when:** [generalized task class description]
**Do NOT use this skill when:** [exclusion conditions; reference L2-05 or L2-10 if appropriate]

## Prerequisites
| Input | Source | Required? |
|-------|--------|-----------|

## Scene Classification (if multiple optimization modes)
**Scene A:** [description] — Core evidence: [tools]
**Scene B:** [description] — Core evidence: [tools]

## Baseline Establishment (Phase 0)
[Establish baseline metrics before entering the loop]
[Lock parameters that must remain constant across rounds — ref L2-05 Docking Parameter Locking]

## Iterative Loop Architecture (Phases 1–N)

Each round consists of four steps forming an **Evaluate → Diagnose → Design → Verify** closed loop.

### Step 1: Current State Assessment
[Full evaluation using all relevant tools]
[Record all metrics from tool returns — Principle 11]
**CHECKPOINT after Step 1:**
- [ ] All scores from tool returns (not memory)
- [ ] Structure files downloaded

### Step 2: Diagnosis and Strategy Formulation
[Three questions from Principle 5:]
1. What is this round trying to improve? [must cite Step 1 data]
2. What strategy? [chemical/structural rationale]
3. How to measure improvement? [quantifiable criterion]

### Step 3: Design and Generation
[LLM-guided design and/or REINVENT generation]
[Scaffold preservation check if required]
[Drug-likeness filtering]
**COUNT GATE:** Verify candidate count

### Step 4: Verification and Decision
[Re-evaluate candidates with Step 1 tools]
[Compare against baseline AND previous round best]
**Decision logic:**
- IF success criteria met → Report. Done.
- ELIF round < max_rounds → Update seed (Seed Update Rule), return to Step 1
- ELSE → Report global best with complete trajectory

### Seed Update Rule
[Define how the seed molecule/state is updated between rounds]

### Global Target Tracker (if cumulative termination)
[Maintain and check cumulative progress — ref L2-05]

### Convergence Criteria (Principle 7)
[Define specific stopping conditions for this workflow]

## Exploration–Exploitation Schedule (Principle 6)
| Round | Strategy | Scope |
|-------|----------|-------|

## Iteration Record Requirements (Principle 8)
[Optimization trajectory table format with Source Files column]

## Common Failures & Recovery
| Failure | Likely Cause | Recovery |
|---------|-------------|----------|

## Quality Gates (Active Checkpoints)
[Summary of all per-step checkpoints]

## Output Specification (Data Handoff Contract)
| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|

## Known Limitations
## Provenance
```

### Section B-C: L2 Branching Decision Template (Paradigm C)

Reference skeletons: L2-02 (docking screening by library size), L2-04 (generative molecular design by mode).

```markdown
# [Descriptive Workflow Title]

## Applicability
**Use this skill when:** [generalized task class description]
**Do NOT use this skill when:** [exclusion conditions]

## Prerequisites
| Input | Source | Required? |
|-------|--------|-----------|

## Mode / Scene Classification (Decision Entry Point)

Classify the task into one of the following modes based on [classification criterion]:

| Criterion | Mode | Sub-Protocol |
|-----------|------|-------------|
| [condition A] | Mode 1: [name] | See Section below |
| [condition B] | Mode 2: [name] | See Section below |
| [condition C] | Mode 3: [name] | See Section below |

## Shared Prerequisites and Setup (all modes)
[Steps common to all modes, executed before branching]

## Mode 1: [Name]
### Phase 1-1: [Title]
[Mode-specific steps]
### Phase 1-2: [Title]
[...]
**CHECKPOINT after Mode 1:**
- [ ] [mode-specific conditions]

## Mode 2: [Name]
### Phase 2-1: [Title]
[Mode-specific steps]
[...]

## Mode 3: [Name]
[...]

## Shared Post-Processing (all modes)
[Steps common to all modes, executed after branching]

## Common Failures & Recovery
| Failure | Likely Cause | Recovery |
|---------|-------------|----------|

## Output Specification (Data Handoff Contract)
| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|

## Known Limitations
## Provenance
```

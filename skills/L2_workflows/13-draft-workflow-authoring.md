---
name: molclaw-draft-workflow-authoring
description: >
  Meta-workflow for autonomous draft workflow authoring. Invoked when the agent
  encounters a concrete execution task that does not match any existing L2 workflow
  (≥ 70% tool-sequence overlap) AND has been classified as Grade A or Grade B per
  L3 Principle 23.2. This workflow operationalizes L3 Chapter 8 Principle 24
  (Autonomous Workflow Authoring) as a reproducible step-by-step procedure that
  produces a compliant draft workflow document, marks it as DRAFT, and hands it
  off for execution. Successful execution of the draft workflow is the canonical
  upstream event for T1 crystallization in L2-12.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 1.0
    methodology-ref: >
      L3 Chapter 8 Supplement Principle 24 in its entirety (24.1 Structural
      Requirements, 24.2 Mandatory Cross-References, 24.3 Draft Workflow Marking
      and Limitation Declaration, 24.4 Scope Restrictions),
      Principle 23.1a (Data Flow Connectivity Map — used to verify path closure),
      Principle 23.2 (Grade A/B/C — entry condition),
      Principle 25 (Experiential Crystallization — downstream consumer),
      Principle 26 (Capability Boundary Self-Awareness — invoked throughout),
      L3 Principles 1, 4–8, 9, 11, 12, 13, 17, 18, 20, 22 (referenced at workflow
      execution points per Principle 24.2 cross-reference table)
---

# Draft Workflow Authoring Meta-Workflow

## Applicability

**Use this workflow when:** The agent has received a concrete execution task (specific target / ligand / deliverable) AND the following entry conditions all hold:
- No single existing L2 workflow covers the task at ≥ 70% tool-sequence match (same novelty threshold used by L2-12 Phase 0.1 trigger validation).
- The task is classified Grade A or Grade B per L3 Principle 23.2 (Grade C tasks MUST be refused per Principle 23.2, not authored).
- The required tool chain length is ≤ 25 (per Principle 24.4 scope restriction).
- The task's required tool parameters are within documented ranges in existing L1 SKILL.md files (if not, this becomes a Grade B gap to be declared, not a reason to refuse authoring).

**Do NOT use this workflow when:**
- An existing L2 workflow covers the task — use that L2 instead (do not duplicate expert-curated content as a draft).
- The task is Grade C — refuse execution per Principle 23.2; do not author a draft that silently papers over capability gaps.
- The task is an open-ended problem discovery request — use L2-00 instead.
- The task requires a tool chain longer than 25 invocations — decompose into sub-workflows first, each authored independently.
- An auto-generated skill with confidence ≥ MEDIUM already covers this task class — load that skill instead of re-authoring.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| L3 methodology (parent document) | `skills/L3_methodology/molclaw-drug-discovery-methodology.md` | Yes |
| L3 Chapter 8 Supplement | `skills/L3_methodology/molclaw-drug-discovery-methodology-supplement-ch8.md` | Yes |
| Concrete task description with specific deliverables | User input | Yes |
| Full L1 skill registry (SKILL.md for every tool anticipated in the draft) | `skills/L1_tools/` on demand | Yes (on demand per Phase 2) |
| Existing L2 workflow list (for novelty verification) | `ls skills/L2_workflows/` | Yes |
| Auto-generated skill index (if exists) | `skills/auto-generated-skills/skill-index.md` | Optional |
| Reference L2 workflow for paradigm skeleton | Selected in Phase 1 | Yes |

---

## Phase 0: Entry Validation

Before committing to authoring, confirm all entry conditions and record the decision with deliberate skepticism.

### 0.1 Novelty Verification

Scan every existing L2 workflow in `skills/L2_workflows/` and every auto-generated skill in `skills/auto-generated-skills/L2_workflows/`. For each, extract the ordered tool sequence from its Phase-by-Phase Execution Protocol and compare against the anticipated tool sequence for the current task.

- If any existing workflow matches ≥ 70% of the anticipated sequence in the same order → ABORT; use that workflow instead. Record: `Draft authoring ABORTED: existing workflow [L2-NN or auto-skill name] covers this task.`
- If all existing workflows match < 70% → PROCEED.

### 0.2 Feasibility Grade Confirmation

Re-run Principle 23.2 classification on the current task:

- [ ] Every anticipated computational step maps to ≥ 1 available tool (verify via L1 folder scan).
- [ ] Data flow between steps is compatible (verify via Principle 23.1a produce→consume map).
- [ ] At least one quantitative success criterion is defined or definable.
- [ ] Expected computational time is within session budget.

Record the grade: `Feasibility Grade: [A / B with gap list]`. If Grade C → ABORT authoring; refuse execution per Principle 23.2.

### 0.3 Scope Compliance Precheck

Apply Principle 24.4 scope restrictions:

- [ ] Anticipated tool chain length ≤ 25 invocations.
- [ ] Required parameter ranges within ranges documented in existing L1 SKILL.md files (if not, mark as Grade B gap — do not override silently).
- [ ] No recursive self-invocation planned.
- [ ] Task completable within a single session (if cross-session needed, flag to user before authoring).

### 0.4 Draft Mode Declaration

Append to the top of `run_log.md` (before any tool call):

```
## ⚠️ DRAFT WORKFLOW EXECUTION
This task was executed using an agent-authored draft workflow, not an
expert-curated L2 skill. Results should be interpreted with additional caution.
- Draft workflow name: draft-[descriptive-name]
- Feasibility grade: [A / B]
- Declared Grade B gaps (if any): [list]
- Parent L3 principles: [list]
```

**CHECKPOINT: Entry Validation Complete**
- [ ] Novelty confirmed (≥70% match test failed for all existing workflows)
- [ ] Grade A or B confirmed (never C)
- [ ] Scope restrictions satisfied or gaps declared as Grade B
- [ ] Draft mode declared in run_log.md
- [ ] Decision recorded: PROCEED / ABORT with reason

---

## Phase 1: Paradigm Matching and Reference Skeleton Selection

Identify which structural paradigm the draft workflow will follow and select the reference L2 whose skeleton will be copied. This is the same paradigm matching logic used by L2-12 Phase 0.4; the two workflows share this sub-process.

### 1.1 Anticipated Trace Analysis

Based on the task's logical structure (not yet executed), predict the trace shape:

| Trace Characteristic | Paradigm | Reference L2 | Skeleton to Copy |
|---------------------|----------|-------------|------------------|
| Linear data flow: tools execute in strict sequence, each tool's output feeds the next, no tool group is invoked more than once | **Pipeline (A)** | L2-01 (protein prep), L2-07 (conformational sampling), L2-08 (post-docking evaluation) | Sequential phases with strict dependencies; one CHECKPOINT per phase |
| Same tool group invoked ≥ 2 rounds: each round has seed/state update, strategy adaptation, convergence check | **Iterative Loop (B)** | L2-05 (iterative optimization), L2-10 (protein design validation) | Evaluate→Diagnose→Design→Verify cycle; seed update rule; convergence criteria |
| Input-dependent routing: execution path branches based on task characteristics or intermediate results | **Branching Decision (C)** | L2-02 (docking screening by library size), L2-04 (generative design by mode) | Decision tree entry; scene/mode classification; scene-specific sub-protocols |

### 1.2 Mixed Paradigm Handling

If the anticipated trace combines paradigms (e.g., a Pipeline phase followed by an Iterative Loop phase), select the dominant paradigm for overall structure and embed the secondary paradigm within a single phase. Follow the same rule as L2-12 Phase 0.4 mixed-paradigm clause for consistency.

### 1.3 Reference L2 Open-and-Read

Read the selected reference L2's Phase-by-Phase Execution Protocol, CHECKPOINT placement, COUNT GATE / MAPPING GATE placement, and Output Specification table. These are the structural elements to be copied (not the domain-specific content).

**CHECKPOINT: Paradigm Matched**
- [ ] Paradigm identified (A / B / C / mixed with dominant)
- [ ] Reference L2 selected and read
- [ ] Structural elements identified for copying (phase count, checkpoint positions, gate positions)
- [ ] Decision recorded: `Paradigm: [A/B/C]. Reference L2: [NN]. Rationale: [explanation].`

---

<!-- NEW: Optional LR method precedent search -->
### Optional: Method Precedent Search (if LR tools are available)

Before finalizing the draft workflow's tool chain in Phase 2, search for published computational studies addressing a similar question:

1. PubMed search: `"[scientific question keywords] computational"` (retmax=10)
2. Note: which methods were used, what worked, what limitations were reported, what validation strategies were applied
3. Use findings to validate or refine the draft's tool chain choices:
   - If a published study used the same tool chain → confidence boost; check for pitfalls they reported
   - If a published study used a different method → evaluate whether their approach suggests missing steps in the draft
   - If a published study used a method not in the current toolkit → record as a Grade B/C gap in the draft's Limitations
4. Record: `[LR] Method precedent search: [query] → [count] relevant studies found. Key insight: [summary with PMID]`

**If LR tools are not available**, proceed to Phase 2 using computational reasoning and L3 methodology guidance alone.

---

## Phase 2: Data Flow Specification and Tool Chain Verification

Before filling in the skeleton, specify the data flow and verify that the tool chain is closed and within scope.

### 2.1 Edge-by-Edge Specification

For each anticipated phase of the draft workflow, specify:

- **Input data type(s)** — what the phase receives, tied to Principle 23.1a data type vocabulary
- **Tool invocation(s)** — SCP tool name(s) (snake_case), with provisional parameters
- **Output data type(s)** — what the phase produces
- **Downstream consumer phase** — which subsequent phase consumes this output

Produce the following table:

| Phase # | Input Data Type | Tool(s) Invoked | Parameters (provisional) | Output Data Type | Consumed by |
|---------|----------------|-----------------|-------------------------|------------------|-------------|
| 1 | [type] | [scp_tool_name] | [key=value, ...] | [type] | Phase 2 |
| 2 | [type] | [scp_tool_name] | [...] | [type] | Phase 3 |
| ... | ... | ... | ... | ... | ... |

### 2.2 Path Closure Verification

Walk the table from Phase 1 input to the terminal deliverable:
- [ ] Every phase's input data type is produced by a prior phase OR is a user-provided prerequisite.
- [ ] Every phase's output data type is consumed by a downstream phase OR is the final deliverable.
- [ ] No dangling outputs (produced but never consumed).
- [ ] No unsatisfied inputs (consumed but never produced).

If path closure fails → return to Phase 1 and revise the skeleton, OR insert a utility tool from L1 (format converters, residue mapper, chain extractor) to bridge the gap.

### 2.3 Tool Chain Length Check

Count distinct tool invocations across all phases (counting the same tool invoked in multiple phases as separate invocations, per Principle 24.4 convention).

**COUNT GATE:** `Tool chain length: [count]`. If count > 25 → ABORT; decompose the task into sub-workflows per Principle 24.4 and author each independently.

### 2.4 Parameter Range Check

For every provisional parameter in the table, open the corresponding L1 SKILL.md and verify the parameter value is within the documented valid range:
- If within range → OK.
- If outside range but the L1 SKILL.md notes "may be extended with caution" → document as a Grade B gap; do not use silently.
- If outside range with no such note → revise to within-range value OR re-classify task as Grade B with explicit gap declaration OR ABORT.

**CHECKPOINT: Data Flow Specified**
- [ ] Every phase has input/tool/params/output/consumer declared
- [ ] Path closure verified (no dangling edges)
- [ ] Tool chain length ≤ 25 (Principle 24.4)
- [ ] All parameters within L1-documented ranges OR declared as Grade B gaps

---

## Phase 3: Six-Section Skeleton Population

Assemble the draft workflow document following the exact section structure mandated by Principle 24.1. Six sections are required; all must be present.

### 3.1 YAML Metadata Header (Principle 24.1 #1)

```yaml
---
name: draft-[descriptive-kebab-case-name]
description: >
  [One-paragraph summary of the draft workflow's purpose, derived from the task
  description and generalized to the task class.]
license: MIT license
metadata:
    skill-author: MolClaw-Agent
    skill-level: L2-Workflow-DRAFT
    source-task: "[one-sentence description of the task that prompted this draft]"
    source-session-date: "[date]"
    source-platform: "[Claude Code / OpenClaw]"
    feasibility-grade: "[A / B]"
    grade-b-gaps: "[list if grade B, omit field if grade A]"
    paradigm: "[Pipeline A / Iterative Loop B / Branching Decision C / Mixed-A-dominant / etc.]"
    reference-L2: "[L2-NN used as skeleton]"
    methodology-ref: >
      [List of parent L3 principles referenced, with chapter and principle numbers]
    confidence: UNTESTED
    tool-chain-length: [count from Phase 2.3]
---
```

### 3.2 Applicability Section (Principle 24.1 #2)

```markdown
## Applicability

**Use this draft workflow when:** [generalized from the current task; describe the task CLASS, not the specific instance]

**Do NOT use this draft workflow when:**
- [exclusion conditions]
- An existing expert-curated L2 workflow covers a substantially similar task (see L2-NN).
- Capability boundaries per Principle 26 are violated (e.g., protein exceeds ESMFold size limit).
```

### 3.3 Prerequisites Table (Principle 24.1 #3)

```markdown
## Prerequisites

| Input | Source | Required? | Notes |
|-------|--------|-----------|-------|
| [input name] | [user / upstream phase / L1 tool output] | [Yes/No] | [validation requirements] |
```

### 3.4 Phase-by-Phase Execution Protocol (Principle 24.1 #4)

Copy the reference L2's phase structure (from Phase 1.3), then populate each phase with:

```markdown
### Phase [N]: [Phase Title]

**Objective:** [one-sentence objective]

**Tool calls:**
- `call_tool("[scp_tool_name]", arguments={[params from Phase 2.1]})`
- Expected output: [description]
- Output file: `step[NN]_[description].[ext]`

**COUNT GATE:** [insert wherever molecule/structure counts change — Principle 24.2]
**MAPPING GATE:** [insert before any residue-specific analysis — Principle 24.2]

**CHECKPOINT after Phase [N]:**
- [ ] [Principle 9 plausibility check condition]
- [ ] [Principle 10 three-category labeling applied]
- [ ] [Principle 11 count verification if applicable]
- [ ] All output files downloaded per Principle 14/15 policy
```

Embed checkpoints, COUNT GATEs, and MAPPING GATEs at the structurally equivalent positions inherited from the reference L2.

### 3.5 Failure-and-Recovery Table (Principle 24.1 #5)

Anticipate ≥ 3 failure modes by consulting the L1 SKILL.md files of each tool in the chain and extracting failure patterns from their "Common Failures" sections (or equivalent).

```markdown
## Common Failures & Recovery

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| [failure signature from L1 SKILL.md] | [root cause] | [recovery action referencing available tools] |
| [≥ 3 entries required] | | |
```

### 3.6 Output Specification / Data Handoff Contract (Principle 24.1 #6)

```markdown
## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy (Principle 16) |
|--------|--------|-------------|-------------------------------|
| [output artifact] | [format] | [downstream consumer / final report] | [A / B / C] |
```

**CHECKPOINT: Six Sections Populated**
- [ ] YAML header with all mandatory fields including `draft-` prefix and `L2-Workflow-DRAFT` level
- [ ] Applicability section with both Use-when and Do-NOT-use conditions
- [ ] Prerequisites table non-empty
- [ ] Phase-by-phase protocol with at least one CHECKPOINT per phase
- [ ] Failure table with ≥ 3 entries
- [ ] Output specification with download policy for each output

---

## Phase 4: Mandatory Cross-Reference Insertion

Insert references to parent L3 principles at every required execution point, per the Principle 24.2 cross-reference table. These references are not decorative — they direct the executing agent to the operative principle at the moment it is needed.

### 4.1 Cross-Reference Checklist

Walk the draft workflow and verify insertion at each point specified in Principle 24.2:

| Execution Point in Draft | Required Reference | Inserted? |
|-------------------------|-------------------|-----------|
| Before first tool call | Principle 1 (plan complete?) | [ ] |
| Every molecule/structure count change | Principle 11 (COUNT GATE) | [ ] |
| Every evaluation step | Principle 9 (plausibility), Principle 10 (three-category) | [ ] |
| Before residue-specific interpretation | Principle 17 (MAPPING GATE) | [ ] |
| Every docking setup | Principle 18 (box ≥ 25 Å, progressive enlargement) | [ ] |
| Before any report text | Principle 13 (computation-first) | [ ] |
| Iterative decision points | Principles 4–8 | [ ] |
| Before final report | Principle 12 Checkpoint C | [ ] |

### 4.2 Insertion Style

Follow the style of expert-curated L2 workflows: references are written inline as short parenthetical notes, e.g., `*(ref Principle 11)*` or `*(COUNT GATE — Principle 11)*`. Do NOT reproduce principle text in the draft; refer by number.

**CHECKPOINT: Cross-References Inserted**
- [ ] All 8 execution points verified
- [ ] Every reference uses principle number, not section name
- [ ] No principle text duplicated inline

---

## Phase 5: Scope Compliance Final Check and DRAFT Marking

### 5.1 Scope Compliance Final Check (Principle 24.4)

Re-verify that the assembled draft respects all four scope restrictions:

- [ ] Tool chain length ≤ 25
- [ ] All parameters within documented L1 ranges (or declared as Grade B gaps in YAML `grade-b-gaps`)
- [ ] No recursive self-invocation (the draft does not call itself)
- [ ] Single-session scope (draft is marked UNTESTED and valid only for current session until crystallized via L2-12)

### 5.2 DRAFT Marking (Principle 24.3)

Apply all three mandatory annotations:

**(a) In `run_log.md`** — already inserted at Phase 0.4. Verify still present and accurate.

**(b) In `result.md`** — add a Methodology Note section (to be written when `result.md` is finalized after execution):

```markdown
## Methodology Note

This task was executed using an agent-authored draft workflow (L2-Workflow-DRAFT),
not an expert-curated L2 skill.
- Draft workflow name: draft-[name]
- Feasibility grade: [A / B]
- Declared capability gaps: [list if Grade B; "none" if Grade A]
- Confidence assessment for each major result:
  - [Result 1]: [high / medium / low — with reason]
  - [Result 2]: [...]
- Recommended follow-up: If the draft workflow succeeded, Phase 2.5 post-execution
  self-assessment will evaluate T1 crystallization per Principle 25. If crystallized,
  the auto-generated L2 workflow will be available for future sessions with initial
  confidence LOW.
```

**(c) In the draft workflow document itself** — YAML header already has `skill-level: L2-Workflow-DRAFT`. Additionally, place a one-line notice immediately after the `---` closing delimiter:

```markdown
> **⚠️ DRAFT WORKFLOW** — Agent-authored; not yet expert-reviewed. Apply with Principle 26 capability-boundary caution.
```

### 5.3 Save Draft Workflow Document

Save to a session-scoped location (draft workflows are single-session per Principle 24.4):

- Recommended path: `./draft_workflows/draft-[name].md` in the current task's working directory (NOT in `skills/L2_workflows/` — that directory is for expert-curated content only).

If the task's crystallization trigger fires after execution and L2-12 produces a persistent version, that persistent version goes to `skills/auto-generated-skills/L2_workflows/` with `L2-Workflow-AUTO` level. The DRAFT version remains in the task directory as provenance.

**CHECKPOINT: DRAFT Marked and Saved**
- [ ] Scope compliance re-verified
- [ ] run_log.md draft notice present
- [ ] result.md Methodology Note template prepared (to be filled after execution)
- [ ] Draft workflow document saved with DRAFT notice after YAML
- [ ] Correct path: task directory, NOT main skill library

---

## Phase 6: Handoff to Execution

The draft workflow is now a complete, compliant document. Hand off to execution.

### 6.1 Pre-Execution Self-Check (Principle 1 meta-application)

Before invoking the first tool of the draft workflow, re-read the complete draft and confirm:
- [ ] All phase objectives are clear and non-overlapping.
- [ ] All CHECKPOINTs have concrete, testable conditions (not vague checks like "looks OK").
- [ ] Failure recovery actions reference tools and parameters that actually exist.
- [ ] The final deliverable is explicitly defined and traceable from Phase 1 input.

### 6.2 Execute the Draft Workflow

Proceed to execute the draft's Phase-by-Phase Execution Protocol. Each phase is executed as an ordinary task phase per L3 Chapters 1–7. The DRAFT marking does not suspend any L3 principle — all data integrity, file collection, and verification principles apply in full.

### 6.3 Post-Execution Reporting

After execution, write `result.md` including the Methodology Note template prepared in Phase 5.2(b). Confidence assessments must be concrete (e.g., "docking score ranking: high confidence; absolute binding affinity: low confidence per Principle 26.1 methodological precision table") — not generic hedges.

### 6.4 Post-Execution Self-Assessment Handoff

The agent MUST then execute the standard Phase 2.5 self-assessment (system prompt) with the understanding that this task used a draft workflow. Expected outcomes:

- **Successful Grade A execution** → T1 is almost certainly active (novel tool composition succeeded). Invoke L2-12 for crystallization.
- **Successful Grade B execution** → T1 is active; L2-12 will produce a skill with `feasibility-grade: B` and the gap list inherited from this draft's YAML.
- **Failed execution with systematic failure identified** → T5 may be active even though T1 is not; invoke L2-12 simplified path for T5.
- **Failed execution without systematic failure** → No crystallization. Record in run_log: `Draft workflow [name] executed but failed without systematic pattern. Draft discarded at session end. No skill generated.`

**FINAL CHECKPOINT: Draft Ready for Execution**
- [ ] Draft workflow document complete and compliant
- [ ] DRAFT markings in all three locations (run_log, result.md template, draft doc itself)
- [ ] Pre-execution self-check passed
- [ ] Execution entry point clear (Phase 1 of the draft)
- [ ] Phase 2.5 handoff plan recorded

---

## Common Failures & Recovery

| Failure | Likely Cause | Recovery |
|---------|-------------|----------|
| Novelty check reveals ≥ 70% match with existing L2 mid-authoring | Initial scan in Phase 0.1 was incomplete; expert workflow found after skeleton population | ABORT draft; use the matched L2 workflow; record in run_log that draft was aborted due to post-hoc novelty failure |
| Path closure fails in Phase 2.2 (dangling produce→consume edge) | Missing utility tool in chain (format conversion, chain extraction, residue mapping) | Insert the relevant L1 utility (e.g., `molclaw-extract-chains`, `molclaw-file-transfer`, residue mapper) as a bridging phase; re-verify closure |
| Tool chain length exceeds 25 | Over-ambitious single-workflow scope | Decompose into 2 sub-workflows, each authored independently via this protocol; the first sub-workflow's output becomes the second's input |
| Parameter outside L1-documented range and L1 SKILL.md has no "may extend" note | Task requires behavior outside validated bounds | Re-classify task as Grade B with explicit `grade-b-gaps: ["param X outside documented range Y"]` declaration; OR revise draft to use an in-range value even if suboptimal; OR refuse authoring if the out-of-range is central to the task (then it is Grade C, not Grade B) |
| Reference L2 skeleton doesn't fit observed trace structure | Paradigm misidentification in Phase 1.1 | Re-run Phase 1.1 with the actual anticipated trace; if mixed paradigm, pick the dominant paradigm per Phase 1.2; if truly novel paradigm (not A/B/C), record as methodological observation and proceed with closest-fit skeleton, flagging the mismatch in YAML `paradigm: "[closest-fit + novel-element: description]"` |
| Cross-reference insertion (Phase 4) finds no natural insertion point for a required principle | The draft workflow skipped an execution point where the principle applies (e.g., no count-change step but COUNT GATE required) | Re-examine the draft: either the principle is genuinely inapplicable (rare; document the exemption) or the draft is missing a phase that should be there (add it) |
| Draft execution reveals the plan was wrong (trace diverges from authored phases) | Plan-execution mismatch; real execution required mid-course correction | Allow the execution to adapt — the agent is not rigidly bound to its own draft. Record every divergence in run_log as a "Draft deviation: [what was authored] → [what was executed] — [why]". These deviations become prime T4 crystallization candidates if they produced better results |
| Context window insufficient to hold full draft plus execution | Complex task exhausting context during authoring | Apply simplified draft authoring: write only YAML, Applicability, Prerequisites, and an abbreviated Phase Protocol with tool sequence + key params (omit detailed CHECKPOINT descriptions, reference parent L2 by section instead). Mark `confidence: UNTESTED-ABBREVIATED` in YAML. Full elaboration deferred to future crystallization |
| Auto-generated skill with confidence ≥ MEDIUM already covers task | Phase 0.1 check missed the auto-skill index | Re-check `skills/auto-generated-skills/skill-index.md`; if a MEDIUM/HIGH auto-skill matches, ABORT draft authoring and load that auto-skill instead |

---

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| `draft_workflows/draft-[name].md` | Markdown, L2-Workflow-DRAFT structure | Execution phase (Phase 6); post-execution crystallization (L2-12, if T1 fires) | **A — MUST save** |
| `run_log.md` draft declaration block (Phase 0.4) | Appended header block | Audit; Phase 2.5 self-assessment | **A — MUST save** |
| `result.md` Methodology Note (Phase 5.2b) | Section in final report | User visibility per Principle 26.3 | **A — MUST save** |
| Draft deviation log entries (from Common Failures row on plan-execution mismatch) | Appended to run_log | T4 crystallization candidates for L2-12 | **B — SHOULD save** |

---

## Known Limitations

- **Novelty detection is tool-sequence-based, not semantic.** A draft workflow with the same tool sequence as an existing L2 but applied to a genuinely different problem class will be flagged as non-novel and aborted. Mitigation: if the agent believes the task is semantically distinct despite sequence match, record the rationale and consult user before abort.
- **Grade classification at Phase 0.2 is predictive, not empirical.** If execution reveals a Grade C condition (missing capability) that was not anticipated, the draft will fail partway. Recovery depends on Phase 2.5 picking up T5 or the agent honestly refusing to over-interpret partial results per Principle 26.3.
- **Parameter range checks rely on L1 SKILL.md completeness.** If an L1 SKILL.md omits a parameter's valid range, Phase 2.4 may silently pass an out-of-range value. Mitigation: when in doubt, default to the value used in the L1's code examples; flag any omitted range as a suggested L1 update.
- **Draft workflows do not benefit from prior T3 (recurring sub-workflow) learning within the same session.** If the agent independently composes the same sub-sequence across two drafts in one session, L2-12 T3 may fire — but within each draft, the repetition is invisible.
- **No automatic cost estimation.** Phase 0.2's "within session budget" check is qualitative. A draft that passes all checks may still exhaust compute in practice. Mitigation: when Phase 4 (MD / MMPBSA / ensemble) tools are in the chain, explicitly flag expected wall-clock in the YAML `expected-runtime-class: [fast / medium / slow / very-slow]`.
- **DRAFT status is session-local.** On platforms without persistent workspaces, drafts that do not crystallize via L2-12 are lost at session end. This is a feature for containment (untested drafts should not leak), not a bug. Mitigation: if a draft is valuable but did not fire a crystallization trigger, the agent can propose it to the user as a "candidate for human review and promotion to expert L2" in its Methodology Note.

---

## Provenance

- **Source:** L3 Chapter 8 Supplement, Principle 24 (all sections).
- **Companion workflows:** L2-00 (problem discovery, upstream producer of tasks that trigger this workflow), L2-12 (skill crystallization, downstream consumer of successful draft executions).
- **L3 principles referenced:** 1, 4–8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23.1a, 23.2, 24, 24.1, 24.2, 24.3, 24.4, 25 (T1 handoff), 26 (throughout), 26.1 (precision table), 26.3 (honest communication).
- **Relationship to other L2 workflows:** L2-13 is a META-workflow (like L2-00 and L2-12); it does not execute domain science itself. It authors a DRAFT L2 whose execution is governed by the same L3 principles as any expert-curated L2. The full autonomous discovery pipeline is:

  ```
  [User open-ended request]
       ↓
   L2-00 (Problem Discovery and Feasibility Triage)
       ↓  [user selects a candidate]
   L2-13 (Draft Workflow Authoring)        ← THIS WORKFLOW
       ↓  [draft executed]
   Ordinary task execution governed by L3 Chapters 1–7
       ↓  [post-execution Phase 2.5]
   L2-12 (Skill Crystallization)           if trigger T1/T2/T4/T5 fires
       ↓
   Persistent auto-generated skill
  ```

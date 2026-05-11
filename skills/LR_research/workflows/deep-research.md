---
name: deep-research
description: Execute autonomous multi-step deep research on any topic. Use when the user asks for comprehensive research, literature reviews, competitive analysis, topic deep-dives, or wants to understand a complex subject from multiple angles. Triggers on "deep research", "research on", "investigate", "literature review", "comprehensive analysis", "what do we know about", "summarize research on".
---

# Deep Research

Autonomous multi-step research that searches multiple sources, reads full content, synthesizes findings, and produces a structured report.

## When to Use

- User wants a thorough understanding of a topic (medical condition, drug, treatment, technology)
- User asks for a literature review or evidence summary
- User wants competitive or landscape analysis
- User wants to investigate an open question with multiple angles
- User asks "what does the research say about X"

## Research Strategy

### Step 1: Query Decomposition
Break the research question into 3–5 sub-questions covering:
- Core definition / mechanism
- Current evidence / state of the art
- Debates, limitations, or contradictions
- Clinical / practical implications (if medical)
- Recent developments (last 1–2 years)

### Step 2: Multi-Source Search
Run searches across complementary sources using the available search tools:

```python
# Use multi-search-engine for broad web coverage
# Use pubmed-search for peer-reviewed medical literature
# Use agent-browser to read full-text articles and retrieve content blocked by snippets
```

**Search order:**
1. PubMed (if medical/biomedical topic) — for peer-reviewed evidence
2. Multi-search-engine (Bing, Google, DuckDuckGo) — for guidelines, reviews, news
3. Wikipedia — for background and structured overviews
4. agent-browser — for reading full articles, PDFs, clinical guidelines

### Step 3: Source Evaluation
For each source note:
- Publication type (RCT, meta-analysis, guideline, review, news)
- Date (prefer sources within 5 years for medical topics)
- Authority (journal impact, organization credibility)
- Relevance to the specific sub-question

### Step 4: Synthesis
Synthesize across sources into a coherent narrative. Do NOT just concatenate summaries — identify:
- Points of consensus
- Contradictions or conflicting evidence
- Knowledge gaps
- Strongest evidence vs. weak/preliminary evidence

### Step 5: Structured Report
Produce a well-formatted Markdown report with:

```markdown
# [Topic] — Deep Research Report

## Summary
2–3 sentence executive summary of the key finding.

## Background
What is this? Core definitions, mechanisms, or context.

## Current Evidence
What does the research show? Organized by sub-question or theme.

## Key Debates / Open Questions
Where do experts disagree? What is still unknown?

## Clinical / Practical Implications
(For medical topics) What should clinicians or patients know?

## Recent Developments
Anything notable from the past 12–24 months.

## Sources
Numbered list of all sources with titles, URLs/DOIs, and dates.
```

## Medical Research Guidelines

When researching medical topics:
- **Prioritize evidence hierarchy**: Systematic reviews > RCTs > Cohort studies > Case reports > Expert opinion
- **Include safety information**: Drug interactions, contraindications, adverse effects
- **Note population specifics**: Pediatric vs. adult, special populations, comorbidities
- **Flag regulatory status**: FDA/EMA approval status, off-label use
- **Cite clinical guidelines**: NICE, AHA, ACC, IDSA, WHO guidelines where relevant
- **Distinguish mechanistic from clinical evidence**: Lab/animal data ≠ human evidence

## Depth Levels

Adapt depth to user request:
- **Quick overview** (user asks briefly): 3–5 sources, 1-page summary
- **Standard research** (default): 8–15 sources, full structured report
- **Comprehensive review** (user asks explicitly): 20+ sources, deep synthesis with evidence grading

## Example Execution

**User:** "Research the evidence for metformin use in longevity/anti-aging"

1. Decompose: mechanism of action → RCT evidence → observational data → safety profile → current trials
2. Search PubMed for "metformin longevity aging", "TAME trial metformin"
3. Search web for "metformin anti-aging clinical trials 2024"
4. Read key papers with agent-browser
5. Synthesize: strong mechanistic evidence, TAME trial ongoing, limited long-term human RCT data
6. Produce structured report with citations

---

## Drug Discovery Research Guidelines (MolClaw Integration)

When deep-research is invoked within a MolClaw computational drug discovery context, follow these additional guidelines on top of the general strategy above.

### Drug Discovery Search Strategies

Decompose the research need into domain-specific sub-questions:

- **Target validation:** Prioritize reviews and meta-analyses on target druggability, genetic validation (GWAS, OMIM associations), and clinical precedent. Search for: `"[target] drug target validation review"`, `"[target] genetic association disease"`.
- **Compound SAR:** Search for structure-activity relationship studies; extract IC50/Ki values, selectivity data, and pharmacokinetic profiles. Search for: `"[target] inhibitor structure-activity"`, `"[target] SAR potency selectivity"`.
- **Known binders as controls:** Retrieve experimentally validated binders with published binding data — these serve as positive controls for docking validation (supports Principle 9 cross-validation). Search for: `"[target] crystal structure ligand"`, `"[target] inhibitor IC50 Ki"`.
- **Method benchmarking:** When researching computational methods (docking, scoring, MD, MMPBSA), search for benchmark comparisons on the specific target class. Search for: `"[target class] molecular docking benchmark"`, `"MM-PBSA [target class] accuracy"`.
- **Patent landscape:** Use multi-search-engine to check patent databases (Google Patents) for freedom-to-operate context. Search for: `site:patents.google.com "[target] inhibitor"`.
- **Clinical pipeline:** Search for the target's clinical development status. Search for: `"[target] clinical trial inhibitor phase"`, or use multi-search-engine for ClinicalTrials.gov queries.
- **Experimental binding energy:** For MMPBSA/MMGBSA validation, search for experimentally measured ΔG, Kd, or Ki values. Search for: `"[target] binding affinity Kd Ki ITC SPR"`.

### Evidence Hierarchy for Drug Discovery

Adapt source prioritization for computational chemistry context:
1. **Peer-reviewed computational studies** on the same target with same methods — directly comparable benchmarks
2. **Experimental binding data** (ITC, SPR, X-ray co-crystal) — gold standard for validating computational predictions
3. **Review articles and meta-analyses** on the target class — broad context
4. **Patent filings** — prior art and freedom-to-operate signals
5. **Preprints and conference proceedings** — cutting-edge but unreviewed

### MolClaw Principle Compliance

All deep-research output within MolClaw context MUST follow these rules:

- **Category 3 labeling (Principle 10):** Every retrieved value is Category 3 information. Mark with ⚠️ LITERATURE VALUE. This does not change regardless of source quality.
- **Computation-first (Principle 13):** Literature NEVER replaces computation. Research findings inform computational design choices (seed selection, parameter tuning, validation baselines) but do not constitute computational evidence.
- **Citation format:** Every cited source must include: First Author, Year, Journal, PMID (if from PubMed) or DOI, and a one-sentence key finding summary.
- **Disagreement reporting (Principle 20):** If literature findings disagree with computational results, both must be reported with the discrepancy explicitly noted. Do not suppress either.

### Output Format for MolClaw Integration

When deep-research produces output as part of a MolClaw execution:

1. Save the research report as `stepNN_LR_[topic]_research.md` following MolClaw file naming convention.
2. The research report is an **intermediate artifact** — its key findings must be integrated into `result.md` per Phase 2 step 4. It is not a standalone deliverable.
3. Record the research execution in `run_log.md` Tool Call Sequence using `[LR] deep-research` prefix.
4. In the structured report, add a "Relevance to Current Task" section that explicitly connects findings to the computational workflow.

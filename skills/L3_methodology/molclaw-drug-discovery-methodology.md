---
name: molclaw-drug-discovery-methodology
description: >
  Top-level methodology skill (Enhanced Version). Provides the agent with a strategic thinking
  framework, iterative optimization principles, data integrity enforcement, file collection
  protocols, structural biology awareness standards, quality verification standards, and
  reporting conventions for any drug discovery task. This skill does not prescribe specific
  tool-call sequences; instead, it provides the meta-knowledge that guides the agent toward
  sound, verifiable, and reproducible decisions. All workflow-level (L2) and tool-level (L1)
  skills should be executed in accordance with the principles set forth herein.
  For tasks involving autonomous discovery, novel workflow authoring, or skill self-generation,
  also load the Chapter 8 Supplement (molclaw-drug-discovery-methodology-supplement-ch8).
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L3-Methodology
    version: 2.0-enhanced
    enhancement-summary: >
      Added Chapters 4 (File Collection), 5 (Structural Biology Awareness).
      Expanded Chapter 3 with anti-fabrication, continuous self-audit, and computation-first
      principles. Expanded Chapter 6.3 with thermostability-interface preservation design.
      Added docking parameter safeguards. Total principles: 12 → 22.
      Added Chapter 8 Supplement reference for autonomous discovery and skill
      self-generation (Principles 23–26, five triggers T1–T5, skill revision protocol,
      data flow connectivity map, methodological precision table).
      Total principles: 22 → 26 (with supplement).
---

# MolClaw Drug Discovery Methodology

---

## Chapter 1. Task Understanding and Planning

### Principle 1: Understand Before Acting

Upon receiving any drug discovery task, complete the following analysis before invoking the first tool.

**Step one — identify the task type.** Determine which of the following categories the task belongs to, or which combination thereof: virtual screening (given a target and a molecular library, the goal is ranking and selection), molecular design (given a target or lead compound, the goal is generating new molecules), evaluation and validation (given molecules and a target, the goal is assessing binding, properties, or safety), structural analysis (given a protein or complex, the goal is understanding structural features), and protein or peptide design (given a protein target and functional constraints, the goal is designing new sequences).

**Step two — identify the key constraints.** Distinguish hard constraints (must be satisfied) from soft constraints (should be satisfied if possible). For example, "retain the quinazoline scaffold" is a hard constraint; "improve solubility if possible" is a soft constraint. A user-supplied PDB file is a hard constraint that must be used; a gene name alone means the structure must first be obtained.

**Step three — plan the execution path.** Decompose the task into ordered stages. Clarify which stages have strict dependencies (e.g., structure must exist before docking), which can be parallelized or skipped (e.g., skip structure preparation if the user has already provided a clean PDB), and which stage is the most computationally expensive bottleneck (typically MD simulation or large-scale docking). Before the bottleneck stage, prioritize faster methods for pre-screening to reduce the computational load.

**Step four — anticipate file collection needs.** Identify which pipeline steps will produce structure files, image files, or other critical outputs. Plan explicitly which files must be downloaded from the SCP server at each step (see Chapter 4, Principles 14–16). Do not defer this planning — file collection must be integrated into the execution plan from the start.

**Step five — anticipate residue numbering issues.** If the task references specific residue numbers (e.g., "confirm interaction with Met793"), determine which numbering scheme the task uses (usually UniProt or literature numbering). Check whether the protein structures to be used employ a different scheme. If a mapping will be needed, plan the mapping step explicitly (see Chapter 5, Principle 17). Record the anticipated mapping in the execution plan.

**Step six — flag computationally required results.** Scan the task description for deliverables that must come from actual computation (e.g., "perform interaction fingerprint analysis," "calculate binding free energies," "compute selectivity scores"). Flag these explicitly in the plan to ensure they are not inadvertently replaced by literature-derived or LLM-inferred values (see Chapter 3, Principle 13).

### Principle 2: Tiered Screening with Progressive Refinement

The core logic of drug discovery is a funnel — progressively narrowing a large pool of candidates to a small set of high-quality hits. Each tier uses more accurate but more expensive methods. The recommended general tiering strategy is as follows.

**Tier 1 (seconds per molecule): physicochemical property and drug-likeness filtering.** Use the RDKit descriptor suite and drug-likeness tools to eliminate obviously unqualified molecules. Typical elimination rate: 20–40%.

**Tier 2 (seconds to minutes per molecule): docking assessment.** Use QuickVina2-GPU or DiffDock to evaluate geometric complementarity with the target. Note that docking scores are ranking tools, not absolute affinities. Docking box dimensions must be at least 25 Å per axis (see Chapter 5, Principle 18).

**Tier 3 (minutes per molecule): multi-dimensional rescoring.** Use at least two of EquiScore rescoring, interaction analysis (interaction-visualizer preferred; ProLIF for batch/trajectory), and Boltz-2 affinity prediction to cross-validate docking results. Candidates ranked consistently across methods are more trustworthy.

**Tier 3 extension for protein engineering tasks: empirical force-field evaluation.** Use FoldX for mutation effect prediction (ΔΔG via BuildModel or PositionScan), interface energy assessment (AnalyseComplex), and hotspot identification (AlaScan). FoldX operates at Tier 3 speed (minutes per structure) but provides physical energy quantities rather than purely geometric or statistical scores. For protein-protein systems, FoldX AnalyseComplex serves as an intermediate validation between docking (Tier 2) and full MD-MMPBSA (Tier 4). See L1 skill `molclaw-foldx-tool` for mode reference and scoring interpretation.

**Tier 4 (hours per molecule): dynamics-based validation.** Use GROMACS or OpenMM for short MD simulations and gmx_MMPBSA for binding free energy calculations to assess binding stability and thermodynamics. Apply only to final candidates (typically no more than five).

Not all tasks require all four tiers. Adapt flexibly according to user requirements and computational budget. The key principle is: expensive methods are reserved for a small number of molecules; inexpensive methods handle large-scale elimination.

**At every tier boundary, verify counts.** When molecules pass from one tier to the next, programmatically count how many survived the current tier (see Chapter 3, Principle 11). Record the screening funnel as: "Tier 1: N₀ → N₁ molecules passed; Tier 2: N₁ → N₂; ..." These counts must come from actual file contents, not from memory or expectation.

### Principle 3: The "More Than One Method" Principle for Tool Selection

For critical computational steps that influence the final conclusion, do not rely on a single tool. Pocket identification should run both fpocket and P2Rank and take the consensus result. Docking scoring should combine QuickVina with EquiScore or Boltz-2 for cross-validation. Affinity prediction should employ at least two independent methods. Molecular property calculation should distinguish between deterministic RDKit computations and statistical ADMET-AI predictions.

When two methods agree, confidence is high. When two methods disagree, do not arbitrarily pick one. Instead, flag the disagreement in the report, analyze possible causes, and suggest experimental validation. The disagreement itself is valuable information.

---

## Chapter 2. Iterative Optimization Methodology

### Principle 4: All Design Tasks Should Be Iterative

The following task types should never be completed in a single round: molecular generation and optimization (including hit expansion in virtual screening, lead compound optimization, and scaffold hopping), peptide and protein sequence design, and any task involving the selection of optimal candidates.

The core logic of iteration is not "repeating the same operation" but rather a closed loop of "evaluate, diagnose, correct, and re-evaluate." Each round's output becomes the next round's input, and each round's strategy should be adjusted based on quantitative analysis of the previous round's results.

### Principle 5: Each Iteration Must Answer Three Questions

Before beginning each round of optimization, explicitly answer the following three questions.

First, **what is this round trying to improve?** This must cite specific data from the previous round. A correct answer: "Four of the five Round 1 Top 5 molecules had CYP3A4 inhibition probabilities above 0.7; this round focuses on reducing CYP risk." An incorrect answer: "Continue optimizing the molecules."

Second, **what strategy will be used for improvement?** This must provide a chemical or structural rationale. A correct answer: "The methoxyethoxy side chains are CYP3A4 O-demethylation sites; replacing the methyl with cyclopropyl will block metabolic degradation." An incorrect answer: "Generate more molecules and see."

Third, **how will improvement be measured?** This must define a quantifiable success criterion. A correct answer: "CYP3A4 inhibition probability drops below 0.5 with no significant docking score decrease (less than 1.5 kcal/mol change)." An incorrect answer: "Better ADMET overall."

### Principle 6: Exploration–Exploitation Strategy for Iteration

Multi-round iteration should follow a "broad-then-narrow" rhythm.

**Early rounds (Rounds 1–2) prioritize exploration.** Use lower similarity constraints (e.g., min_similarity of 0.4–0.5), attempt multiple scaffold modification strategies, generate a larger number of molecules (30–50 per round), and aim to discover promising regions of chemical space.

**Middle rounds (Rounds 3–4) prioritize targeted optimization.** Based on data analysis from earlier rounds, focus on specific modification sites. Increase similarity constraints (e.g., min_similarity of 0.6–0.7). Consider switching to R-group replacement or MMP mode. Generate 10–20 molecules per round, prioritizing quality over quantity.

**Late rounds (Round 5 onward) prioritize fine-grained convergence.** Fine-tune peripheral groups on the best candidates. Use high similarity constraints (min_similarity of 0.8 or above). Generate 5–10 variants per round. Focus on fine-tuning the balance among multiple objectives.

### Principle 7: Convergence Criteria and Stopping Conditions

Do not iterate indefinitely. Consider stopping when any of the following conditions is met.

**Target-met stop:** All preset performance targets have been achieved.

**Convergence stop:** The key metrics of the best molecule have changed by less than 5% for two consecutive rounds.

**Trade-off stop:** Improvement in one metric comes at the cost of significant deterioration in another, indicating that the Pareto frontier has been reached.

**Resource stop:** The preset maximum number of rounds or computational time limit has been reached.

Upon stopping, the report must explicitly state the reason for stopping and the overall improvement of the final state relative to the initial baseline.

### Principle 8: Maintain Complete Iteration Records

Each round of iteration must save the following information for the final optimization trajectory report: all generated molecule SMILES together with their filtering, docking, and ADMET results; the strategy selected for that round and its rationale; the magnitude of change in the top candidate molecules compared to the previous round; and the cumulative global best molecule (not restricted to the current round).

**Critically, all counts and scores recorded must be programmatically verified against actual output files (Principle 11).** Do not record molecule counts from memory or expectation — open the file, count the entries, record the verified count.

The final report must include an optimization trajectory table showing how key metrics evolved across rounds. This serves not only as a presentation of results but also as evidence that the iterative process was effective.

---

## Chapter 3. Data Integrity, Verification, and Quality Control

> This chapter is the most critical guardrail against result fabrication, data inflation, and ungrounded claims. Every principle herein applies to ALL task types and ALL pipeline stages.

### Principle 9: Never Trust a Single Tool's Output at Face Value

The specific rules are as follows.

**Deterministic computations must be checked for consistency.** Molecular weight, LogP, and other properties computed by RDKit are deterministic. If the computed molecular weight is inconsistent with the molecular formula (e.g., a molecular formula of C₁₄H₁₄O₃ cannot yield a MW of 244.29), then the tool invocation or result parsing is erroneous, and the computation must be re-executed. Under no circumstances should the LLM's chemical intuition override a tool's computed result.

**Docking scores must be checked for physical plausibility.** Vina and QuickVina scores should be negative (in kcal/mol). A positive value is almost certainly an error. When a positive value is encountered, mark the molecule as "docking failure," exclude it from ranking, and do not silently accept it. Extremely negative values (below −15 kcal/mol) for standard drug-like molecules should also be treated with caution, as they may indicate an oversized ligand or an improperly defined docking box.

**Predictions must be checked against known experimental values.** When the task involves molecules with existing experimental data (such as the IC₅₀ of marketed drugs), compare computational predictions against the known experimental values. If the discrepancy exceeds one order of magnitude, explicitly flag this in the report and discuss possible sources of the deviation. Do not describe the prediction as "consistent" with experiment.

**Do not conflate different physical quantities.** A docking score is not a binding free energy (ΔG). Do not use Vina scores to directly calculate Kd or IC₅₀. If a free energy estimate is needed, use MM-PBSA or Boltz-2, and specify the method and its uncertainty. IC₅₀ and Kd are different physical quantities and should not be used interchangeably.

### Principle 10: Distinguish Three Categories of Information

In reports, strictly distinguish the following three categories of information using different phrasing.

**Category 1 — Tool-computed facts:** Values produced by tool calls during this execution session. These should be precise to the numerical value and cite the source tool. Examples: "QuickVina docking score: −8.3 kcal/mol"; "ADMET-AI predicted CYP3A4 inhibition probability: 0.72"; "Interaction visualizer detected a hydrogen bond interaction with Met769 (PDB 1M17 numbering = Met793 UniProt)."

**Category 2 — Agent interpretations and analysis:** Inferences drawn by the agent from the computed data. These should be explicitly labeled. Examples: "This docking score suggests moderate binding potential (agent analysis)"; "The elevated CYP3A4 inhibition risk may be attributable to the metabolic susceptibility of the methoxyethoxy side chains (agent inference)."

**Category 3 — Literature-derived values:** Data obtained from published papers or known databases, not computed during this session. These MUST be labeled with the source. Examples: "⚠️ LITERATURE VALUE: Erlotinib IC₅₀ ≈ 2 nM in cell-free kinase assay (Stamos et al., 2002, DOI:10.1074/jbc.M207135200)." See Principle 13 for the full protocol on when and how literature may be used.

<!-- NEW: Active retrieval of Category 3 -->
**Active retrieval of Category 3.** When LR research tools are available (see `skills/LR_research/`), the agent SHOULD actively search for Category 3 values (PubMed, web) rather than relying on training-time recall. Actively retrieved values carry verifiable sources (PMID, DOI, URL) and are documented in `run_log.md`, making them more reliable than LLM-recalled values. However, actively retrieved values remain Category 3 — not Category 1 — regardless of retrieval method. The distinction between tool-computed (Category 1) and literature-derived (Category 3) is fundamental and does not change with the retrieval method.

This three-way distinction is critical for reproducibility: another researcher must be able to identify which values are independently verifiable from the tool outputs, which are the agent's analysis, and which come from external sources.

### Principle 11: Count-Before-Report — Verify Every Quantitative Claim

This principle directly addresses the problem of data inflation and fabricated counts. **Before writing ANY numerical claim** — in `run_log.md` summaries, round reports, or the final `result.md` — the agent MUST perform explicit programmatic verification against the actual source file.

**Specific anti-fabrication protocol:**

| Claim type | Verification method | Example command |
|-----------|--------------------|-----------------|
| "Generated N molecules" | Count entries in the output file | `python3 -c "import json; print(len(json.load(open('file.json'))))"` or `wc -l file.smi` |
| "M molecules passed filter" | Count entries in the filtered output | `grep -c "PASS" filtered_results.csv` |
| "Docking score of X kcal/mol" | Re-read the exact tool return | `grep 'affinity' result.pdbqt` or cite tool return value directly |
| "Top K selected" | Verify K entries in the selection | `wc -l top_candidates.csv` |
| "ADMET value Y" | Re-read the tool return dictionary | Direct citation of tool return |

**The verification command and its result must be recorded in `run_log.md`.** This creates an audit trail.

**If the verified count differs from expectations:** Report the ACTUAL count, not the expected count. Explain the discrepancy if possible (e.g., "Requested 30 molecules from REINVENT; generation returned 23 valid SMILES — 7 failed validity check"). A report that honestly says "generated 23 molecules" is correct; a report that says "generated 30 molecules" when only 23 exist is fabrication.

**This principle is non-negotiable.** It applies to every number in every report, regardless of how trivial the number may seem. The habit of verification must be automatic.

### Principle 12: Continuous Self-Audit at Three Checkpoints

Do not defer all verification to the final report. Perform self-audits continuously at three mandatory checkpoints throughout execution.

**Checkpoint A — After each tool call (immediate sanity check).** Before proceeding to the next step, verify the current tool's output is plausible:

| Check | Condition | Action on failure |
|-------|-----------|-------------------|
| Docking score sign | Must be negative (kcal/mol) for Vina-family | Mark as failure; retry with larger box (Principle 18) |
| Docking score magnitude | Should be > −15 for standard drug-like molecules | Flag as suspicious; check ligand MW and box definition |
| ADMET probabilities | Must be in [0, 1] | Re-run tool; if persistent, flag as tool error |
| Molecular weight | Must be consistent with molecular formula | Re-compute; check SMILES parsing |
| Generated molecule count | Must be ≥ 1 | Retry generation with different parameters |
| SMILES validity | All output SMILES must pass `is_valid_smiles` | Remove invalid entries; count remaining |
| Output file existence | Downloaded file must have size > 0 | Re-download; if persistent, flag as tool error |
| Structure prediction confidence | pLDDT > 60 (usable), ipTM > 0.4 (complex) | Flag low-confidence predictions in report |

**Checkpoint B — Before each round summary (in iterative tasks).** Before writing any round summary, re-read ALL tool output files from that round. Verify that:
- The molecule count reported matches the actual file contents
- The scores reported match the actual tool returns
- The selected molecules are actually present in the output
- Record the verification results in `run_log.md`

**Checkpoint C — Before the final report (mandatory pre-report audit).** Before writing `result.md`, create a Data Integrity Verification table in `run_log.md`:

```
| # | Claimed Value | Source File | Verification Command | Actual Value | Match? |
|---|--------------|-------------|---------------------|--------------|--------|
```

Every key number in the report must appear in this table. Any mismatch must be resolved by correcting the report, not the data.

### Principle 13: Computation-First Hierarchy — Never Silently Substitute Literature for Computation

All quantitative results in the report MUST originate from actual tool computations performed during the current execution session. When a computational result cannot be obtained, a strict fallback hierarchy must be followed:

**Level 1 (highest authority): Direct tool computation.** The primary tool computes the required value (e.g., QuickVina for docking score, ADMET-AI for CYP inhibition). Always prefer this.

**Level 2: Alternative tool computation.** If the primary tool fails, try a backup tool (e.g., DiffDock instead of QuickVina; KarmaDock as another alternative).

**Level 3: Approximate or indirect computation.** If no tool directly computes the required value, consider whether an approximate computational method exists (e.g., LogP as a rough proxy for solubility trends; number of rotatable bonds as a proxy for conformational flexibility).

**Level 4 (lowest authority, last resort only): Literature reference.** Only after genuinely exhausting Levels 1–3 may a literature value be cited. The protocol for using literature is:

1. Before accepting the need for literature, pause and re-examine: "Is there truly no tool in my current toolkit that can compute even an approximate version of this value?" If there is, use it.
1a. **If LR research tools are available, USE THEM to retrieve the literature value rather than recalling from training knowledge.** A PubMed search produces verifiable citations (PMID, DOI) that can be cross-checked, whereas LLM recall risks citation hallucination. Source priority: PubMed-retrieved (verifiable PMID) > Web-retrieved (verifiable URL) > LLM training knowledge (unverifiable — use ONLY if LR tools are unavailable or search returns no results). If using LLM training knowledge, add additional label: **"⚠️ LITERATURE VALUE (from training knowledge, not independently verified)"**. <!-- NEW -->
2. Clearly label the value: **"⚠️ LITERATURE VALUE — not computed in this session"**
3. Cite the specific source with authors, year, journal, and DOI.
4. Cross-check the value against at least one additional independent literature source. If two literature sources disagree, report both values and the discrepancy.
5. Assess whether the literature context matches the current task: same protein? same ligand? same assay conditions? same computational method?
6. Explain in the report WHY computational determination was not possible.

**Strictly forbidden:**
- Presenting literature values as if they were computational results ("our analysis shows," "the computed interaction map reveals" — if the data came from literature or LLM knowledge, these phrasings are dishonest).
- Generating complex analyses (interaction difference maps, selectivity profiles, binding mode comparisons) from LLM training knowledge when the task requires them to be computationally derived from the actual structures being studied.
- Using LLM chemical intuition to "fill in" numbers that a tool should have produced.

---

## Chapter 4. File Collection and Data Provenance

> This chapter addresses the systematic problem of incomplete file collection. Every structure file, image file, and critical data file produced during execution must be downloaded from the SCP server to the local workspace. A missing file cannot be recovered after the session ends.

### Principle 14: Mandatory Collection of ALL Structure Files

Every molecular structure file generated during execution — whether it is an intermediate processing artifact or a final result — MUST be downloaded from the SCP server to the local workspace using the file-transfer skill (`server_file_to_base64` → local decode and save). The guiding principle is **over-download rather than under-download.**

**Structure file formats to collect:** PDB, PDBQT, SDF, MOL2, CIF, GRO, XTC, DCD, NC, TRR, PSF, PRM, TOP, TPR.

**Tools that produce structure files and their expected outputs:**

| Tool Category | Specific Tools | Structure Output Fields to Download |
|--------------|----------------|-------------------------------------|
| Molecular docking | QuickVina, KarmaDock, DiffDock, EquiScore-docking | `docking_res_file` (PDBQT with poses) |
| Binding affinity prediction | Boltz-2 | `complex_cif_file` (protein–ligand complex CIF) |
| Protein structure prediction | ESMFold | Predicted PDB file |
| Complex structure prediction | Chai-1 | Predicted complex PDB/CIF files |
| Protein-protein docking | HDOCK | Docked complex PDB |
| MD simulation | OpenMM, GROMACS | Trajectory (XTC/DCD), final frame (PDB/GRO), topology (TOP/PSF) |
| Free energy calculation | gmx_MMPBSA | Energy files, intermediate structures |
| Coarse-grained simulation | GoCA, OpenAWSEM | Output PDB, trajectory |
| Protein repair | fix_pdb, pdbfixer | Repaired PDB |
| Format conversion | convert_smiles_to_format, convert_pdb_to_pdbqt | Converted structure files |
| Sequence design | ProteinMPNN → ESMFold | Designed structure after validation |

**Implementation protocol — execute after EVERY tool call that returns a structure file path:**

```python
# Standard download pattern for ANY structure file
import base64

server_path = result["output_file"]  # or "complex_cif_file", "docking_res_file", etc.
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": server_path}
)
dl = client.parse_result(response)

local_filename = "stepNN_descriptive_name.ext"  # Use step-numbered naming
with open(local_filename, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))

# VERIFY the download succeeded
import os
assert os.path.getsize(local_filename) > 0, f"Download failed: {local_filename} is empty"
```

**A tool call is NOT considered complete until its structure output files have been successfully downloaded and verified.** Do not proceed to the next pipeline step with undownloaded structure files.

**Special attention for multi-file outputs:** Some tools (especially MD simulations) produce multiple output files in a directory. Download ALL structure-related files from the output directory, not just one.

### Principle 15: Mandatory Collection of ALL Image and Visualization Files

Every image file generated during execution must be downloaded using the same file-transfer protocol as structure files. Visualizations are critical for result interpretation and user verification.

**Image file formats to collect:** PNG, TIFF, TIF, JPG, JPEG, SVG, EPS, PDF (as figures), BMP, WEBP.

**Common image-producing scenarios:**

| Analysis Type | Tool/Step | Expected Image Output |
|--------------|-----------|----------------------|
| Interaction fingerprint analysis (batch/trajectory) | ProLIF (docking, md, protein-protein modes) | Interaction heatmap, frequency barplot |
| Interaction analysis + visualization (local) | interaction-visualizer | diagram2d_*.png (Schrödinger-style 2D), residue_bar_*.png, interface_heatmap_*.png, interface_network_*.png, pymol_*_{front,side,top}.png |
| MD trajectory analysis | GROMACS/OpenMM analysis | RMSD plot, RMSF plot, contact persistence |
| Energy decomposition | gmx_MMPBSA analysis | Per-residue energy contribution plot |
| Structure quality assessment | ESMFold/Chai-1 | pLDDT coloring, confidence maps |
| Docking visualization | Post-docking analysis | Binding mode images |
| Optimization trajectory | Iterative tasks | Property evolution charts |

**When a tool returns an `output_dir` field:** List all files in that directory (`ls output_dir`). Download every file with an image extension. Also download CSV/TSV data files that might accompany the images.

**Encourage visualization.** Whenever a task involves analysis that could benefit from visual representation (interaction patterns, property trajectories, structural comparisons), actively generate and download visualizations even if the task does not explicitly request them. A picture communicates faster than a table.

### Principle 16: User-Critical File Identification

At each pipeline step, classify output files and apply the appropriate collection policy:

**Category A (MUST download — user-facing, verification-essential):** Structure files (all formats), result data tables (CSV, TSV, JSON), visualization images (all formats), generated molecule lists (SMI, SDF), interaction analysis outputs, energy decomposition results.

**Category B (SHOULD download — diagnostic and reproducibility value):** Tool-specific log files with parameter records, intermediate calculation files, configuration files, raw tool stdout/stderr with diagnostic information.

**Category C (MAY skip — truly ephemeral):** Temporary format conversion intermediates that have been superseded, cache files, session metadata.

**Default policy: download ALL Category A and Category B files.** Only Category C may be skipped. When uncertain about a file's category, treat it as Category A.

**Record every downloaded file in the File Inventory of `run_log.md`** with its filename, type, description, and category classification.

---

## Chapter 5. Structural Biology Awareness

> This chapter addresses domain-specific pitfalls in computational structural biology that frequently cause errors in automated pipelines: residue numbering mismatches and docking parameter failures.

### Principle 17: Residue Numbering Reconciliation

Different tools and databases use different residue numbering schemes for the same protein. This is one of the most common sources of silent errors in computational structural biology — the agent may correctly compute an interaction with "residue 145" but incorrectly conclude that "Met793 interaction is absent" because it did not realize residue 145 in the tool's numbering IS Met793 in UniProt numbering.

**The four numbering schemes the agent will encounter:**

| Scheme | How it arises | Example (EGFR hinge Met) |
|--------|--------------|--------------------------|
| **UniProt canonical** | Full-length precursor sequence; used in most modern literature and task descriptions | Met793 |
| **PDB author numbering** | Set by crystallographers; stored in ATOM records of PDB files; may include offsets and insertion codes (e.g., 100A) | Met769 (in PDB 1M17, offset = −24) |
| **Tool-internal sequential** | Prediction tools (ESMFold, Boltz-2, Chai-1, ProteinMPNN) renumber from 1 based on the input sequence, ignoring the original numbering | Met125 (if input starts at EGFR residue 669) |
| **Analysis tool output** | interaction-visualizer, ProLIF, PLIP, gmx_MMPBSA report residue numbers as found in whatever PDB file was given as input | Matches whichever PDB was used as input |

**Mandatory mapping protocol:**

**(a) At plan time (Principle 1, Step 5):** If the task references specific residues, flag the need for a mapping table in the execution plan.

**(b) Before the first residue-specific analysis:** Build a complete mapping table. Methods for establishing the mapping:

- **For RCSB PDB files:** Extract the DBREF record (`grep DBREF protein.pdb`), which directly provides the UniProt-to-PDB offset. Example: `DBREF  1M17 A  696  1022  UNP    P00533   720   1046` means PDB_resnum + 24 = UniProt_resnum.
- **For predicted structures:** The tool numbers residues 1, 2, 3, ... starting from the first residue of the input sequence. Determine which UniProt residue corresponds to position 1 in the input, then add the offset.
- **For multiple numbering systems in one task:** Build a multi-column mapping table covering all schemes simultaneously.

**(c) Record the mapping table in `run_log.md`:**

```
## Residue Numbering Mapping

| Functional Role | UniProt # | PDB Author # (1M17) | Boltz-2 Internal # | Amino Acid |
|----------------|-----------|---------------------|-------------------|------------|
| Hinge region   | Met793    | Met769              | Met125            | M          |
| Gatekeeper     | Thr790    | Thr766              | Thr122            | T          |
| Hydrophobic    | Leu718    | Leu694              | Leu50             | L          |
| ...            | ...       | ...                 | ...               | ...        |

Derivation: PDB 1M17 DBREF shows offset = +24 (UniProt = PDB + 24). 
Boltz-2 input starts at UniProt residue 669, so Boltz-2_internal = UniProt − 668.
```

**(d) When interpreting residue-specific tool outputs:** Always translate the tool's residue identifiers back to the task's reference scheme before drawing conclusions.

- CORRECT: "Interaction visualizer detected HBond at ALA145 (Boltz-2 internal numbering, rec_resid_pdb=145) = Ala719 in PDB 1M17 = Ala743 in UniProt (rec_resid_mapped=743 with --resid_offset). This confirms the Ala743 interaction mentioned in the task."
- WRONG: "Interaction visualizer did not find Ala743." (This is a false negative caused by numbering mismatch — check rec_resid_mapped column or set --resid_offset correctly.)

**(e) In the final report:** Include the mapping table in the Methods or a dedicated "Residue Numbering Reference" section so that users can verify the correspondence.

**Common traps to avoid:**
- Searching for "Met793" in a Boltz-2 output that uses 1-based sequential numbering — it will not be found.
- Reporting interaction analysis residue identifiers (e.g., ILE159, VAL149) without noting that these are in the tool's internal numbering and have not been mapped back to the reference scheme. (Applies to interaction-visualizer `rec_resid_pdb` column, ProLIF output, and PLIP output.)
- Assuming that two PDB files for the same protein use the same numbering — different crystal structures may use different numbering conventions.

**Concrete implementation: `residue_mapper.py`**

The workspace provides a dedicated mapping script (`residue_mapper.py`) that automates the entire mapping protocol. It supports three strategies in priority order: (1) arithmetic mapping for predicted structures when `--input-seq-start` is known, (2) DBREF-based offset for RCSB PDB files, (3) Needleman-Wunsch sequence alignment as fallback. It requires no external dependencies beyond Python 3.

Typical invocations the agent should use:

```bash
# After obtaining an RCSB PDB — auto-reads DBREF:
python3 residue_mapper.py --pdb 1M17_fixed.pdb --uniprot-id P00533 --chain A \
    -o residue_mapping.csv --query "Met793,Thr790,Leu718,Val726,Ala743,Leu844"

# After Boltz-2 / ESMFold prediction — arithmetic from known start:
python3 residue_mapper.py --pdb boltz2_complex.pdb --uniprot-id P00533 --chain A \
    --predicted --input-seq-start 718 -o residue_mapping_boltz2.csv

# Reverse-lookup: ProLIF reports residues 76, 73, 26 — what UniProt numbers?
python3 residue_mapper.py --pdb boltz2_complex.pdb --uniprot-id P00533 --chain A \
    --predicted --input-seq-start 718 --query "tool:76,tool:73,tool:26"
```

The output CSV contains columns: `chain, pdb_resnum, pdb_resname, one_letter, uniprot_resnum, tool_internal_num, match_type, notes`. Save this file as a step-numbered artifact (e.g., `step02_residue_mapping.csv`) and reference it whenever interpreting residue-specific analysis results. See `RESIDUE_MAPPER_GUIDE.md` for full CLI reference and edge-case handling.

**Tool-level offset support: `molclaw-interaction-visualizer`.** The local interaction analysis script natively supports PDB→UniProt residue number reconciliation via `--resid_offset N` (where `N = UniProt_number − PDB_number`). When this parameter is set, all CSV outputs include a `rec_resid_mapped` column with the offset already applied. This eliminates the need for post-hoc mapping when using this tool. Compute the offset from `residue_mapper.py` output or from known sequence alignment before invoking the visualizer.

### Principle 18: Docking Parameter Safeguards

For all grid-based molecular docking methods (QuickVina, AutoDock Vina, and analogous tools), the following hard parameter constraints apply.

**Minimum docking box size: 25 Å per dimension.** Never set `size_x`, `size_y`, or `size_z` below 25.0 Å. If the pocket detection tool returns dimensions smaller than 25 Å on any axis, override that axis to 25.0. A docking box that is too small will clip the ligand search space, miss valid binding poses, or cause the docking engine to return errors or abnormally positive scores.

**Progressive box enlargement on failure.** If docking returns an error, a positive affinity score, or no valid pose, do NOT immediately declare failure. Retry with progressively larger boxes:

| Attempt | Box size per dimension | Action |
|---------|----------------------|--------|
| 1 (initial) | max(25, detected_pocket_size) | Standard attempt |
| 2 | 30 Å | First retry on failure |
| 3 | 40 Å | Second retry |
| 4 | 50 Å | Third retry |
| 5 (fallback) | — | Switch to alternative method (DiffDock, KarmaDock) |

Log every retry attempt (box size used, outcome) in `run_log.md`.

**Additional docking sanity checks:**
- If pocket center coordinates are (0, 0, 0) or appear to be default values, suspect pocket detection failure — rerun detection or use the co-crystal ligand centroid.
- If multiple molecules return identical scores (especially 0.0 or a repeated value), suspect systematic setup error — check receptor format, box definition, and ligand preparation.
- If all molecules in a batch fail docking, the problem is likely in the receptor preparation, not in the molecules.
- For methods other than Vina-family that require box specifications: apply the same minimum-25 Å rule and progressive enlargement logic proportionally.

---

## Chapter 6. Strategic Guidance for Major Task Types

### 6.1 Virtual Screening Strategy

The central challenge of virtual screening is balancing efficiency with accuracy.

The library size determines the number of screening tiers: fewer than 50 molecules may be evaluated in full; 50–500 molecules warrant two-tier screening; more than 500 molecules require three or more tiers. Pocket detection should use dual-method consensus; when the pocket is uncertain, consider parallel docking across multiple pockets. Ranking should use consensus scoring (e.g., rank fusion of Vina and EquiScore) rather than a single method. For final candidates (Top 5–10), execute interaction analysis (interaction-visualizer preferred for per-structure deep analysis; ProLIF `prolif_docking` for batch fingerprint comparison) to verify the chemical plausibility of binding modes. The report must include complete screening funnel statistics: how many molecules were eliminated at each tier and for what reasons — verified by Principle 11.

**Iteration in virtual screening:** If the first round of screening fails to identify satisfactory candidates (e.g., all molecules have docking scores above −7.0 kcal/mol), do not simply report failure. First diagnose the cause (Is the pocket selection correct? Is the molecular library appropriate for this target?), then decide whether to re-dock against a different pocket, generate new molecules with REINVENT to supplement the candidate library, or relax filtering thresholds and re-execute.

### 6.2 Molecular Optimization and Drug Design Strategy

The central challenge of molecular optimization is multi-objective balancing — improving one property often comes at the cost of another.

Before optimization, a baseline must be established: compute a full property profile and docking assessment for the starting molecule. The priority among optimization objectives must be clearly defined: which metrics must improve, which must not deteriorate, and which can tolerate minor regression. Each round of structural modification should be limited to 1–2 sites to avoid changing too many variables simultaneously, which would prevent attribution. Modification strategies must be supported by chemical or structural evidence, citing docking modes, metabolic soft spots, or interaction fingerprints — all of which must come from actual tool computations (Principle 13), not from LLM training knowledge. The iterative methodology described in Chapter 2 should be followed throughout.

Three key indicators of iteration quality are: whether each round's best molecule is better than the previous round's (progressiveness); whether this round's strategy differs from the previous round's (non-repetition); and whether a Pareto improvement has been achieved — at least one metric improved with no metric worsened.

### 6.3 Protein and Peptide Design Strategy

The central challenge of protein and peptide design is the triangular relationship among sequence, structure, and function.

**General principles for all protein/peptide design tasks:**

Determining the binding site is paramount; experimental data or literature-reported interface information should be used preferentially. After peptide design with EvoBind, independent validation with Chai-1 is mandatory — EvoBind's ipTM is a design score, not an independent prediction, and requires third-party confirmation. After protein sequence design with ProteinMPNN, a self-consistency check is mandatory — predict the structure of the designed sequence using ESMFold and verify that it is consistent with the design backbone. Peptide drugs require special attention to stability (protease degradation), membrane permeability, and immunogenicity, which are not fully covered by standard ADMET tools and must be discussed qualitatively in the report based on sequence features.

**Iteration in peptide and protein design:** Round 1 uses EvoBind or ProteinMPNN for initial design, followed by Chai-1 validation to select candidates with ipTM above 0.6. Round 2 performs ProteinMPNN sequence optimization on the best candidates, fixing key residues. Round 3 uses interaction-visualizer (peptide mode) to analyze interface interactions, identifies positions amenable to improvement, and re-optimizes. If needed, cyclization (cyclic=True) or peptide length adjustment may be attempted.

**Specialized strategy: thermostability enhancement with binding interface preservation.**

This is a constrained optimization: maximize protein thermostability while ensuring that specific binding interfaces (e.g., receptor interaction surfaces) remain intact. The core difficulty is that mutations improving thermostability in the protein core may propagate conformational changes to the interface, disrupting binding.

Design protocol:

**Step 1 — Define the constraint architecture.** Partition all residues into three classes:
- **Fixed (never mutate):** All interface residues (both sides of each relevant interface), structural cysteines (especially those forming disulfide bonds), catalytic residues.
- **Cautious (may mutate with validation):** Second-shell residues adjacent to the interface (within 5 Å of fixed residues); residues in structurally critical regions (helix caps, turn residues).
- **Free (preferred mutation targets):** Surface-exposed non-interface residues; loop regions distant from functional sites; positions where FoldX PositionScan, ProSST, or literature indicates tolerance for substitution (FoldX ΔΔG < 0.5 kcal/mol for most substitutions).

Additional cysteine constraint: if the design goal does not involve introducing new disulfides, use `omit_aas="CX"` in ProteinMPNN to prevent introduction of new cysteines that could form non-native disulfide bonds.

**Step 2 — Multi-round design with interface validation at every round.**

Round 1: Structure prediction (wild-type baseline) → Interface/pocket identification → Conformational sampling baseline → ProteinMPNN design with fixed interface residues, multiple temperatures, ≥8 candidates → Score by NLL fitness. Optionally run FoldX BuildModel on top ProteinMPNN candidates to obtain ΔΔG as an independent stability predictor orthogonal to NLL fitness.

Round 2: Select top candidates by fitness → Predict structure of each (ESMFold) → **Critical diagnostic step:** compare per-residue pLDDT with wild-type. Identify positions where design decreased local confidence → Fix those problematic positions in the next iteration; optionally open high-confidence positions that were previously fixed. Generate refined candidates.

Round 3: Interface binding validation — predict complex structures (Chai-1) for wild-type and top candidate with the binding partner → Protein-protein docking (HDOCK) → Interface interaction analysis (interaction-visualizer protein mode preferred for single-structure visualization; ProLIF protein-protein mode for trajectory analysis) → Verify ALL fixed interface residues maintain native contacts → Optionally run FoldX AlaScan (with chains) on wild-type and designed complex to confirm hotspot residues (ΔΔG > 1.0 kcal/mol) are preserved → Conformational sampling comparison: reduced conformational diversity in the designed protein vs. wild-type suggests improved thermostability.

**Key checkpoints specific to this strategy:**
- Were positions causing pLDDT drops in Round 2 correctly identified and constrained in subsequent rounds?
- Was the overall fold (e.g., four-helix bundle for IL-2) preserved throughout?
- Were critical interface contacts (salt bridges, hydrophobic packing, hydrogen bonds) maintained?
- Did the final candidate show reduced conformational diversity relative to wild-type?

### 6.4 Multi-Target Selectivity Strategy

The central challenge of selectivity optimization is exploiting subtle structural differences between homologous targets.

Before cross-docking, perform residue-level sequence alignment between targets to identify positions where amino acid identity differs. These are the positions that could enable selectivity. After cross-docking, compare interaction fingerprints across targets — target-specific interactions (present in the desired target, absent in off-targets) are the structural basis for selectivity.

**Critical rule:** Do NOT convert docking score differences (ΔScore) into selectivity fold-changes via thermodynamic equations (ΔG = RT·ln(Kd)). Docking scores are approximate ranking tools, not thermodynamically exact free energies. Only the direction and relative magnitude of ΔScore are informative.

**Residue numbering is especially critical in multi-target work** (Principle 17): different PDB structures for homologous targets may use entirely different numbering schemes. Build a cross-target alignment table before interpreting any interaction comparison.

### 6.4a Multi-Target Dual-Activity Strategy

When the goal is DUAL ACTIVITY (high affinity on BOTH targets) rather than selectivity (high on one, low on another), the design logic inverts:

- **Exploit conserved residues:** Interactions at conserved positions contribute to binding at BOTH targets — these are the anchor points to preserve.
- **Navigate divergent residues carefully:** At positions where targets differ, modifications must be compatible with BOTH amino acid identities. Avoid modifications that form strong interactions with Target 1's residue but clash with Target 2's residue at the same alignment position.
- **Bottleneck-first optimization:** In each iteration round, diagnose which target has the weaker binding, and prioritize modifications that improve binding at THAT target while maintaining binding at the other.
- **Cross-target interaction monitoring:** After each design round, check interaction fingerprints at BOTH targets to ensure no anchor interaction was disrupted.

This strategy is operationalized in Skill 5 Scene D.

---

## Chapter 7. Reporting Standards

### Principle 19: Report Structure

The final report for all tasks should include the following sections, which may be adapted according to the task type.

**Task summary:** A single sentence stating the objective, the target, and the main conclusion.

**Methods overview:** Which tools were used and why they were selected.

**Residue numbering reference (if applicable):** The complete mapping table (Principle 17), including the derivation method.

**Results:** Presented by stage, with every key numerical value annotated with its source tool (Principle 10, Category 1). Every number must have passed the Checkpoint C verification (Principle 12). Clearly distinguish tool-computed facts, agent interpretations, and literature-derived values using the three-category system.

**Iteration history (if applicable):** Optimization trajectory, strategy changes, and convergence status. All molecule counts and scores must be verified values (Principle 11).

**Final recommendations:** Top candidate molecules or sequences with their complete property profiles.

**Downloaded files summary:** List all structure files, image files, and data tables available for user inspection. This enables users to independently verify any claimed result.

**Limitations discussion:** Inherent limitations of the computational methods, prediction uncertainties, and the gap between computation and experimental validation. This section must be substantive, not perfunctory.

**Suggested next steps:** Recommended experimental validation approaches.

### Principle 20: Honest Annotation of Uncertainty

The following situations must be explicitly flagged in the report:

- A predicted structure was used rather than an experimental structure.
- The two pocket identification methods yielded different results.
- Docking scores and independent rescoring produced inconsistent rankings.
- Certain ADMET prediction endpoints have unclear confidence levels.
- Designed molecules or sequences have not yet been experimentally validated.
- **Literature values were used because computational determination was not possible** — cite source and reason (Principle 13).
- **Residue numbering required mapping** — state which mapping was applied and how it was derived (Principle 17).
- **Molecule generation count differed from the requested count** — state both the requested and actual counts (Principle 11).
- **Docking required box enlargement retries** — state the final box size used and why the initial attempt failed (Principle 18).
- **Any computational step that failed and was not completed** — describe the failure, recovery attempts, and impact on conclusions.

A report that acknowledges uncertainty is of greater scientific value than one that claims perfect accuracy.

### Principle 21: Mandatory Data Provenance in the Execution Log

The `run_log.md` must include a "Data Integrity Verification" section (built during Checkpoint C) that maps every key reported value to its source file and verification command. This is not optional — it is the audit trail that makes the report trustworthy. See the system prompt for the required table format.

### Principle 22: File Inventory Completeness

The `run_log.md` must include a complete File Inventory listing every file in the workspace at the end of execution, classified by category (A/B/C per Principle 16). Structure files and image files must be explicitly annotated. Any file referenced in `result.md` must appear in this inventory. If a file is referenced but missing, this is a critical error that must be resolved before the report is finalized.

---

## Quick Reference: Principle Index

| # | Name | Chapter | Core Purpose |
|---|------|---------|-------------|
| 1 | Understand Before Acting | 1 | Plan before execution; anticipate files, numbering, computation needs |
| 2 | Tiered Screening | 1 | Funnel logic; verify counts at every tier boundary |
| 3 | More Than One Method | 1 | Cross-validation; disagree = flag, don't pick |
| 4 | All Design Tasks Iterative | 2 | Never single-round for design/optimization |
| 5 | Three Questions Per Round | 2 | What to improve (data), how (strategy), how to measure (criterion) |
| 6 | Exploration–Exploitation | 2 | Broad→narrow rhythm across rounds |
| 7 | Convergence Criteria | 2 | When to stop; report the reason |
| 8 | Complete Iteration Records | 2 | Trajectory table with verified values |
| 9 | Never Trust Single Output | 3 | Physical plausibility checks; no quantity conflation |
| 10 | Three-Category Distinction | 3 | Tool fact vs. agent inference vs. literature value |
| 11 | Count-Before-Report | 3 | **Anti-fabrication: verify every number against source files** |
| 12 | Three-Checkpoint Self-Audit | 3 | Continuous verification: A (per-call), B (per-round), C (pre-report) |
| 13 | Computation-First Hierarchy | 3 | **Never substitute literature for computation silently** |
| 14 | Mandatory Structure File Collection | 4 | Download ALL structure files from every tool call |
| 15 | Mandatory Image File Collection | 4 | Download ALL visualization files |
| 16 | User-Critical File Identification | 4 | Category A/B/C classification; default = download |
| 17 | Residue Numbering Reconciliation | 5 | **Explicit mapping table before residue-specific analysis** |
| 18 | Docking Parameter Safeguards | 5 | Min 25 Å box; progressive enlargement on failure |
| 19 | Report Structure | 7 | Sections, source annotations, file summary |
| 20 | Honest Uncertainty Annotation | 7 | Flag all uncertainty sources explicitly |
| 21 | Data Provenance in Log | 7 | Checkpoint C audit table is mandatory |
| 22 | File Inventory Completeness | 7 | Every file listed, classified, accounted for |
| 23 | Capability Landscape Mapping | 8 (Supplement) | Data flow connectivity map; A/B/C feasibility grading; scientific value heuristics; problem discovery |
| 24 | Autonomous Workflow Authoring | 8 (Supplement) | Draft workflow standards; paradigm matching; scope limits |
| 25 | Experiential Crystallization | 8 (Supplement) | Triggers T1–T5; five-step process; failure-triggered retrieval; skill revision protocol; mandatory post-execution self-assessment |
| 26 | Capability Boundary Self-Awareness | 8 (Supplement) | Three boundary dimensions; methodological precision table; dynamic update; honest communication |

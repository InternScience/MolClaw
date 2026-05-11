---
name: molclaw-target-protein-preparation
description: >
  Obtain and prepare a clean protein structure from any input form (PDB ID, gene name,
  UniProt ID, amino acid sequence, FASTA file, or PDB file) for downstream computation.
  Almost every protein-related workflow begins with this skill.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 1 (Understand Before Acting — including residue numbering anticipation),
      L3 Principle 9 (Never trust a single tool),
      L3 Principle 14 (Mandatory structure file collection),
      L3 Principle 17 (Residue numbering reconciliation — record numbering scheme of every structure),
      L3 Principle 20 (Honest annotation of uncertainty)
---

# Target Protein Preparation Workflow

## Applicability

**Use this skill when:** The task involves any protein-related computation (docking, free energy, pocket detection, peptide design, etc.) and the protein structure is not yet in a clean, computation-ready state.

**Do NOT use this skill when:** The user has already provided a fully prepared PDB file and explicitly states it requires no further processing. In that case, proceed directly to the downstream workflow.

## Prerequisites

No upstream skill dependency. This skill is itself the starting point for most workflows.

## Input Classification and Acquisition Strategy

Protein input may arrive in six forms. Identify the form first, then follow the corresponding path.

**PDB ID (e.g., "2L3R", "6LU7"):** Call `retrieve_protein_structure_by_pdb_id`. This returns both `fasta_path` and `prot_structure_path`. Record the resolution and method (X-ray/cryo-EM/NMR) in the log — this affects downstream reliability.

**Gene name (e.g., "TP53", "EGFR"):** Call `retrieve_protein_structure_by_gene_name`. If it fails, fall back to: (1) search UniProt for the ID, then try the UniProt path; (2) ask the user for a sequence and use ESMFold; (3) if neither works, report failure with the specific error.

**UniProt ID (e.g., "P38398"):** Call `retrieve_protein_structure_by_uniprot_id` to retrieve an AlphaFold structure. If it fails, suggest ESMFold prediction from the sequence (retrieve the sequence from UniProt first).

**Amino acid sequence (raw or FASTA):** Validate with `is_valid_protein_sequence`. If valid and length ≤ 800 residues, call `pred_protein_structure_esmfold`. If length > 800, use `chai1_predict` with `mode="sequence"` instead — ESMFold quality degrades significantly beyond 800 residues. For multi-chain complexes, always use Chai-1 or Boltz-2, never ESMFold.

**PDB file path:** Skip acquisition. Proceed directly to quality assessment and repair.

**Mixed input (structure + sequence):** Use the structure file. Keep the sequence as a reference for completeness checking.

### Post-Acquisition File Download (L3 Principle 14 — MANDATORY)

After acquiring the protein structure via any path above:

1. **Download the structure file** from the MCP server to the local workspace using `server_file_to_base64` → local decode and save.
2. **Verify download:** `ls -la <filename>` — file must exist with size > 0. A zero-byte file indicates download failure; retry.
3. **Save with step-numbered name:** e.g., `step01_raw_protein.pdb`, `step01_esmfold_prediction.pdb`.

**For ESMFold/Chai-1 predictions:** The predicted structure file is a Category A (user-critical) output. Download is mandatory — this file is the structural basis for all downstream analysis.

<!-- NEW: Optional LR target context -->
### Optional: Target Context Retrieval (if LR tools are available)

Before proceeding to structure quality assessment, optionally search PubMed for target background that informs downstream decisions:

1. Search PubMed: `"[protein name] structure function review"` (retmax=5)
2. Note key findings: known active site residues, co-factors, conformational states, key mutations, known binders
3. Record findings in `run_log.md` under "Target Context": `[LR] pubmed-search | query: [terms] | key findings: [summary]`

This information does NOT replace computational analysis but informs downstream decisions:
- Which chain to extract if multi-chain complex
- Whether apo or holo structure is more appropriate for the task
- Known allosteric sites that may warrant separate pocket detection
- Critical residues to verify in interaction analysis

**If LR tools are not available**, skip this step entirely. Proceed to Structure Quality Assessment.

## Structure Quality Assessment

Before any repair, run a health check to inform repair decisions.

**Step 1 — Basic statistics.** Call `calculate_pdb_basic_info`. Record: chain count (multi-chain?), heteroatom count (ligands/cofactors/waters?), residue count (compare to expected sequence length to estimate missing regions).

**Step 2 — Geometry.** Call `calculate_pdb_structural_geometry`. Record: center of mass (reference for pocket detection), radius of gyration (protein size indicator).

**Step 3 — Quality metrics.** Call `calculate_pdb_quality_metrics`. Record: `avg_bfactor`. Interpretation depends on structure source:
- Experimental structure: B-factor > 80 → poor resolution region
- AlphaFold structure: B-factor column contains pLDDT; < 70 → low confidence overall
- ESMFold structure: same as AlphaFold interpretation

**Quality decision gate:**
- If pLDDT (for predicted structures) < 50: issue a strong warning — "This predicted structure has very low overall confidence. Downstream results may be unreliable. Consider searching for an experimental structure or using Chai-1/Boltz-2 for prediction." Do NOT auto-terminate; let the user or the task requirements decide.
- If pLDDT is 50–70: issue a moderate warning and proceed.
- If pLDDT > 70 or structure is experimental: proceed normally.

**Mandatory source annotation (L3 Principle 20):** Record in the output metadata: `source_type` = one of ["experimental_xray", "experimental_cryoem", "experimental_nmr", "alphafold_prediction", "esmfold_prediction", "chai1_prediction", "boltz2_prediction", "user_provided_unknown"]. This annotation must propagate to all downstream reports.

### Residue Numbering Scheme Documentation (L3 Principle 17 — MANDATORY)

**At this stage, document the numbering scheme of the acquired structure.** This is essential for all downstream residue-specific analyses.

| Structure source | Numbering scheme | How to determine |
|-----------------|-----------------|------------------|
| RCSB PDB | PDB author numbering | `grep DBREF protein.pdb` → extract offset to UniProt |
| AlphaFold DB | UniProt canonical numbering | AlphaFold models use UniProt numbering directly |
| ESMFold prediction | Sequential from 1 | First residue of input = 1; offset = UniProt_start - 1 |
| Chai-1 prediction | Sequential from 1 | Same as ESMFold |
| Boltz-2 prediction | Sequential from 1 | Same as ESMFold |

**Record in `run_log.md`:**
```
### Structure Numbering Scheme
- Structure file: step01_raw_protein.pdb
- Source: [experimental/predicted]
- Numbering scheme: [PDB author / UniProt canonical / Sequential from 1]
- DBREF offset (if RCSB PDB): [UniProt_resnum = PDB_resnum + offset]
- Input sequence start (if predicted): UniProt residue [N] = tool residue 1
```

**If the task description references specific residues:** Immediately check whether those residue numbers match the structure's numbering scheme. If not, plan a mapping step (execute before any residue-specific analysis downstream). Use `residue_mapper.py` if available, or compute the offset manually from DBREF records or known sequence boundaries.

## Chain Processing Strategy

- **Single chain:** Skip extraction, proceed to repair.
- **Multi-chain, user specified target chain:** Call `extract_and_save_chains` to extract the specified chain(s).
- **Multi-chain, user did NOT specify:** Call `extract_pdb_chains` to list all chains with their sequences. Then decide based on task context:
  - If the task involves a specific binding site or active site, select the chain that contains it (check by matching known residue numbers or domain annotations, not by length).
  - If no contextual clue, present the chain list to the user and ask for selection.
  - Only as a last resort, use the longest chain — but explicitly note this choice and warn that it may not be the functionally relevant chain.

## Structure Repair

Call `fix_pdb` with parameters chosen based on the downstream task:

| Parameter | Default | For docking/MD | For ProteinMPNN | For pocket detection |
|-----------|---------|---------------|-----------------|---------------------|
| `add_hydrogens` | True | True | **False** | True |
| `remove_heterogens` | True | True | True | True |
| `remove_water` | True | True | True | True |
| `replace_nonstandard` | True | True | True | True |
| `add_missing_residues` | False | False (unless near pocket) | **True** | False |

**Post-repair verification:** Confirm `status == "success"` and `output_file` exists and is non-empty. If repair fails, check the error log for specific residue/chain issues and report them.

### Post-Repair File Download (L3 Principle 14 — MANDATORY)

The repaired PDB is a Category A output — it is the foundation for ALL downstream workflows.

1. Download the repaired PDB from the MCP server: `server_file_to_base64` → local save as `step02_prepared_protein.pdb`.
2. Verify: `ls -la step02_prepared_protein.pdb` — must have size > 0.
3. **If the task extracted specific chains:** Also download the extracted chain PDB(s).

**⚠ A repair step is NOT considered complete until the repaired PDB has been downloaded and verified locally.**

### FoldX-Specific Repair (When Downstream Uses FoldX)

If the downstream workflow involves FoldX analysis (Stability, BuildModel, AlaScan, PositionScan, PSSM, AnalyseComplex, or SequenceDetail — see L1 skill `molclaw-foldx-tool`), an additional FoldX-specific repair step is **MANDATORY** after the standard pdbfixer repair:

```python
response = await client.session.call_tool("foldx_tool", arguments={
    "mode": "repairpdb",
    "pdb_path": pdbfixer_output_path
})
foldx_repair = client.parse_result(response)
foldx_repaired_pdb = foldx_repair["output_dir"] + "/" + [
    k for k in foldx_repair["key_files"] if k.endswith("_Repair.pdb")
][0]
```

Download the FoldX-repaired PDB via `server_file_to_base64` — Category A output. This optimizes side-chain rotamers against FoldX's energy function. The `*_Repair.pdb` output is the ONLY acceptable input for subsequent FoldX modes.

**When to skip:** If the downstream workflow does NOT involve FoldX (e.g., only docking, MD simulation, or pocket detection), FoldX RepairPDB is not needed.

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| `retrieve_protein_structure_by_gene_name` returns nothing | Gene name ambiguous or not in database | Try UniProt ID; try PDB search with organism filter; ask user for sequence |
| `pred_protein_structure_esmfold` crashes | Sequence too long (>800) or contains non-standard amino acids | Switch to Chai-1; truncate to domain of interest if known |
| `fix_pdb` fails on specific residues | Non-standard residues, missing atoms, or corrupt PDB format | Re-download structure; try with `replace_nonstandard=True`; if still fails, manually remove problematic residues and note the gap |
| AlphaFold structure has very low pLDDT in binding region | Disordered region or poor prediction | Search for experimental structure; consider whether the task is feasible for this target |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after acquisition:**
- [ ] Structure file downloaded to local workspace and verified non-empty
- [ ] Numbering scheme documented in run_log.md
- [ ] If task references specific residues, mapping plan established

**CHECKPOINT after repair:**
- [ ] Repaired PDB downloaded to local workspace and verified non-empty
- [ ] Source type annotation recorded
- [ ] Quality metrics (pLDDT or B-factor) recorded and interpreted
- [ ] If pLDDT < 70 for predicted structure, warning issued

## Output Specification (Data Handoff Contract)

| Output | Variable name | Format | Consumed by | Download Policy |
|--------|--------------|--------|-------------|-----------------|
| Prepared structure | `prepared_pdb` | PDB file path | Skills 2, 6, 7, 8, 9, 10, 11 | **A — MUST download** |
| Chain information | `chain_info` | Dict: {chain_id: sequence} | Skills 9, 10, 11 | B — record in log |
| Quality summary | `quality_summary` | Dict: {source_type, avg_plddt_or_bfactor, residue_count, chain_count} | All downstream skills (for reporting) | B — record in log |
| Sequence (FASTA) | `fasta_path` | FASTA file path | Skills 9, 10 | **A — MUST download** |
| Numbering scheme info | `numbering_scheme` | Dict: {scheme, offset, input_seq_start} | Skills 2, 6, 8, 9, 10, 11 | B — record in log |

| FoldX-repaired structure | `foldx_repaired_pdb` | PDB file path | FoldX modes in Skills 9, 10 (Scene B/F) | **A — MUST download** (only when FoldX downstream) |

**Critical rule:** Downstream skills MUST use `prepared_pdb`, never the raw input file.

---
name: molclaw-conformational-sampling-analysis
description: >
  Protein conformational sampling and analysis: coarse-grained and all-atom simulation,
  full-atom reconstruction, multi-conformation pocket identification, and cryptic pocket discovery.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L2-Workflow
    version: 3.0-enhanced
    methodology-ref: >
      L3 Principle 3 (More than one method),
      L3 Principle 14 (Mandatory structure file collection — download ALL conformational ensemble structures and trajectories),
      L3 Principle 15 (Mandatory image file collection — download RMSD plots, pocket analysis images),
      L3 Principle 11 (Count-Before-Report — verify conformation counts from actual files)
---

# Conformational Sampling and Analysis Workflow

## Applicability

**Use this skill when:** Exploring protein conformational diversity for cryptic pocket discovery, ensemble docking, assessing conformational effects on drug binding, or studying protein folding/assembly dynamics.

**Do NOT use this skill when:** The protein is small (< 80 residues) and known to be rigid; or when a single high-quality crystal structure with a well-defined pocket is sufficient for the task.

## Prerequisites

| Input | Source | Required? |
|-------|--------|-----------|
| Protein structure | Skill 1 `prepared_pdb` | Yes (for GoCa, OpenAWSEM, OpenMM) |
| Protein sequence | Skill 1 `fasta_path` | Yes (for BioEmu, ESMFold alternative) |

## Sampling Method Selection

| Method | Tool | Input | Speed | Conformational range | Best for |
|--------|------|-------|-------|---------------------|----------|
| **BioEmu** | `molclaw-run-bioemu` | Sequence (FASTA) | Fast | Equilibrium ensemble | Quick diverse sampling; proteins < 300 residues |
| **GoCa** | `molclaw-goca-tool` | Structure (PDB) | Medium | Large-amplitude motions | Multi-protein complexes; domain motions |
| **OpenAWSEM** | `molclaw-openawsem-tool` | Structure (PDB) | Medium | Folding landscape, large transitions | DFG-flip studies; fold switching |
| **OpenMM** | `molclaw-protein-openmm` | Structure (PDB) | Slow (most accurate) | Local fluctuations, loop dynamics | Precise local conformational changes |

**Selection decision tree:**
- Protein > 500 residues → GoCa or OpenAWSEM (coarse-grained)
- Need fast diverse conformations → BioEmu
- Need time-resolved dynamics → OpenMM
- Studying large domain motions → GoCa or OpenAWSEM
- Need highest accuracy for local loop region → OpenMM

### Recommended Parameters

**BioEmu:** `num_samples`: 20–50 for exploration, 100+ for statistical analysis. `temperature`: default (300K); increase to 350K for enhanced sampling.

**GoCa:** `n_steps`: 10000–50000. `temperature`: 300K default; 350K for enhanced sampling.

**OpenAWSEM:** `n_steps`: 10000–100000. `temperature`: 300K; use replica exchange temperatures [280, 300, 320, 350] if available.

**OpenMM:** `forcefield`: "amber14-all". `temperature`: 300 K. `timestep`: 2 fs. `simulation_time`: 5–20 ns for pocket analysis; 50–100 ns for thorough sampling. `save_interval`: every 10 ps. `solvent`: "tip3p" (explicit) or "implicit" (faster).

## Core Workflow

### Step 1: Generate Conformational Ensemble

Execute the chosen sampling method with the parameters above. Target: at least 10 distinct conformations for downstream analysis.

### Mandatory Ensemble Download (L3 Principle 14 — CRITICAL)

**After sampling completes, download ALL structure and trajectory files:**

| Tool | Files to download | Category |
|------|------------------|----------|
| BioEmu | All sampled PDB structures | **A — MUST download** |
| GoCa | Output trajectory PDB(s), Cα trace files | **A — MUST download** |
| OpenAWSEM | Output PDB(s), trajectory files | **A — MUST download** |
| OpenMM | Trajectory (XTC/DCD), final frame (PDB/GRO), topology (PSF/TOP) | **A — MUST download** |

```python
# Download ALL structure files from sampling output
import os, base64
for struct_file in sampling_output_files:
    response = await client.session.call_tool(
        "server_file_to_base64",
        arguments={"file_path": struct_file}
    )
    dl = client.parse_result(response)
    local_path = f"step{N}_conf_{i:03d}.pdb"
    with open(local_path, "wb") as f:
        f.write(base64.b64decode(dl["base64_string"]))
    assert os.path.getsize(local_path) > 0
```

**⚠ COUNT GATE (L3 Principle 11):** After downloading, count the actual number of conformations obtained:
```
Conformational sampling verification:
- Requested: 50 conformations
- Output files: [list]
- Actual count: 47 valid conformations (verified by file count)
```

### Step 2: Full-Atom Reconstruction (coarse-grained methods only)

If GoCa or OpenAWSEM was used, reconstruct full-atom structures:

1. Call `molclaw-pulchura-rebuild` to rebuild backbone and side-chain heavy atoms.
2. Call `molclaw-pack-sidechains` (AttnPacker) to optimize side-chain conformations.
3. Validate: call `calculate_pdb_quality_metrics` and `calculate_pdb_basic_info` on each reconstructed structure.

**Post-reconstruction download (L3 Principle 14):** Download ALL reconstructed full-atom PDB files. These are Category A outputs.

### Step 3: Conformational Analysis

**Quality check on each conformation:**
- Call `calculate_pdb_structural_geometry` for radius of gyration and center of mass
- Call `calculate_pdb_quality_metrics` for quality metrics
- Discard conformations with severe steric clashes or unfolded structures (Rg > 2× initial structure)

**Pocket identification across conformations:**
For each retained conformation, run `fpocket_toolkit` and/or `pred_pocket_prank`. Record for each conformation: pocket count, positions, volumes, druggability scores.

**Cryptic pocket discovery (core step):**
Compare pockets across conformations vs. the initial reference structure:
- Pockets in reference AND most conformations → stable, canonical
- Pockets in reference but ABSENT in some → conformationally dependent
- Pockets ABSENT in reference but APPEARING in some → **candidate cryptic pockets**

For each candidate cryptic pocket, record: frequency, druggability score range, key residues, conformational change that opens it.

### Post-Analysis Image Download (L3 Principle 15 — MANDATORY)

Download ALL visualization outputs generated during analysis:
- RMSD/RMSF plots (PNG)
- Pocket volume variation plots (PNG)
- Conformational clustering dendrograms (PNG)
- Any other images from analysis tools

### Step 4: Downstream Applications

**Ensemble docking:** Pass representative conformations to Skill 2. Dock the same molecule library against each conformation.

**Cryptic pocket drug design:** For validated cryptic pockets, use Skill 4 (generative design) to generate molecules targeting the new pocket shape, then Skill 2 to dock and validate.

## Common Failures & Recovery

| Failure | Likely cause | Recovery |
|---------|-------------|----------|
| BioEmu produces very similar conformations | Protein is genuinely rigid; or temperature too low | Increase temperature to 350K; accept limited diversity as a valid finding |
| Pulchra reconstruction produces distorted structures | Input Cα trace had unphysical bond lengths | Filter Cα frames by geometry before reconstruction |
| OpenMM simulation crashes | Missing parameters for non-standard residues | Use `fix_pdb` with `replace_nonstandard=True`; try implicit solvent |
| No cryptic pockets found | Protein may not have them; or sampling insufficient | Run longer simulation; try different method; report the negative result |

## Quality Gates (Active Checkpoints)

**CHECKPOINT after Step 1 (sampling):**
- [ ] All conformation/trajectory files downloaded and verified non-empty
- [ ] Actual conformation count verified from file count (not from requested count)

**CHECKPOINT after Step 2 (reconstruction, if applicable):**
- [ ] Reconstructed full-atom PDB files downloaded and verified
- [ ] Structures validated (atom counts reasonable, no unfolded structures)

**CHECKPOINT after Step 3 (analysis):**
- [ ] Pocket identification run on multiple conformations
- [ ] Analysis images downloaded
- [ ] Cryptic pocket claims supported by frequency data
- [ ] If task mentions specific residues, numbering context clarified

## Output Specification (Data Handoff Contract)

| Output | Format | Consumed by | Download Policy |
|--------|--------|-------------|-----------------|
| Representative conformation PDBs | PDB files (numbered) | Skill 2 (ensemble docking) | **A — MUST download** |
| Trajectory files | XTC/DCD/PDB trajectory | Archive | **A — MUST download** |
| Pocket comparison table | Markdown | Report | B — record in log |
| Cryptic pocket report | Markdown | Report, Skill 4 | B — record in log |
| RMSD/analysis plots | PNG | Report | **A — MUST download** |
| Sampling parameters and statistics | Markdown | Report | B — record in log |

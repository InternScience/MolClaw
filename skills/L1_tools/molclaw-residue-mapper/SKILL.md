---
name: molclaw-residue-mapper
description: >
  Map residue numbering between UniProt canonical, PDB author, and tool-internal sequential
  numbering schemes. Essential for correctly interpreting ProLIF/PLIP results from predicted
  structures (ESMFold, Boltz-2, Chai-1) and RCSB PDB files with non-trivial numbering offsets.
  Prevents silent misinterpretation of residue-specific analysis outputs.
license: MIT license
metadata:
    skill-author: PJLab
    skill-level: L1-Tool
    version: 1.0
    methodology-ref: >
      L3 Principle 17 (Residue Numbering Reconciliation — this tool is the primary
      implementation of the mandatory mapping protocol).
      L2 Skills 01, 02, 05, 06, 08, 09, 10, 11 all reference this tool for residue mapping.
---

# Residue Numbering Mapping Skill

> [!IMPORTANT]
> **When to use this skill:** BEFORE interpreting ANY residue-specific analysis results (ProLIF,
> PLIP, per-residue energy decomposition, interface contact analysis) when the task references
> specific residues AND the analysis structure uses a different numbering scheme from the task
> description. This is extremely common — prediction tools (ESMFold, Boltz-2, Chai-1) ALWAYS
> renumber from 1, and RCSB PDB files frequently have offsets relative to UniProt.
>
> **Failure to map numbering is a silent catastrophic error:** ProLIF may report "HBDonor at
> MET76" when the task asks about "Met793" — these are the SAME residue in different numbering
> schemes. Without mapping, the agent concludes "Met793 interaction is absent" — a false negative.

## Task Description

Build an explicit, verifiable mapping table between residue numbering schemes:
- **UniProt canonical numbering** — used in most task descriptions, literature, and databases
- **PDB author numbering** — used in RCSB PDB ATOM records (may have offsets, insertion codes)
- **Tool-internal sequential numbering** — used by ESMFold, Boltz-2, Chai-1, ProLIF output (always 1-based from input sequence start)

The tool supports three mapping strategies in priority order:
1. **Arithmetic mapping** (instant, exact) — for predicted structures with known `input_seq_start`
2. **DBREF fast path** (instant, exact) — for RCSB PDB files with DBREF header records
3. **Sequence alignment** (seconds, robust) — Needleman-Wunsch fallback for any PDB

## Input Source Mapping

| Parameter | Source Guidance |
|-----------|----------------|
| `pdb_path` | PDB file from structure retrieval (`retrieve_protein_structure_by_*`), prediction (`pred_protein_structure_esmfold`, `chai1_predict`, Boltz-2), or repair (`fix_pdb`). Must be on the MCP server filesystem. |
| `uniprot_id` | UniProt accession (e.g., `"P00533"` for EGFR). Fetches sequence online. Use this when network is available. |
| `uniprot_fasta` | Path to local FASTA file containing UniProt sequence. Use when offline or when you already have the FASTA from `retrieve_protein_structure_by_*`. |
| `uniprot_seq` | Raw amino acid sequence string. Use for scripting or when neither ID nor FASTA is available. |
| `chain` | Chain ID in the PDB file to process (e.g., `"A"`). Recommended to always specify for clarity. |
| `predicted` | Set `True` for structures from ESMFold, Boltz-2, Chai-1, ProteinMPNN → ESMFold. These use 1-based sequential numbering. |
| `input_seq_start` | **Required when `predicted=True`.** The UniProt residue number of the FIRST residue in the input sequence given to the prediction tool. E.g., if you predicted EGFR kinase domain starting from UniProt residue 718, set `input_seq_start=718`. |
| `query` | Comma-separated residue identifiers to look up. See Query Syntax below. |

## Usage


### Tool: `residue_mapper`

```text
Map residue numbering between UniProt, PDB author, and tool-internal numbering schemes.
Args:
    pdb_path (str): Path to PDB file (RCSB or predicted structure) on the MCP server.
    uniprot_id (str|None): UniProt accession ID (e.g., "P00533"). Fetches sequence online. Default: None.
    uniprot_fasta (str|None): Path to local FASTA file with UniProt sequence. Default: None.
    uniprot_seq (str|None): Raw amino acid sequence string. Default: None.
    chain (str|None): Chain ID to process (e.g., "A"). Default: None (all chains).
    predicted (bool): True if PDB is from a prediction tool (ESMFold/Boltz-2/Chai-1). Default: False.
    input_seq_start (int|None): UniProt residue number of the first residue in the prediction input sequence. Required when predicted=True. Default: None.
    query (str|None): Comma-separated residue query string. Default: None.
    no_dbref (bool): Skip DBREF parsing; force alignment-based mapping. Default: False.
    output_format (str): Output format: "csv" or "json". Default: "csv".
    dry_run (bool): Validate arguments only, do not execute mapping. Default: False.
    quiet (bool): Suppress informational messages. Default: False.
Return:
    status (str): "success", "partial_success", or "error".
    msg (str): Human-readable summary or error message.
    output_dir (str): Absolute path to run-specific output directory.
    mapping_file (str): Filename of the mapping table (mapping.csv or mapping.json) inside output_dir.
    format (str): Output format used ("csv" or "json").
    total_residues (int): Total number of residue rows in the mapping.
    matched_residues (int): Rows with match_type "matched" or "dbref" (correctly mapped).
    mismatch_residues (int): Rows with match_type "mismatch" (amino acid differs — mutation or selenomethionine).
    unmapped_residues (int): Rows without UniProt index (expression tags, insertions).
    chains (list[str]): Chain IDs that were processed.
    query_results (list[dict]): Query result rows (only when query is provided). Each dict has keys: chain, pdb_resnum, pdb_resname, one_letter, uniprot_resnum, tool_internal_num, match_type, notes.
```

## Scenario 1: RCSB PDB → UniProt Mapping

**When:** You downloaded a structure from RCSB (e.g., PDB 1M17 for EGFR) and the task references UniProt residue numbers (e.g., "confirm interaction with Met793").

```python
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step01_1M17_fixed.pdb",
        "uniprot_id": "P00533",
        "chain": "A",
        "output_format": "csv"
    }
)
result = client.parse_result(response)
mapping_dir = result["output_dir"]
mapping_file = result["mapping_file"]  # "mapping.csv"
# Full mapping saved at: {mapping_dir}/{mapping_file}
# Download this file for user verification
```

The tool auto-reads the `DBREF` record from the PDB header, determines the offset (e.g., +24 for 1M17 chain A: UniProt = PDB + 24), and produces the complete mapping table.

## Scenario 2: Predicted Structure → UniProt Mapping

**When:** You ran ESMFold, Boltz-2, or Chai-1 with a protein subsequence (e.g., EGFR kinase domain, UniProt residues 718–1046). The output PDB uses 1-based sequential numbering (residue 1, 2, 3...). You need to translate ProLIF results back to UniProt residue numbers.

```python
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step05_boltz2_complex.pdb",
        "uniprot_id": "P00533",
        "chain": "A",
        "predicted": True,
        "input_seq_start": 718,    # First residue of input = UniProt 718
        "output_format": "csv"
    }
)
result = client.parse_result(response)
# Mapping: tool residue 1 = UniProt 718, tool residue 76 = UniProt 793 (Met793!), etc.
```

**⚠ Critical:** `input_seq_start` must be the UniProt position of the FIRST residue in the sequence you gave to the prediction tool. Get this from the FASTA header or from the sequence extraction step. An incorrect `input_seq_start` will silently produce wrong mappings for ALL residues.

## Scenario 3: Query Specific Residues (Forward Lookup)

**When:** The task says "confirm that interactions with Met793, Thr790, and Leu718 are preserved." You need to find these residues in the analysis structure's numbering.

```python
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step05_boltz2_complex.pdb",
        "uniprot_id": "P00533",
        "chain": "A",
        "predicted": True,
        "input_seq_start": 718,
        "query": "Met793,Thr790,Leu718,Val726,Ala743,Leu844"
    }
)
result = client.parse_result(response)
for qr in result["query_results"]:
    print(f"UniProt {qr['uniprot_resnum']} = PDB {qr['pdb_resnum']} "
          f"({qr['pdb_resname']}) = Tool internal #{qr['tool_internal_num']}")
# Output:
# UniProt 793 = PDB 76 (MET) = Tool internal #76
# UniProt 790 = PDB 73 (THR) = Tool internal #73
# UniProt 718 = PDB 1 (LEU) = Tool internal #1
# ...
```

Now search ProLIF output for `MET76` (not `MET793`) to find the hinge hydrogen bond.

## Scenario 4: Reverse Lookup — ProLIF Output → UniProt

**When:** ProLIF reported interactions at tool-internal residues 76, 73, 26. You need to know what these are in UniProt numbering.

```python
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step05_boltz2_complex.pdb",
        "uniprot_id": "P00533",
        "chain": "A",
        "predicted": True,
        "input_seq_start": 718,
        "query": "tool:76,tool:73,tool:26"
    }
)
result = client.parse_result(response)
# query_results tells you:
# tool:76 = UniProt 793 (Met) → This IS the Met793 hinge interaction!
# tool:73 = UniProt 790 (Thr) → Gatekeeper
# tool:26 = UniProt 743 (Ala) → Ala743
```

## Scenario 5: Lookup by PDB Author Numbering

**When:** You have PDB residue numbers from a crystallography paper and need UniProt mapping.

```python
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step01_1M17_fixed.pdb",
        "uniprot_id": "P00533",
        "chain": "A",
        "query": "pdb:769,pdb:766,pdb:694"
    }
)
result = client.parse_result(response)
# pdb:769 = UniProt 793 (Met)
# pdb:766 = UniProt 790 (Thr)
# pdb:694 = UniProt 718 (Leu)
```

## Scenario 6: Offline Mode (No Network Access)

**When:** The MCP server cannot reach the internet to fetch UniProt sequences.

```python
# Option A: Use a local FASTA file (from retrieve_protein_structure_by_uniprot_id output)
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step01_1M17_fixed.pdb",
        "uniprot_fasta": "step01_P00533.fasta",
        "chain": "A",
        "output_format": "csv"
    }
)

# Option B: Provide raw sequence directly
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "step01_1M17_fixed.pdb",
        "uniprot_seq": "MRPSGTAGAALLALLAALCPASRALEEKKVC...",
        "chain": "A",
        "output_format": "csv"
    }
)
```

## Scenario 7: Multi-Chain Complex (Two Different Proteins)

**When:** Mapping a two-chain complex where chain A and chain B are different proteins (e.g., receptor + ligand protein).

```python
response = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "complex.pdb",
        "uniprot_id": "P00533",          # For chain A
        "chain": "A",
        "output_format": "csv"
    }
)
# Run separately for chain B with its own UniProt ID
response_b = await client.session.call_tool(
    "residue_mapper",
    arguments={
        "pdb_path": "complex.pdb",
        "uniprot_id": "P01589",          # For chain B
        "chain": "B",
        "output_format": "csv"
    }
)
```

## Query Syntax Reference

| Syntax | Numbering scheme | Example |
|--------|-----------------|---------|
| `Met793` or `793` | UniProt canonical (default) | `"Met793,Thr790,Leu718"` |
| `pdb:769` | PDB author numbering | `"pdb:769,pdb:766"` |
| `tool:76` | Tool-internal sequential | `"tool:76,tool:73,tool:26"` |
| Mixed | All three in one query | `"Met793,pdb:769,tool:76"` |

## Output CSV Columns

| Column | Description | Example |
|--------|-------------|---------|
| `chain` | PDB chain ID | `A` |
| `pdb_resnum` | PDB author residue number (may include insertion code) | `769`, `100A` |
| `pdb_resname` | Three-letter residue name | `MET` |
| `one_letter` | One-letter amino acid code | `M` |
| `uniprot_resnum` | UniProt canonical position | `793` |
| `tool_internal_num` | 1-based sequential number | `76` |
| `match_type` | Mapping quality indicator | `matched`, `dbref`, `mismatch` |
| `notes` | Additional information | `DBREF offset=+24` |

### Match Type Interpretation

| Type | Meaning | Action |
|------|---------|--------|
| `dbref` | Mapped via PDB DBREF record — highest confidence | Trust |
| `matched` | Sequence alignment: amino acids match — high confidence | Trust |
| `mismatch` | Amino acids differ (engineered mutation, selenomethionine) | Note in report; position mapping is still correct |
| `outside_dbref_estimated` | Outside DBREF range; UniProt number estimated from offset | Use with caution; verify manually |
| `insertion_in_pdb` | Residue in PDB not in UniProt (expression tag, linker) | No UniProt number available |
| `NOT_FOUND` | Query residue not found in mapping | Residue may be in disordered region (no coordinates) |

## Downloading the Mapping File

**The mapping CSV/JSON file is a Category A output (L3 Principle 14) — MUST be downloaded:**

```python
import base64, os

# Download the mapping file from MCP server to local workspace
mapping_server_path = os.path.join(result["output_dir"], result["mapping_file"])
dl_response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={"file_path": mapping_server_path}
)
dl = client.parse_result(dl_response)
local_path = f"step{N}_residue_mapping.csv"
with open(local_path, "wb") as f:
    f.write(base64.b64decode(dl["base64_string"]))
assert os.path.getsize(local_path) > 0, "Mapping file download failed"
```

## Common Pitfalls and Recovery

| Problem | Cause | Solution |
|---------|-------|----------|
| All residues show `mismatch` | Wrong UniProt ID or wrong chain specified | Verify UniProt accession matches the protein; check `--chain` value |
| Wrong `input_seq_start` value | Uncertain which UniProt residue starts the input sequence | Check the FASTA header from the structure retrieval step; look at the first few residues in the PDB and match them against the UniProt sequence |
| `Failed to fetch UniProt sequence` | MCP server has no internet access | Use `uniprot_fasta` (from `retrieve_protein_structure_by_*` output) or `uniprot_seq` instead of `uniprot_id` |
| Query returns `NOT_FOUND` | Residue is in a disordered region (no ATOM coordinates in PDB) | The residue truly has no structural coordinates; note this as a limitation |
| DBREF gives wrong offset | PDB has non-standard or incorrect DBREF | Use `no_dbref=True` to force alignment-based mapping |
| Tool-internal numbers in ProLIF don't match expected | PDB file given to ProLIF had a different numbering than expected | Confirm which PDB file was used as ProLIF input; run residue_mapper on THAT specific PDB file |

## Integration with Other Skills

### When to Call This Skill in a Pipeline

```
Skill 1 (Protein Preparation)
    ↓ outputs: prepared_pdb, numbering_scheme
    ↓
★ residue_mapper (if task references specific residues)
    ↓ outputs: mapping_table.csv
    ↓
Skill 2 (Docking) → ProLIF analysis
    ↓
★ Use mapping_table to interpret ProLIF residue IDs → report in UniProt numbering
```

### Integration with ProLIF (Skills 2, 8)

After running `prolif_docking` or `prolif_pdb`, the output reports residue identifiers in the numbering of the PDB file given to ProLIF. Use residue_mapper with `query="tool:XX,tool:YY"` to translate these to UniProt numbering before concluding whether task-specified interactions are present or absent.

### Integration with MM-PBSA Per-Residue Decomposition (Skill 6)

After `analyze_mmpbsa` reports per-residue energy contributions, use the mapping table to translate hotspot residue numbers to UniProt numbering for reporting and cross-validation with ProLIF data.

### Integration with Multi-Target Selectivity (Skill 11)

Run residue_mapper independently for each target structure. Build a cross-target alignment table by mapping both targets to their respective UniProt sequences, then aligning by UniProt position.

## Technical Notes

- **No external dependencies required.** The tool includes a built-in Needleman-Wunsch alignment algorithm (pure Python). BioPython `pairwise2` is used if available (faster for very long sequences) but is not required.
- **Non-standard amino acids recognized:** MSE→M (selenomethionine), TPO→T (phosphothreonine), SEP→S (phosphoserine), PTR→Y (phosphotyrosine), and CHARMM/AMBER histidine variants (HSD/HSE/HSP/HIE/HID/HIP→H).
- **Insertion codes preserved:** PDB insertion codes (e.g., 100A, 100B) are correctly handled in both DBREF and alignment strategies.
- **Performance:** Arithmetic and DBREF strategies are instant. Sequence alignment is O(n×m) where n and m are sequence lengths — typically completes in 1–5 seconds for standard proteins.

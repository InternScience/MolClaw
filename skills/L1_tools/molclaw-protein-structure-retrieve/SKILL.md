---
name: molclaw-protein-structure-retrieve
description: Retrieve and download protein structure file (pdb format) using gene name, Uniprot ID or PDB ID. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Retrieve Protein Structure 

**Scene 1**: If the **gene name** is provided, please use tool *retrieve_protein_structure_by_gene_name*.

The description of tool *retrieve_protein_structure_by_gene_name*.

```tex
Retrieve and download the protein structure (.pdb) file using standard gene name.
Args:
    gene_name (str): Input gene name (e.g., 'TP53')
    organism (str): Species NCBI Taxonomy ID (default: 9606 for human, 10090 for mouse)
    sort_by (str): The sorting strategy defaults ('length') to prioritizing sequence length for maximum coverage, with an alternative option ('resolution') to prioritize structural resolution. 
Return:
    status (str): success/error
    msg (str): message
    prot_structure_path (str): Path to the downloaded protein structure file (pdb format)
```

How to use tool *retrieve_protein_structure_by_gene_name* :

```python
response = await client.session.call_tool(
    "retrieve_protein_structure_by_gene_name",
    arguments={
        "gene_name": gene_name,
        "organism": "9606",
        "sort_by": "length"
    }
)
result = client.parse_result(response)
prot_structure_path = result["prot_structure_path"]
```

**Scene 2**: If the **UniProt ID** is provided, please use tool *retrieve_protein_structure_by_uniprot_id*.

The description of tool *retrieve_protein_structure_by_uniprot_id*.

```tex
Retrieve and download the protein structure (.pdb) file using uniprot id.
Args:
    uniprot_id (str): Input uniprot id (e.g., 'P04637')
    sort_by (str): The sorting strategy defaults ('length') to prioritizing sequence length for maximum coverage, with an alternative option ('resolution') to prioritize structural resolution. 
Return:
    status (str): success/error
    msg (str): message
    prot_structure_path (str): Path to the downloaded protein structure file (pdb format)
```

How to use tool *retrieve_protein_structure_by_uniprot_id* :

```python
response = await client.session.call_tool(
    "retrieve_protein_structure_by_uniprot_id",
    arguments={
        "uniprot_id": uniprot_id,
        "sort_by": "length"
    }
)
result = client.parse_result(response)
prot_structure_path = result["prot_structure_path"]
```

**Scene 3**: If the **PDB ID** is provided, please use tool *retrieve_protein_structure_by_pdb_id*.

The description of tool *retrieve_protein_structure_by_pdb_id*.

```tex
Retrieve and download the protein structure (.pdb) file using pdb id.
Args:
    pdb_id (str): Input pdb id (e.g., "2l3r", "5XYF")
Return:
    status (str): success/error
    msg (str): message
    prot_structure_path (str): Path to the downloaded protein structure file (pdb format)
```

How to use tool *retrieve_protein_structure_by_pdb_id* :

```python
response = await client.session.call_tool(
    "retrieve_protein_structure_by_uniprot_id",
    arguments={
        "pdb_id": pdb_id
    }
)
result = client.parse_result(response)
prot_structure_path = result["prot_structure_path"]
```


---

## ⚠ Mandatory Structure File Download (L3 Principle 14)

After retrieving a protein structure, **download the PDB file** from the MCP server to the local workspace. This is a Category A file — the foundation for all downstream workflows. Also download the FASTA file if provided.

## ⚠ Record Numbering Scheme (L3 Principle 17)

After downloading, document the structure's residue numbering scheme in `run_log.md`:
- RCSB PDB: check DBREF records for UniProt offset
- AlphaFold: uses UniProt canonical numbering
- If the task references specific residues, plan a mapping step using `molclaw-residue-mapper`

---
name: pubmed-search
description: Search PubMed for scientific literature. Use when the user asks to find papers, search literature, look up research, find publications, or asks about recent studies. Triggers on "pubmed", "papers", "literature", "publications", "research on", "studies about".
---

# PubMed Search

Search NCBI PubMed for scientific literature using BioPython's Entrez module.

## When to Use

- User asks to find papers on a topic
- User wants recent publications in a field
- User asks for references or citations
- User wants to know the state of research on a topic

## How to Execute

### 1. Set up Entrez

```python
from Bio import Entrez
Entrez.email = "medclaw@freedomai.com"
```

### 2. Search PubMed

```python
# Search
handle = Entrez.esearch(db="pubmed", term="CRISPR delivery methods", retmax=20, sort="date")
record = Entrez.read(handle)
handle.close()

id_list = record["IdList"]
print(f"Found {record['Count']} results, showing top {len(id_list)}")
```

### 3. Fetch article details

```python
# Fetch details
handle = Entrez.efetch(db="pubmed", id=id_list, rettype="xml")
records = Entrez.read(handle)
handle.close()

for article in records['PubmedArticle']:
    medline = article['MedlineCitation']
    pmid = str(medline['PMID'])
    title = medline['Article']['ArticleTitle']
    
    # Get authors
    authors = medline['Article'].get('AuthorList', [])
    first_author = f"{authors[0].get('LastName', '')} {authors[0].get('Initials', '')}" if authors else "Unknown"
    
    # Get journal and year
    journal = medline['Article']['Journal']['Title']
    pub_date = medline['Article']['Journal']['JournalIssue'].get('PubDate', {})
    year = pub_date.get('Year', 'N/A')
    
    # Get abstract
    abstract_parts = medline['Article'].get('Abstract', {}).get('AbstractText', [])
    abstract = ' '.join(str(a) for a in abstract_parts)[:300]
    
    print(f"PMID: {pmid}")
    print(f"Title: {title}")
    print(f"Authors: {first_author} et al.")
    print(f"Journal: {journal} ({year})")
    print(f"Abstract: {abstract}...")
    print(f"Link: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
    print()
```

### 4. Drug Discovery Query Templates

Common search patterns for computational drug discovery tasks:

```python
# Target validation / background
term = '"[TARGET]"[Title] AND (review[Publication Type] OR "drug target"[Title/Abstract])'

# Known inhibitors / binders with binding data
term = '"[TARGET]" AND (inhibitor OR antagonist) AND (IC50 OR Ki OR Kd)[Title/Abstract]'

# Crystal structures with ligands
term = '"[TARGET]" AND "crystal structure"[Title] AND "ligand"[Title/Abstract]'

# Virtual screening / computational docking studies
term = '"[TARGET]" AND ("molecular docking" OR "virtual screening")[Title/Abstract]'

# SAR studies
term = '"[TARGET]" AND "structure-activity relationship"[Title/Abstract]'

# Binding free energy / MMPBSA benchmarks
term = '"[TARGET]" AND ("binding free energy" OR "MM-PBSA" OR "MM-GBSA")[Title/Abstract]'

# Peptide / protein-protein interaction
term = '"[TARGET]" AND ("protein-protein interaction" OR "peptide inhibitor")[Title/Abstract]'

# ADMET / pharmacokinetics for compound class
term = '"[COMPOUND CLASS]" AND (ADMET OR pharmacokinetics OR "drug-likeness")[Title/Abstract]'
```

**MolClaw integration requirements:**
- Every retrieved result MUST be labeled as Category 3 information (⚠️ LITERATURE VALUE) per Principle 10.
- Output MUST include PMID, DOI (when available), first author, year, journal for each citation.
- Retrieved literature values NEVER substitute for computational results (Principle 13).
- Save search results as `stepNN_LR_pubmed_[topic].md` following MolClaw file naming convention.

### 5. Advanced searches

Support these query patterns:
- `"CRISPR"[Title] AND "delivery"[Title]` — title-specific
- `"2026"[Date - Publication]` — date filter
- `"Nature"[Journal]` — journal filter
- `review[Publication Type]` — type filter

### 6. Follow-up suggestions

After showing results, suggest:
- "Want me to summarize any of these papers?"
- "Should I search with different keywords?"
- "Want me to find related papers to any of these?"

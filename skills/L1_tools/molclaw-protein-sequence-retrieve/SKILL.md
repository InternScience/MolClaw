---
name: molclaw-protein-sequence-retrieve
description: Search the target protein sequence information from the input gene name or uniprot id. 
license: MIT license
metadata:
    skill-author: PJLab
---

# Retrieve Target Protein Sequence

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

The description of tool *retrieve_protein_sequence*.

```tex
Retrieve protein sequence data for a given identifier (gene name or uniprot id) and organism.
Args:
    identifier (str): Input gene name (e.g., 'TP53') or uniprot id (e.g., 'P04637')
    organism (str): Species name, default is "Homo sapiens" 
Return:
    status (str): success/error
    msg (str): message
    seq_info (dict): A dict containing uniprot_id, gene_name, protein_name, organism, sequence, length
```

How to use tool *retrieve_protein_sequence* :

```python
response = await client.session.call_tool(
    "retrieve_protein_sequence",
    arguments={
        "identifier": identifier,
        "organism": organism
    }
)
result = client.parse_result(response)
prot_sequence_info = result["seq_info"]
```

An example of output sequence information:

```
{'uniprot_id': 'O76074', 'gene_name': 'PDE5A', 'protein_name': "cGMP-specific 3',5'-cyclic phosphodiesterase", 'organism': 'Homo sapiens', 'length': 875, 'sequence': 'MERAGPSFGQQRQQQQPQQQKQQQRDQDSVEAWLDDHWDFTFSYFVRKATREMVNAWFAERVHTIPVCKEGIRGHTESCSCPLQQSPRADNSAPGTPTRKISASEFDRPLRPIVVKDSEGTVSFLSDSEKKEQMPLTPPRFDHDEGDQCSRLLELVKDISSHLDVTALCHKIFLHIHGLISADRYSLFLVCEDSSNDKFLISRLFDVAEGSTLEEVSNNCIRLEWNKGIVGHVAALGEPLNIKDAYEDPRFNAEVDQITGYKTQSILCMPIKNHREEVVGVAQAINKKSGNGGTFTEKDEKDFAAYLAFCGIVLHNAQLYETSLLENKRNQVLLDLASLIFEEQQSLEVILKKIAATIISFMQVQKCTIFIVDEDCSDSFSSVFHMECEELEKSSDTLTREHDANKINYMYAQYVKNTMEPLNIPDVSKDKRFPWTTENTGNVNQQCIRSLLCTPIKNGKKNKVIGVCQLVNKMEENTGKVKPFNRNDEQFLEAFVIFCGLGIQNTQMYEAVERAMAKQMVTLEVLSYHASAAEEETRELQSLAAAVVPSAQTLKITDFSFSDFELSDLETALCTIRMFTDLNLVQNFQMKHEVLCRWILSVKKNYRKNVAYHNWRHAFNTAQCMFAALKAGKIQNKLTDLEILALLIAALSHDLDHRGVNNSYIQRSEHPLAQLYCHSIMEHHHFDQCLMILNSPGNQILSGLSIEEYKTTLKIIKQAILATDLALYIKRRGEFFELIRKNQFNLEDPHQKELFLAMLMTACDLSAITKPWPIQQRIAELVATEFFDQGDRERKELNIEPTDLMNREKKNKIPSMQVGFIDAICLQLYEALTHVSEDCFPLLDGCRKNRQKWQALAEQQEKMLINGESGQAKRN', 'query_input': 'PDE5A'}
```

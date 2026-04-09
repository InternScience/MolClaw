---
name: molclaw-fpocket-toolkit-base
description: Detect binding pockets with fpocket_toolkit and return parsed pocket descriptors and run artifacts.
license: MIT license
metadata:
    skill-author: PJLab
---

# fpocket_toolkit Pocket Detection

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `drugsda-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `drugsda-fix_pdb` before execution.

## Usage


### 2. Pocket Detection

The description of tool *fpocket_toolkit*.

```tex
Detect pockets with fpocket_toolkit and store every run under the tool_result/fpocket_result directory.
Args:
    pdb_file (str): Input PDB/mmCIF file to scan (required).
    top_n (int): Limit returned pockets to the top N (0 = all). Default: 0.
    min_druggability (float|None): Filter out pockets below this threshold. Default: None.
    verbose (bool): Enable verbose descriptor parsing during the run. Default: False.
Return:
    status (str): 'success' or 'error'.
    msg (str): Human-readable narrative about the run.
    run_dir (str): Absolute directory storing this run.
    output_dir (str): Path where fpocket preserved its outputs.
    pockets (List[Dict[str, Any]]): Parsed pocket descriptors, including scores and centers.
    pocket_count (int): Number of pockets returned.
    output_files (Dict[str, str]): Preserved fpocket output files.
    exported (Dict[str, str]|None): Export metadata when requested.
    files (Dict[str, str]): All files created under the run_dir.
```

How to use tool *fpocket_toolkit* :

```python
response = await client.session.call_tool(
    "fpocket_toolkit",
    arguments={
        "pdb_file": "/path/to/input.pdb",
        "top_n": 0,
        "min_druggability": None,
        "verbose": False,
    }
)
result = client.parse_result(response)
pockets = result.get("pockets")

```

#### Example parameter sets

```python
# 1) Main mode: analyze full structure and return all pockets (README example)
{
    "pdb_file": "/path/to/input.pdb",
    "top_n": 0,
    "min_druggability": None,
    "verbose": False,
}

# 2) Variant mode: return top 3 pockets above a druggability threshold
{
    "pdb_file": "/path/to/input.pdb",
    "top_n": 3,
    "min_druggability": 0.5,
    "verbose": True,
}
```


---

## ⚠ Docking Box Size Enforcement (L3 Principle 18)

When fpocket pocket dimensions are used for downstream docking (QuickVina, etc.), **enforce a minimum of 25.0 Å per dimension.** If any pocket dimension returned by fpocket is less than 25 Å, override it to 25.0 Å before passing to the docking tool.

```python
# After fpocket pocket detection:
size_x = max(25.0, pocket["size_x"])
size_y = max(25.0, pocket["size_y"])
size_z = max(25.0, pocket["size_z"])
```


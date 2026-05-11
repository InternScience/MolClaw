---
name: molclaw-diffdock-auto
description: "[CURRENTLY UNAVAILABLE] DiffDock protein-ligand docking. This tool is not deployed on the current MCP server. Use molclaw-quickvina-docking or molclaw-karmadock-tool as alternatives."
license: MIT license
metadata:
    skill-author: PJLab
---

# DiffDock Automated Protein-Ligand Docking

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

> **⚠ TOOL NOT AVAILABLE:** The `diffdock_auto` tool is **not currently deployed** on the MCP server. The DiffDock API endpoint is disabled. **Do NOT attempt to call `diffdock_auto`.** Use one of these alternatives instead:
> - **`molecule_docking_quickvina_fullprocess`** — GPU-accelerated AutoDock Vina variant (see skill `molclaw-quickvina-docking`)
> - **`karmadock_tool`** — ML-based docking (see skill `molclaw-karmadock-tool`)

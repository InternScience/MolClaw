---
name: molclaw-scp-server
description: All tools utilized within molclaw skills connect via the MCP protocol. This skill serves as a unified guide for using the MCP Server. This skill must be loaded to create the MCP server before invoking any tools. 
license: MIT license
metadata:
    skill-author: PJLab
---

# MCP Usage


### 2. MCP Server Connection

The **initialization** and **shutdown** of the MCP server are shown below:

```python
## When start, connect the MCP server
client = DrugSDAClient()
if not await client.connect(server_url):
    print("connection failed")
    return

## When finish, disconnect the MCP server
await client.disconnect() 
```

**Note**: For most tools, the default MCP server endpoint (`server_url`) is `https://scp.intern-ai.org.cn/api/v1/mcp/2/DrugSDA-Tool`. However, for the specific tools listed below, the `server_url` is `http://180.184.86.2:32208/mcp`.

```tex
evobind_tool (molclaw-evobind-tool)
gmx_mmpbsa_workflow (molclaw-protein-ligand-mmpbsa)
gmx_mmpbsa_propro (molclaw-protein-protein-mmpbsa)
run_openawsem_simulation (molclaw-openawsem-tool)
pred_binding_affinity_boltz2 (molclaw-boltz2-affinity)
```

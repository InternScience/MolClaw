---
name: molclaw-file-transfer
description: Implement data transmission between the local computer and the MCP Server using Base64 encoding 
license: MIT license
metadata:
    skill-author: PJLab
---

# File Transfer

### 1. Transfer local file to MCP server

Example code:

```python
import base64

client = DrugSDAClient("https://scp.intern-ai.org.cn/api/v1/mcp/2/DrugSDA-Tool")
if not await client.connect():
    print("connection failed")
    return

## Convert local file to base64 string
local_file = "/path/a.txt"		#Input local file path
with open(local_file, "rb") as f:
    file_content = f.read()
    file_base64_string = base64.b64encode(file_content).decode('utf-8')

## Call tool base64_to_server_file to save base64 string as server file
response = await client.session.call_tool(
    "base64_to_server_file",
    arguments={
        "file_name": "a.txt",
        "file_base64_string": file_base64_string
    }
)
result = client.parse_result(response)
save_file = result["save_file"]	#Server file path after transfer	

await client.disconnect() 
```

### 2. Transfer MCP server file to local

Example code:

```python
import base64

client = DrugSDAClient("https://scp.intern-ai.org.cn/api/v1/mcp/2/DrugSDA-Tool")
if not await client.connect():
    print("connection failed")
    return

## Call tool server_file_to_base64 to convert server file to base64 string
response = await client.session.call_tool(
    "server_file_to_base64",
    arguments={
        "file_path": "/path/a.txt" 	#Input server file path
    }
)
result = client.parse_result(response)
base64_string = result["base64_string"]
file_name = result["file_name"]

## Convert base64 string to local file
file_data = base64.b64decode(base64_string)    
local_file_path = "/path/" + file_name
with open(local_file_path, "wb") as f:
    f.write(file_data)

await client.disconnect()
```


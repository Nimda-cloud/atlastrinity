---
name: MCP Monitoring & Operations
description: Instructions for monitoring and managing MCP (Model Context Protocol) servers.
---

# MCP Monitoring & Operations

This skill provides instructions for identifying, monitoring, and debugging MCP servers in the AtlasTrinity system.

## 1. Enumerating Active MCP Servers

To list all currently active and connected MCP servers, DO NOT search for manual command line tools. Instead, use the dedicated health check script:

```bash
python scripts/check_mcp_health.py
```

This script will output:

- A list of all configured MCP servers.
- Their connection status (ONLINE/OFFLINE).
- Latency (ping).
- A summary of overall system health.

### Example Output

```
  ✓ react-devtools         T3     ONLINE        1       168ms
  ✓ googlemaps             T3     ONLINE        1       120ms
  ...
  ✓ Summary: 19 online, 0 degraded, 0 offline (of 19 total)
  ✓ Health: 100%
```

## 2. Inspecting MCP Configuration

To see the raw configuration of MCP servers (what command launches them, their environment variables, etc.):

```bash
cat config/mcp_servers.json.template
# OR (if deployed)
cat ~/.config/atlastrinity/mcp/config.json
```

## 3. Debugging Connection Issues

If a server is reported OFFLINE in step 1:

1. Check the logs for that specific server in `~/.config/atlastrinity/logs/` (e.g., `googlemaps_server.log` if available, or `brain.log`).
2. Verify the server's binary or script path exists.
3. Check `scripts/check_mcp_health.py --verbose` (if supported) or just run the health check again to see if it was transient.

## 4. Verification

When verifying steps related to MCP server logic:

- Always run `python scripts/check_mcp_health.py` to confirm the server is actually reachable.
- Do NOT assume a server is running just because the process exists; the connection must be established.

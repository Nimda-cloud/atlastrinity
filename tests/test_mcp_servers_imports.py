import ast
from pathlib import Path


def test_servers_use_mcp_package():
    server_dir = Path("src/mcp_server")
    py_files = list(server_dir.glob("*.py"))
    assert py_files, "No server files found"
    for p in py_files:
        src = p.read_text()
        # Only consider files that define a 'server' variable (i.e., actual MCP servers)
        if "server =" not in src:
            continue
        tree = ast.parse(src)
        imports = [n for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom)]
        found = False
        for imp in imports:
            if isinstance(imp, ast.ImportFrom):
                if imp.module and imp.module.startswith("mcp.server"):
                    found = True
                    break
        assert found, f"{p} does not import from 'mcp.server' (migration incomplete)"

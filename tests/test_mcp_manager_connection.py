import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from src.brain.mcp_manager import MCPManager


@asynccontextmanager
async def fake_stdio_client(server_params):
    # Simulate a simple stdio client context
    class DummyStream:
        pass

    try:
        yield DummyStream(), DummyStream()
    finally:
        # nothing special
        pass

class FakeClientSession:
    def __init__(self, read, write):
        self.read = read
        self.write = write
        self.initialized = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def initialize(self):
        # emulate some small initialization delay
        await asyncio.sleep(0)
        self.initialized = True

    async def list_tools(self):
        return SimpleNamespace(tools=["a", "b"])

@pytest.mark.asyncio
async def test_connect_and_cleanup(monkeypatch):
    mm = MCPManager()

    # Monkeypatch stdio_client and ClientSession used in the module
    monkeypatch.setattr("src.brain.mcp_manager.stdio_client", fake_stdio_client)
    monkeypatch.setattr("src.brain.mcp_manager.ClientSession", FakeClientSession)

    server_cfg = {"command": "echo", "args": []}

    session = await mm._connect_server("test-server", server_cfg)
    assert session is not None

    tools = await mm.list_tools("test-server")
    assert tools == ["a", "b"]

    # Put the server config into manager config so restart can reconnect
    mm.config.setdefault("mcpServers", {})["test-server"] = server_cfg

    # restart (will signal old task to shut down and reconnect)
    ok = await mm.restart_server("test-server")
    assert ok

    # cleanup should close remaining connection tasks
    await mm.cleanup()
    assert mm.get_status()["session_count"] == 0

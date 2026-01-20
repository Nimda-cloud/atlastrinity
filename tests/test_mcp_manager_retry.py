import errno

import pytest

from src.brain.mcp_manager import MCPManager


@pytest.mark.asyncio
async def test_restart_retry_success(monkeypatch):
    manager = MCPManager()
    manager.config = {"mcpServers": {"foo": {}}}
    calls = {"n": 0}

    async def fake_connect(server_name, cfg):
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError(errno.EAGAIN, "Resource temporarily unavailable")
        return object()

    monkeypatch.setattr(manager, "_connect_server", fake_connect)
    res = await manager.restart_server("foo")
    assert res is True
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_restart_retry_fail(monkeypatch):
    manager = MCPManager()
    manager.config = {"mcpServers": {"bar": {}}}
    manager._max_restart_attempts = 3

    async def always_fail(server_name, cfg):
        raise OSError(errno.EAGAIN, "Resource temporarily unavailable")

    monkeypatch.setattr(manager, "_connect_server", always_fail)
    res = await manager.restart_server("bar")
    assert res is False

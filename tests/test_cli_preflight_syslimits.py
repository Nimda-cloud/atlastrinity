import json


from scripts import check_mcp_preflight as cli


def test_syslimits_warning_default(monkeypatch, tmp_path):
    cfg = {"mcpServers": {}}
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps(cfg))

    # Monkeypatch package scanner to return no package issues but system check to return an issue
    monkeypatch.setattr("src.brain.mcp_preflight.scan_mcp_config_for_package_issues", lambda x: [])
    monkeypatch.setattr(
        "src.brain.mcp_preflight.check_system_limits",
        lambda: ["kern.maxproc is low: 2000 (global max procs). Consider increasing via sysctl)"],
    )

    # Default behavior: sys limits are warnings -> exit code 0
    rc = cli.run(str(p))
    assert rc == 0


def test_syslimits_fail_when_env_set(monkeypatch, tmp_path):
    cfg = {"mcpServers": {}}
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps(cfg))

    monkeypatch.setattr("src.brain.mcp_preflight.scan_mcp_config_for_package_issues", lambda x: [])
    monkeypatch.setattr(
        "src.brain.mcp_preflight.check_system_limits",
        lambda: ["kern.maxproc is low: 2000 (global max procs). Consider increasing via sysctl)"],
    )

    monkeypatch.setenv("FAIL_ON_SYS_LIMITS", "1")
    rc = cli.run(str(p))
    assert rc == 1

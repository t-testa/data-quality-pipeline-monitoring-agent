import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dqagent import cli
from dqagent.demo import rules, scenario_demo
from dqagent.source import sqlserver_reader, verify_readonly_identity


def test_sqlserver_configuration_fails_closed():
    with pytest.raises(ValueError):
        sqlserver_reader("sqlite:///x")
    with pytest.raises(ValueError):
        sqlserver_reader("mssql+pyodbc://host/database")


def test_elevated_sql_identity_rejected():
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.scalar.return_value = 1
    with pytest.raises(PermissionError):
        verify_readonly_identity(engine, rules())


def test_readonly_permission_checks():
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value

    def scalar(statement, args=None):
        return 1 if "'SELECT'" in str(statement) else 0

    connection.scalar.side_effect = scalar
    verify_readonly_identity(engine, rules())
    assert connection.scalar.call_count > 10


def test_cli_initialization_and_demo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["dqagent", "init"])
    cli.main()
    assert Path(".env").exists()
    with pytest.raises(FileExistsError):
        cli.main()
    monkeypatch.setattr(sys, "argv", ["dqagent", "demo", "success"])
    cli.main()
    assert Path("data/monitoring.sqlite").exists()


def test_explicit_run_scope_and_missing_evidence(client, store, headers):
    run = scenario_demo(store, "success")
    q = {"question": "why", "pipeline": "other", "run_id": run["id"]}
    assert client.post("/api/diagnose", json=q, headers=headers).status_code == 404
    q.pop("run_id")
    assert client.post("/api/diagnose", json=q, headers=headers).json()["facts"] == []
    assert client.get("/api/runs/bad", headers=headers).status_code == 404
    assert client.post("/api/tools/list_pipelines", json={}, headers=headers).status_code == 200
    assert client.post("/api/tools/execute_sql", json={}, headers=headers).status_code == 400


def test_mcp_proxies_authenticated_request(monkeypatch):
    import asyncio
    import json

    from dqagent.mcp_server import make_server

    monkeypatch.setenv("DQ_MCP_TOKEN", "r" * 40)
    mock_client = MagicMock()
    connection = mock_client.return_value.__enter__.return_value
    response = connection.stream.return_value.__enter__.return_value
    response.status_code = 200
    response.iter_bytes.return_value = [json.dumps({"data": [], "limit": 30, "bounded": True}).encode()]
    monkeypatch.setattr("dqagent.mcp_server.httpx.Client", mock_client)
    result = asyncio.run(make_server().call_tool("list_pipelines", {}))
    assert result
    assert connection.stream.call_args.kwargs["headers"]["Authorization"] == "Bearer " + "r" * 40
    response.status_code = 401
    with pytest.raises(Exception, match="denied"):
        asyncio.run(make_server().call_tool("list_pipelines", {}))

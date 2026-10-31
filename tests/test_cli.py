"""`gmc-mcp run` picks the transport and passes host and port through."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from gmc_mcp import cli


class _FakeServer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, transport: str, **kwargs: Any) -> None:
        self.calls.append((transport, kwargs))


@pytest.fixture
def fake_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sa = tmp_path / "sa.json"
    sa.write_text("{}")
    monkeypatch.setenv("GMC_ACCOUNT_ID", "1234567890")
    monkeypatch.setenv("GMC_SERVICE_ACCOUNT_KEY", str(sa))
    monkeypatch.setenv("GMC_AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    for var in ("GMC_OAUTH_TOKEN", "GMC_TRANSPORT", "GMC_HOST", "GMC_PORT", "GMC_TOOL_GROUPS"):
        monkeypatch.delenv(var, raising=False)
    server = _FakeServer()
    monkeypatch.setattr(cli, "build_server", lambda config: server)
    warnings: list[str] = []
    monkeypatch.setattr(cli.logger, "warning", lambda msg, *args: warnings.append(msg % args))

    def invoke(*args: str):
        env_file = str(tmp_path / "missing.env")
        result = CliRunner().invoke(cli.cli, ["--env", env_file, *args, "run"], obj={})
        assert result.exit_code == 0, result.output
        return server.calls, warnings

    return invoke


def test_stdio_is_the_default(fake_run) -> None:
    calls, warnings = fake_run()
    assert calls == [("stdio", {})]
    assert warnings == []


def test_streamable_http_gets_host_and_port(fake_run) -> None:
    calls, warnings = fake_run("--transport", "streamable-http", "--port", "9123")
    assert calls == [("streamable-http", {"host": "127.0.0.1", "port": 9123})]
    assert warnings == []


def test_sse_still_works_but_warns(fake_run) -> None:
    calls, warnings = fake_run("--transport", "sse")
    assert calls == [("sse", {"host": "127.0.0.1", "port": 8000})]
    assert any("deprecated" in w for w in warnings)


def test_non_loopback_host_warns(fake_run) -> None:
    calls, warnings = fake_run("--transport", "streamable-http", "--host", "0.0.0.0")
    assert calls[0][1]["host"] == "0.0.0.0"
    assert any("no authentication" in w for w in warnings)


def test_unknown_transport_is_rejected() -> None:
    result = CliRunner().invoke(cli.cli, ["--transport", "websocket", "run"], obj={})
    assert result.exit_code != 0
    assert "streamable-http" in result.output

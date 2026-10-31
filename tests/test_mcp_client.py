"""End-to-end tests through `mcp.Client` against the real server (fake auth, mocked HTTP)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import Tool

from gmc_mcp import __version__, server, tools
from gmc_mcp.client import BASE_URL, MerchantClient
from gmc_mcp.config import Config, load_config
from gmc_mcp.tool_catalog import ALWAYS_REGISTERED, TOOL_SPECS

from .conftest import FakeAuth

ACCT = "accounts/1234567890"
META_TOOLS = ["gmc_describe_server", "gmc_audit_lookup", "gmc_audit_tail", "gmc_set_dry_run"]


@pytest.fixture(autouse=True)
def fake_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "load_auth", lambda **_: FakeAuth())


def _build(config: Config, **changes: Any) -> MCPServer:
    return server.build_server(dataclasses.replace(config, **changes))


async def _tools(mcp: MCPServer) -> list[Tool]:
    async with Client(mcp) as c:
        return (await c.list_tools()).tools


def _group_tool_names(client: MerchantClient) -> dict[str, list[str]]:
    """Tool names per group, by registering each module on its own server."""
    out: dict[str, list[str]] = {}
    for group in tools.TOOL_GROUPS:
        mcp = MCPServer("probe")
        getattr(tools, group).register(mcp, client)
        out[group] = list(mcp._tool_manager._tools)
    return out


# ---------------------------------------------------------------- metadata


async def test_server_reports_version_and_instructions(config: Config) -> None:
    async with Client(_build(config)) as c:
        assert c.server_info is not None
        assert c.server_info.name == "gmc-mcp"
        assert c.server_info.version == __version__
        assert c.instructions
        assert "gmc_describe_server" in c.instructions
        assert "GMC_TOOL_GROUPS" in c.instructions
        assert 4 <= len(c.instructions.splitlines()) <= 8


async def test_every_tool_has_a_title_and_annotations(config: Config) -> None:
    listed = await _tools(_build(config))
    assert len(listed) == 166
    for tool in listed:
        assert tool.title, tool.name
        assert tool.title[0].isupper(), tool.name
        a = tool.annotations
        assert a is not None, tool.name
        assert a.read_only_hint is not None, tool.name
        assert a.destructive_hint is not None, tool.name
        assert a.idempotent_hint is not None, tool.name
        assert a.open_world_hint is not None, tool.name
    # The catalog has no stale entries either.
    assert {t.name for t in listed} == set(TOOL_SPECS)


async def test_read_only_set_is_plausible(config: Config) -> None:
    by_name = {t.name: t.annotations for t in await _tools(_build(config))}
    read_only = {n for n, a in by_name.items() if a and a.read_only_hint}
    destructive = {n for n, a in by_name.items() if a and a.destructive_hint}

    assert 70 <= len(read_only) <= 100
    assert not read_only & destructive
    for name in by_name:
        if name.startswith(("gmc_list_", "gmc_get_", "gmc_lfp_list_", "gmc_lfp_get_")):
            assert name in read_only, name
        verb = name.removeprefix("gmc_").removeprefix("lfp_").split("_")[0]
        removes = {"delete", "remove", "unsubscribe", "unclaim", "reject", "unregister"}
        # gmc_remove_product_image_background only generates an image.
        if verb in removes and name != "gmc_remove_product_image_background":
            assert name in destructive, name
        if "_delete_" in name and not name.startswith("gmc_undelete_"):
            assert name in destructive, name
        if name.startswith(("gmc_create_", "gmc_update_", "gmc_insert_", "gmc_patch_")):
            assert name not in read_only, name
    # Read-only POSTs and generation.
    assert {
        "gmc_query_report",
        "gmc_render_product_issues",
        "gmc_disapprovals_overview",
        "gmc_list_disapproved_products",
        "gmc_summarize_product_issues",
        "gmc_health_check",
        "gmc_generate_product_text_suggestions",
        "gmc_upscale_product_image",
    } <= read_only
    assert {"gmc_bulk_delete_products", "gmc_rollback", "gmc_delete_account"} <= destructive
    # Only the server-local tools are closed-world.
    closed = {n for n, a in by_name.items() if a and a.open_world_hint is False}
    assert closed == set(META_TOOLS)


async def test_tools_list_order_is_deterministic(config: Config, client: MerchantClient) -> None:
    first = [t.name for t in await _tools(_build(config))]
    second = [t.name for t in await _tools(_build(config))]
    assert first == second
    per_group = _group_tool_names(client)
    expected = META_TOOLS + [n for g in tools.TOOL_GROUPS for n in per_group[g]]
    assert first == expected


# ---------------------------------------------------------------- filtering


async def test_tool_groups_limit_registration(config: Config, client: MerchantClient) -> None:
    names = [t.name for t in await _tools(_build(config, tool_groups=["reports", "products"]))]
    per_group = _group_tool_names(client)
    assert names == META_TOOLS + per_group["products"] + per_group["reports"]


async def test_read_only_registers_only_read_tools(config: Config) -> None:
    listed = await _tools(_build(config, read_only=True))
    names = {t.name for t in listed}
    assert set(META_TOOLS) <= names
    for tool in listed:
        if tool.name not in ALWAYS_REGISTERED:
            assert tool.annotations and tool.annotations.read_only_hint, tool.name
    assert "gmc_delete_product" not in names
    assert "gmc_list_products" in names
    expected = {n for n, s in TOOL_SPECS.items() if s.annotations.read_only_hint}
    assert names == expected | set(META_TOOLS)


async def test_read_only_combines_with_groups(config: Config) -> None:
    names = {t.name for t in await _tools(_build(config, tool_groups=["bulk"], read_only=True))}
    assert names == set(META_TOOLS)


def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **values: str) -> Path:
    sa = tmp_path / "sa.json"
    sa.write_text("{}")
    monkeypatch.setenv("GMC_ACCOUNT_ID", "1234567890")
    monkeypatch.setenv("GMC_SERVICE_ACCOUNT_KEY", str(sa))
    monkeypatch.setenv("GMC_AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    for var in ("GMC_OAUTH_TOKEN", "GMC_SUBACCOUNT_ID", "GMC_TOOL_GROUPS", "GMC_READ_ONLY"):
        monkeypatch.delenv(var, raising=False)
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    return tmp_path / "missing.env"


async def test_env_vars_filter_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = _env(monkeypatch, tmp_path, GMC_TOOL_GROUPS="issues,quotas", GMC_READ_ONLY="1")
    names = {t.name for t in await _tools(server.build_server(env_file=env_file))}
    assert names == set(META_TOOLS) | {
        "gmc_list_account_issues",
        "gmc_get_product_status",
        "gmc_summarize_product_issues",
        "gmc_list_quotas",
        "gmc_list_account_limits",
        "gmc_get_account_limit",
    }


def test_unknown_group_fails_at_startup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = _env(monkeypatch, tmp_path, GMC_TOOL_GROUPS="products,nope")
    with pytest.raises(RuntimeError) as exc_info:
        server.build_server(env_file=env_file)
    message = str(exc_info.value)
    assert "nope" in message
    for group in tools.TOOL_GROUPS:
        assert group in message


def test_unknown_group_in_config_fails_at_startup(config: Config) -> None:
    with pytest.raises(RuntimeError, match="Valid groups"):
        _build(config, tool_groups=["nope"])


def test_load_config_rejects_unknown_group(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = _env(monkeypatch, tmp_path, GMC_TOOL_GROUPS="Products, NOPE")
    with pytest.raises(RuntimeError, match="unknown group"):
        load_config(env_file=env_file)


# ---------------------------------------------------------------- calls


@respx.mock
async def test_read_tool_returns_the_product(config: Config) -> None:
    pid = "online~en~US~SKU1"
    respx.get(f"{BASE_URL}/products/v1/{ACCT}/products/{pid}").mock(
        return_value=httpx.Response(200, json={"name": f"{ACCT}/products/{pid}", "title": "Widget"})
    )
    async with Client(_build(config)) as c:
        result = await c.call_tool("gmc_get_product", {"product_id": pid})
    assert not result.is_error
    payload = result.structured_content or json.loads(result.content[0].text)
    assert payload["title"] == "Widget"


@respx.mock
async def test_api_error_reaches_the_client(config: Config) -> None:
    pid = "online~en~US~MISSING"
    respx.get(f"{BASE_URL}/products/v1/{ACCT}/products/{pid}").mock(
        return_value=httpx.Response(404, json={"error": {"status": "NOT_FOUND"}})
    )
    async with Client(_build(config)) as c:
        result = await c.call_tool("gmc_get_product", {"product_id": pid})
    assert result.is_error
    text = " ".join(getattr(block, "text", "") for block in result.content)
    assert "Merchant API error 404" in text
    assert "NOT_FOUND" in text


async def test_describe_server_reports_filters(config: Config) -> None:
    async with Client(_build(config, tool_groups=["reports"], read_only=True)) as c:
        result = await c.call_tool("gmc_describe_server", {})
    payload = result.structured_content or json.loads(result.content[0].text)
    assert payload["tool_groups"] == ["reports"]
    assert payload["read_only"] is True
    assert payload["version"] == __version__


@respx.mock
async def test_bulk_tool_reports_progress_per_item(config: Config) -> None:
    ids = ["online~en~US~A", "online~en~US~B", "online~en~US~C"]
    for pid in ids:
        respx.post(
            f"{BASE_URL}/inventories/v1/{ACCT}/products/{pid}/regionalInventories:insert"
        ).mock(return_value=httpx.Response(200, json={}))

    updates: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        updates.append((progress, total, message))

    async with Client(_build(config)) as c:
        result = await c.call_tool(
            "gmc_bulk_set_availability",
            {"product_ids": ids, "region": "US", "availability": "in_stock", "confirm": "APPLY"},
            progress_callback=on_progress,
        )
    assert not result.is_error
    payload = result.structured_content or json.loads(result.content[0].text)
    assert payload["applied_count"] == 3
    assert [(p, t) for p, t, _ in updates] == [(1, 3), (2, 3), (3, 3)]
    assert updates[-1][2] == "Updated online~en~US~C (3 of 3)"


@respx.mock
async def test_bulk_delete_reports_progress_and_audits(config: Config) -> None:
    products = [
        {"name": f"{ACCT}/products/en~US~{sku}", "dataSource": f"{ACCT}/dataSources/1"}
        for sku in ("A", "B")
    ]
    respx.get(f"{BASE_URL}/products/v1/{ACCT}/products").mock(
        return_value=httpx.Response(200, json={"products": products})
    )
    deletes = respx.delete(url__regex=rf"{BASE_URL}/products/v1/{ACCT}/productInputs/.*").mock(
        return_value=httpx.Response(204)
    )
    seen: list[float] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        seen.append(progress)

    async with Client(_build(config)) as c:
        result = await c.call_tool(
            "gmc_bulk_delete_products", {"confirm": "DELETE"}, progress_callback=on_progress
        )
    payload = result.structured_content or json.loads(result.content[0].text)
    assert payload["deleted_count"] == 2
    assert deletes.call_count == 2
    assert seen == [0, 1, 2]
    audit = [json.loads(line) for line in config.audit_log.read_text().splitlines()]
    assert [e["op"] for e in audit] == ["bulk_delete_product", "bulk_delete_product"]


async def test_bulk_tool_dry_run_sends_nothing(config: Config) -> None:
    with respx.mock(assert_all_called=False) as router:
        route = router.post(url__regex=r".*regionalInventories:insert").mock(
            return_value=httpx.Response(200, json={})
        )
        async with Client(_build(config, dry_run=True)) as c:
            result = await c.call_tool(
                "gmc_bulk_set_availability",
                {
                    "product_ids": ["x"],
                    "region": "US",
                    "availability": "IN_STOCK",
                    "confirm": "APPLY",
                },
            )
    payload = result.structured_content or json.loads(result.content[0].text)
    assert payload["applied_count"] == 1
    assert not route.called


def test_version_matches_pyproject_and_server_json() -> None:
    root = Path(__file__).resolve().parent.parent
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert f'\nversion = "{__version__}"\n' in pyproject
    manifest = json.loads((root / "server.json").read_text(encoding="utf-8"))
    assert manifest["version"] == __version__
    assert {p["version"] for p in manifest["packages"]} == {__version__}

"""Tool errors must reach the client: MCP SDK 2 hides unexpected exception text."""

from __future__ import annotations

import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from gmc_mcp.client import MerchantAPIError
from gmc_mcp.server import GmcMCPServer


def _server() -> GmcMCPServer:
    mcp = GmcMCPServer("test")

    @mcp.tool()
    def gmc_refuses(confirm: str = "") -> dict:
        """Refuses unless confirmed."""
        raise ValueError("Pass confirm='DELETE' to proceed.")

    @mcp.tool()
    def gmc_api_fails() -> dict:
        """Fails like the Merchant API."""
        raise MerchantAPIError(403, {"error": {"status": "PERMISSION_DENIED"}})

    @mcp.tool()
    def gmc_crashes() -> dict:
        """Crashes with an unexpected error."""
        raise KeyError("internal detail")

    return mcp


@pytest.mark.parametrize(
    ("tool", "message"),
    [
        ("gmc_refuses", "Pass confirm='DELETE' to proceed."),
        ("gmc_api_fails", "Merchant API error 403"),
    ],
)
def test_expected_errors_keep_their_message(tool: str, message: str) -> None:
    with pytest.raises(ToolError, match=message.split(":")[0]):
        asyncio.run(_server().call_tool(tool, {}))


def test_unexpected_errors_stay_hidden() -> None:
    with pytest.raises(Exception) as exc_info:
        asyncio.run(_server().call_tool("gmc_crashes", {}))
    assert "internal detail" not in str(exc_info.value)


def test_wrapper_keeps_the_tool_schema() -> None:
    tools = {t.name: t for t in asyncio.run(_server().list_tools())}
    assert "confirm" in tools["gmc_refuses"].input_schema["properties"]

"""Build the MCP server. Stays import-light so tests can patch pieces individually."""

from __future__ import annotations

import functools
import inspect
import json
from pathlib import Path
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import __version__, tools
from ._logging import configure_default, get_logger
from .audit import AuditLog
from .auth import load_auth
from .client import MerchantAPIError, MerchantClient
from .config import Config, load_config
from .tool_catalog import ALWAYS_REGISTERED, TOOL_SPECS

logger = get_logger("server")

INSTRUCTIONS = """\
Google Merchant Center (Merchant API v1): products, inventory, feeds, issues, reports, promotions, settings.
Start with gmc_describe_server and gmc_health_check; for disapprovals, gmc_disapprovals_overview.
Writes hit the live account. Rehearse with dry-run (gmc_set_dry_run or GMC_DRY_RUN): logged, not sent.
Bulk/batch tools, gmc_delete_account and gmc_rollback need confirm (e.g. 'DELETE'); other deletes don't.
Every write goes to an audit log (gmc_audit_tail); gmc_rollback undoes one that has a before snapshot.
Tools can be limited with GMC_TOOL_GROUPS (module names) or GMC_READ_ONLY=true."""

# Errors whose message helps the agent fix the call (bad arguments, a refusal
# such as a missing confirm, Merchant API errors, permissions or config problems).
_EXPECTED_ERRORS = (
    ValueError,
    RuntimeError,
    PermissionError,
    FileNotFoundError,
    MerchantAPIError,
    httpx.HTTPError,
)


def _as_tool_error(fn):
    """Re-raises expected errors as ToolError so MCP SDK 2 shows their message.

    SDK 2 hides the text of any other exception from the client.
    """
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except _EXPECTED_ERRORS as exc:
                raise ToolError(str(exc)) from exc

        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except _EXPECTED_ERRORS as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


class GmcMCPServer(MCPServer):
    """MCPServer whose tools report expected errors to the client.

    Each tool gets its title and annotations from `tool_catalog.TOOL_SPECS`
    unless the decorator passes them. With `read_only=True`, tools that are not
    annotated read-only are skipped (the meta tools are always registered).
    """

    def __init__(self, *args: Any, read_only: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.read_only = read_only

    def tool(  # type: ignore[override]
        self,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        **kwargs: Any,
    ):
        def decorator(fn):
            tool_name = name or fn.__name__
            spec = TOOL_SPECS.get(tool_name)
            tool_title = title or (spec.title if spec else None)
            tool_annotations = annotations or (spec.annotations if spec else None)
            is_read_only = bool(tool_annotations and tool_annotations.read_only_hint)
            if self.read_only and not is_read_only and tool_name not in ALWAYS_REGISTERED:
                return fn
            register = super(GmcMCPServer, self).tool(
                name=name,
                title=tool_title,
                description=description,
                annotations=tool_annotations,
                **kwargs,
            )
            register(_as_tool_error(fn))
            return fn

        return decorator


def build_server(config: Config | None = None, env_file: Path | None = None) -> MCPServer:
    """Construct an MCPServer instance with all gmc_* tools registered."""
    configure_default()
    if config is None:
        config = load_config(env_file=env_file)
    groups = tools.resolve_tool_groups(config.tool_groups)  # fail fast on unknown groups

    auth = load_auth(
        service_account_key=config.service_account_key,
        oauth_token=config.oauth_token,
    )
    audit = AuditLog(config.audit_log)
    client = MerchantClient(config, auth, audit)

    logger.info(
        "starting gmc-mcp account=%s subaccount=%s auth=%s dry_run=%s",
        config.account_id,
        config.subaccount_id or "-",
        auth.account_label,
        config.dry_run,
    )

    mcp = GmcMCPServer(
        "gmc-mcp",
        title="Google Merchant Center",
        version=__version__,
        instructions=INSTRUCTIONS,
        read_only=config.read_only,
    )

    @mcp.tool()
    def gmc_describe_server() -> dict[str, Any]:
        """Show what this server is connected to and how it's configured."""
        return {
            "account_id": config.account_id,
            "subaccount_id": config.subaccount_id,
            "effective_account_id": config.effective_account_id,
            "auth": auth.account_label,
            "audit_log": str(config.audit_log),
            "dry_run": config.dry_run,
            "page_size": config.page_size,
            "timeout": config.timeout,
            "transport": config.transport,
            "version": __version__,
            "tool_groups": config.tool_groups or "all",
            "read_only": config.read_only,
        }

    @mcp.tool()
    def gmc_audit_lookup(audit_id: str) -> dict[str, Any]:
        """Look up an audit log entry by ID. Useful for diagnosing failed writes or rolling back."""
        entry = audit.find(audit_id)
        if not entry:
            return {"found": False, "audit_id": audit_id}
        return {"found": True, "entry": entry}

    @mcp.tool()
    def gmc_audit_tail(limit: int = 20) -> dict[str, Any]:
        """Show the most recent audit log entries."""
        if not config.audit_log.exists():
            return {"count": 0, "entries": []}
        with config.audit_log.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        entries = [json.loads(line) for line in lines]
        return {"count": len(entries), "entries": entries}

    @mcp.tool()
    def gmc_set_dry_run(enabled: bool) -> dict[str, Any]:
        """Toggle dry-run mode for this session. When enabled, write operations
        are recorded to the audit log but NOT sent to Merchant API."""
        client.config.dry_run = enabled
        logger.info("dry_run=%s (set via tool)", enabled)
        return {"dry_run": enabled}

    for group in groups:
        getattr(tools, group).register(mcp, client)

    logger.info(
        "registered %d tools (groups=%s read_only=%s)",
        len(mcp._tool_manager.list_tools()),
        ",".join(config.tool_groups) or "all",
        config.read_only,
    )
    return mcp

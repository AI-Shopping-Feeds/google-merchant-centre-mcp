from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    @mcp.tool()
    def gmc_list_quotas(max_pages: int = 5) -> dict[str, Any]:
        """List the API quota usage / limits for this account.

        Useful to monitor before hitting rate limits. Returns one entry per
        quota group (e.g. ProductsService, ReportsService).
        """
        items = list(
            client.paginate(
                "GET",
                f"quota/v1/{acct}/quotas",
                items_key="quotaGroups",
                max_pages=max_pages,
            )
        )
        rows = []
        for q in items:
            rows.append(
                {
                    "method": q.get("methodDetails", []),
                    "quota_usage": q.get("quotaUsage"),
                    "quota_limit": q.get("quotaLimit"),
                    "quota_minute_limit": q.get("quotaMinuteLimit"),
                }
            )
        return {"count": len(items), "quotas_raw": items, "summary": rows}

    @mcp.tool()
    def gmc_list_account_limits(
        limit_type: str = "products", max_pages: int = 5
    ) -> dict[str, Any]:
        """List account limits (e.g. maximum number of products per scope).

        limit_type: the limit type to filter on; the API requires a type filter and
            currently supports 'products'.
        """
        items = list(
            client.paginate(
                "GET",
                f"quota/v1/{acct}/limits",
                params={"filter": f'type = "{limit_type}"'},
                items_key="accountLimits",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "limits": items}

    @mcp.tool()
    def gmc_get_account_limit(limit_id: str) -> dict[str, Any]:
        """Get one account limit, e.g. limit_id='products~ADS_NON_EEA'."""
        return client.request("GET", f"quota/v1/{acct}/limits/{limit_id}")

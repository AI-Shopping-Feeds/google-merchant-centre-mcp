"""Multi-Client-Account (MCA) features: account relationships and account services.

For agencies and SaaS that manage multiple client Merchant Center accounts
under one parent. In Merchant API v1, aggregation (making this account a
sub-account of an aggregator) is an account *service* of type
ACCOUNT_AGGREGATION: propose it with gmc_propose_account_service and have the
other side approve it."""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient

# AccountService is a oneof: exactly one of these keys is set on the body.
SERVICE_TYPES = {
    "ACCOUNT_AGGREGATION": "accountAggregation",
    "ACCOUNT_MANAGEMENT": "accountManagement",
    "CAMPAIGNS_MANAGEMENT": "campaignsManagement",
    "COMPARISON_SHOPPING": "comparisonShopping",
    "PRODUCTS_MANAGEMENT": "productsManagement",
    "LOCAL_LISTING_MANAGEMENT": "localListingManagement",
}


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()
    rel_base = f"accounts/v1/{acct}/relationships"
    svc_base = f"accounts/v1/{acct}/services"

    # ---- Relationships ----

    @mcp.tool()
    def gmc_list_relationships(max_pages: int = 5) -> dict[str, Any]:
        """List account relationships (providers/aggregators linked to this account)."""
        items = list(
            client.paginate(
                "GET",
                rel_base,
                items_key="accountRelationships",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "relationships": items}

    @mcp.tool()
    def gmc_get_relationship(relationship_id: str) -> dict[str, Any]:
        """Get one account relationship. relationship_id is the provider account ID."""
        return client.request("GET", f"{rel_base}/{relationship_id}")

    @mcp.tool()
    def gmc_update_relationship(
        relationship_id: str,
        relationship: dict[str, Any],
        update_mask: str = "accountIdAlias",
    ) -> dict[str, Any]:
        """Patch an account relationship. Only `accountIdAlias` is mutable.

        relationship example: {"accountIdAlias": "client-a"}
        """
        before = client.snapshot(f"{rel_base}/{relationship_id}")
        return client.request(
            "PATCH",
            f"{rel_base}/{relationship_id}",
            params={"updateMask": update_mask},
            json_body=relationship,
            op="update_relationship",
            before=before,
        )

    # ---- Account services (delegation / aggregation) ----

    @mcp.tool()
    def gmc_list_account_services(max_pages: int = 5) -> dict[str, Any]:
        """List account services (who provides what to this account, and handshake state)."""
        items = list(
            client.paginate(
                "GET",
                svc_base,
                items_key="accountServices",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "services": items}

    @mcp.tool()
    def gmc_get_account_service(service_id: str) -> dict[str, Any]:
        """Get one account service by ID."""
        return client.request("GET", f"{svc_base}/{service_id}")

    @mcp.tool()
    def gmc_propose_account_service(
        provider: str,
        service_type: str,
        external_account_id: str | None = None,
    ) -> dict[str, Any]:
        """Propose an account service between this account and a provider.

        provider: full account name like 'accounts/PROVIDER_ID'.
        service_type: 'ACCOUNT_AGGREGATION' | 'ACCOUNT_MANAGEMENT' |
            'CAMPAIGNS_MANAGEMENT' | 'COMPARISON_SHOPPING' | 'PRODUCTS_MANAGEMENT' |
            'LOCAL_LISTING_MANAGEMENT'.
        external_account_id: optional ID the provider uses for this account.
        The other party must approve with gmc_approve_account_service.
        """
        key = SERVICE_TYPES.get(service_type.upper())
        if not key:
            return {"error": f"service_type must be one of {sorted(SERVICE_TYPES)}"}
        service: dict[str, Any] = {key: {}}
        if external_account_id:
            service["externalAccountId"] = external_account_id
        return client.request(
            "POST",
            f"{svc_base}:propose",
            json_body={"provider": provider, "accountService": service},
            op="propose_service",
        )

    @mcp.tool()
    def gmc_approve_account_service(service_id: str) -> dict[str, Any]:
        """Approve a proposed account service."""
        return client.request(
            "POST",
            f"{svc_base}/{service_id}:approve",
            json_body={},
            op="approve_service",
        )

    @mcp.tool()
    def gmc_reject_account_service(service_id: str) -> dict[str, Any]:
        """Reject a proposed account service, or end an established one."""
        before = client.snapshot(f"{svc_base}/{service_id}")
        return client.request(
            "POST",
            f"{svc_base}/{service_id}:reject",
            json_body={},
            op="reject_service",
            before=before,
        )

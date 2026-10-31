"""Omnichannel settings + Google Business Profile (GBP) account linkage.

Used by retailers with physical stores to sync online + offline inventory and
appear in local search / Maps.
"""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    # ---- Omnichannel settings ----

    @mcp.tool()
    def gmc_list_omnichannel_settings(max_pages: int = 5) -> dict[str, Any]:
        """List per-region omnichannel settings."""
        items = list(
            client.paginate(
                "GET",
                f"accounts/v1/{acct}/omnichannelSettings",
                items_key="omnichannelSettings",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "settings": items}

    @mcp.tool()
    def gmc_get_omnichannel_settings(region_code: str) -> dict[str, Any]:
        return client.request(
            "GET", f"accounts/v1/{acct}/omnichannelSettings/{region_code}"
        )

    @mcp.tool()
    def gmc_create_omnichannel_settings(
        region_code: str, settings: dict[str, Any]
    ) -> dict[str, Any]:
        """Create omnichannel settings for a region.

        settings example:
            {
              "regionCode": "US",
              "lsfType": "GHLSF_FULL",
              "inStock": {"uri": "https://store.com/storefinder", "state": "ACTIVE"},
              "pickup": {"uri": "https://store.com/pickup", "state": "ACTIVE"}
            }
        """
        body = dict(settings)
        body.setdefault("regionCode", region_code)
        return client.request(
            "POST",
            f"accounts/v1/{acct}/omnichannelSettings",
            json_body=body,
            op="create_omnichannel_settings",
        )

    @mcp.tool()
    def gmc_update_omnichannel_settings(
        region_code: str,
        settings: dict[str, Any],
        update_mask: str | None = None,
    ) -> dict[str, Any]:
        before = client.snapshot(f"accounts/v1/{acct}/omnichannelSettings/{region_code}")
        params = {"updateMask": update_mask} if update_mask else None
        return client.request(
            "PATCH",
            f"accounts/v1/{acct}/omnichannelSettings/{region_code}",
            params=params,
            json_body=settings,
            op="update_omnichannel_settings",
            before=before,
        )

    @mcp.tool()
    def gmc_request_inventory_verification(region_code: str) -> dict[str, Any]:
        """Request Google to verify your inventory accuracy in a region."""
        return client.request(
            "POST",
            f"accounts/v1/{acct}/omnichannelSettings/{region_code}:requestInventoryVerification",
            json_body={},
            op="request_inventory_verification",
        )

    # ---- LFP providers ----

    @mcp.tool()
    def gmc_find_lfp_providers(region_code: str, max_pages: int = 5) -> dict[str, Any]:
        """Find Local Feed Partnership (LFP) providers available in a region.

        region_code: the omnichannel setting's region (e.g. 'US').
        """
        items = list(
            client.paginate(
                "GET",
                f"accounts/v1/{acct}/omnichannelSettings/{region_code}/lfpProviders:find",
                items_key="lfpProviders",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "lfp_providers": items}

    @mcp.tool()
    def gmc_link_lfp_provider(
        region_code: str, lfp_provider_id: str, external_account_id: str
    ) -> dict[str, Any]:
        """Link an LFP provider to this account's omnichannel setting for a region.

        lfp_provider_id: provider ID from gmc_find_lfp_providers (last path segment).
        external_account_id: this merchant's account ID in the provider's system.
        """
        before = client.snapshot(f"accounts/v1/{acct}/omnichannelSettings/{region_code}")
        return client.request(
            "POST",
            f"accounts/v1/{acct}/omnichannelSettings/{region_code}"
            f"/lfpProviders/{lfp_provider_id}:linkLfpProvider",
            json_body={"externalAccountId": external_account_id},
            op="link_lfp_provider",
            before=before,
        )

    # ---- GBP account linkage ----

    @mcp.tool()
    def gmc_link_gbp_account(gbp_email: str) -> dict[str, Any]:
        """Link a Google Business Profile account so its store locations sync to GMC.

        gbp_email: the email of the GBP account owner.
        """
        return client.request(
            "POST",
            f"accounts/v1/{acct}/gbpAccounts:linkGbpAccount",
            json_body={"gbpEmail": gbp_email},
            op="link_gbp_account",
        )

    @mcp.tool()
    def gmc_list_gbp_accounts(max_pages: int = 3) -> dict[str, Any]:
        """List linked Google Business Profile accounts."""
        items = list(
            client.paginate(
                "GET",
                f"accounts/v1/{acct}/gbpAccounts",
                items_key="gbpAccounts",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "gbp_accounts": items}

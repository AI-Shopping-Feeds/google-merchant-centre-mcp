from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    @mcp.tool()
    def gmc_list_subscriptions(max_pages: int = 5) -> dict[str, Any]:
        """List push-notification subscriptions on this account."""
        items = list(
            client.paginate(
                "GET",
                f"notifications/v1/{acct}/notificationsubscriptions",
                items_key="notificationSubscriptions",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "subscriptions": items}

    @mcp.tool()
    def gmc_subscribe(
        registered_event: str,
        callback_uri: str,
        all_managed_accounts: bool = False,
        target_account: str | None = None,
    ) -> dict[str, Any]:
        """Create a notification subscription.

        registered_event: 'PRODUCT_STATUS_CHANGE' (currently the only supported event)
        callback_uri: HTTPS endpoint that will receive push messages
        all_managed_accounts: True for MCA-wide subscription
        target_account: e.g. 'accounts/12345' for single sub-account (mutually exclusive with all_managed_accounts)
        """
        body: dict[str, Any] = {
            "registeredEvent": registered_event,
            "callBackUri": callback_uri,
        }
        if all_managed_accounts:
            body["allManagedAccounts"] = True
        elif target_account:
            body["targetAccount"] = target_account
        return client.request(
            "POST",
            f"notifications/v1/{acct}/notificationsubscriptions",
            json_body=body,
            op="create_subscription",
        )

    @mcp.tool()
    def gmc_unsubscribe(subscription_id: str) -> dict[str, Any]:
        """Delete a notification subscription by ID."""
        path = f"notifications/v1/{acct}/notificationsubscriptions/{subscription_id}"
        before = client.snapshot(path)
        client.request("DELETE", path, op="delete_subscription", before=before)
        return {"deleted": subscription_id}

    @mcp.tool()
    def gmc_get_subscription(subscription_id: str) -> dict[str, Any]:
        """Get one notification subscription by ID."""
        return client.request(
            "GET", f"notifications/v1/{acct}/notificationsubscriptions/{subscription_id}"
        )

    @mcp.tool()
    def gmc_update_subscription(
        subscription_id: str,
        subscription: dict[str, Any],
        update_mask: str = "callBackUri",
    ) -> dict[str, Any]:
        """Patch a notification subscription (e.g. move it to a new callback URL).

        subscription example: {"callBackUri": "https://example.com/gmc-webhook"}
        update_mask: comma-separated fields, e.g. 'callBackUri'.
        """
        path = f"notifications/v1/{acct}/notificationsubscriptions/{subscription_id}"
        before = client.snapshot(path)
        return client.request(
            "PATCH",
            path,
            params={"updateMask": update_mask},
            json_body=subscription,
            op="update_subscription",
            before=before,
        )

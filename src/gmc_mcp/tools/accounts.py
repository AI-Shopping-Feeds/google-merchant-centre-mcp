from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    @mcp.tool()
    def gmc_get_account() -> dict[str, Any]:
        """Get the current Merchant Center account information."""
        return client.request("GET", f"accounts/v1/{acct}")

    @mcp.tool()
    def gmc_list_accounts(filter: str | None = None, max_pages: int = 5) -> dict[str, Any]:
        """List all Merchant Center accounts the caller can access (standalone,
        advanced/MCA, and sub-accounts).

        filter: optional account filter, e.g. 'accountName = "*shop*"' or
            'relationship(providerId = 123 AND service(type = "ACCOUNT_AGGREGATION"))'.
        """
        params = {"filter": filter} if filter else None
        items = list(
            client.paginate(
                "GET",
                "accounts/v1/accounts",
                params=params,
                items_key="accounts",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "accounts": items}

    @mcp.tool()
    def gmc_list_subaccounts(max_pages: int = 5) -> dict[str, Any]:
        """List sub-accounts of this advanced (MCA) account."""
        items = list(
            client.paginate(
                "GET",
                f"accounts/v1/{acct}:listSubaccounts",
                items_key="accounts",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "accounts": items}

    @mcp.tool()
    def gmc_update_account(
        account: dict[str, Any], update_mask: str
    ) -> dict[str, Any]:
        """Patch the account resource (e.g. accountName, adultContent, languageCode, timeZone).

        account example: {"accountName": "My Store", "timeZone": {"id": "America/New_York"}}
        update_mask: comma-separated fields, e.g. 'accountName,timeZone'.
        """
        before = client.snapshot(f"accounts/v1/{acct}")
        return client.request(
            "PATCH",
            f"accounts/v1/{acct}",
            params={"updateMask": update_mask},
            json_body=account,
            op="update_account",
            before=before,
        )

    @mcp.tool()
    def gmc_delete_account(
        confirm: str = "",
        account_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Permanently delete a Merchant Center account. DESTRUCTIVE and NOT reversible.
        Requires confirm='DELETE'.

        account_id: account to delete; defaults to the configured account. Deleting an
            advanced account also deletes all of its sub-accounts and its developer
            registration.
        force: delete even if the account provides services to other accounts or has
            processed offers.
        Requires admin access. Cannot be rolled back.
        """
        target = f"accounts/{account_id}" if account_id else acct
        if confirm != "DELETE":
            return {
                "error": "Refused: pass confirm='DELETE' (case-sensitive) to execute.",
                "would_delete": target,
                "force": force,
            }
        before = client.snapshot(f"accounts/v1/{target}")
        client.request(
            "DELETE",
            f"accounts/v1/{target}",
            params={"force": "true"} if force else None,
            op="delete_account",
            before=before,
        )
        return {"deleted": target}

    @mcp.tool()
    def gmc_create_and_configure_account(
        account: dict[str, Any],
        users: list[dict[str, Any]] | None = None,
        services: list[dict[str, Any]] | None = None,
        set_aliases: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new standalone or sub-account and configure it in one call.

        account: Account body, e.g. {"accountName": "Client A", "languageCode": "en",
            "timeZone": {"id": "America/Los_Angeles"}}
        users: optional list of {"userId": "a@b.com", "user": {"accessRights": ["ADMIN"]}}
        services: optional list of AddAccountService, e.g. to create a sub-account under
            an aggregator: [{"provider": "accounts/PROVIDER_ID", "accountAggregation": {}}]
        set_aliases: optional list of {"provider": "accounts/X", "accountIdAlias": "alias"}
        """
        body: dict[str, Any] = {"account": account}
        if users:
            body["user"] = users
        if services:
            body["service"] = services
        if set_aliases:
            body["setAlias"] = set_aliases
        return client.request(
            "POST",
            "accounts/v1/accounts:createAndConfigure",
            json_body=body,
            op="create_and_configure_account",
        )

    @mcp.tool()
    def gmc_create_test_account(account: dict[str, Any]) -> dict[str, Any]:
        """Create a Merchant Center TEST account under this account.

        Test accounts are sandboxes: nothing in them serves on Google surfaces, and they
        can't be converted to live accounts.
        account example: {"accountName": "API test", "timeZone": {"id": "Etc/UTC"},
                          "languageCode": "en"}
        """
        return client.request(
            "POST",
            f"accounts/v1/{acct}:createTestAccount",
            json_body=account,
            op="create_test_account",
        )

    @mcp.tool()
    def gmc_get_business_info() -> dict[str, Any]:
        """Get business identity info (address, phone, customer service)."""
        return client.request("GET", f"accounts/v1/{acct}/businessInfo")

    @mcp.tool()
    def gmc_update_business_info(
        business_info: dict[str, Any], update_mask: str | None = None
    ) -> dict[str, Any]:
        """Patch business info. Body example:
            {
              "address": {
                "regionCode": "US",
                "postalCode": "94043",
                "administrativeArea": "CA",
                "locality": "Mountain View",
                "addressLines": ["1600 Amphitheatre Pkwy"]
              },
              "phone": {"e164Number": "+14155551234"},
              "customerService": {
                "uri": "https://store.com/contact",
                "email": "support@store.com",
                "phone": {"e164Number": "+18005551234"}
              },
              "koreanBusinessRegistrationNumber": "123-45-67890"
            }
        update_mask: comma-separated FieldMask, e.g. 'address,phone'.
        """
        before = client.snapshot(f"accounts/v1/{acct}/businessInfo")
        params = {"updateMask": update_mask} if update_mask else None
        return client.request(
            "PATCH",
            f"accounts/v1/{acct}/businessInfo",
            params=params,
            json_body=business_info,
            op="update_business_info",
            before=before,
        )

    @mcp.tool()
    def gmc_list_users(max_pages: int = 5) -> dict[str, Any]:
        """List users with access to this Merchant Center account."""
        items = list(
            client.paginate(
                "GET",
                f"accounts/v1/{acct}/users",
                items_key="users",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "users": items}

    @mcp.tool()
    def gmc_add_user(email: str, access_rights: list[str]) -> dict[str, Any]:
        """Add a user to the Merchant Center account.

        access_rights: list of strings, e.g. ['ADMIN'] or ['STANDARD', 'PERFORMANCE_REPORTING']
        """
        return client.request(
            "POST",
            f"accounts/v1/{acct}/users",
            params={"userId": email},
            json_body={"accessRights": access_rights},
            op="add_user",
        )

    @mcp.tool()
    def gmc_remove_user(email: str) -> dict[str, Any]:
        """Remove a user from the Merchant Center account."""
        before = client.snapshot(f"accounts/v1/{acct}/users/{email}")
        client.request(
            "DELETE",
            f"accounts/v1/{acct}/users/{email}",
            op="remove_user",
            before=before,
        )
        return {"removed": email}

    @mcp.tool()
    def gmc_get_user(email: str) -> dict[str, Any]:
        """Get one user's access rights and state. email may also be 'me'."""
        return client.request("GET", f"accounts/v1/{acct}/users/{email}")

    @mcp.tool()
    def gmc_update_user(
        email: str, access_rights: list[str], update_mask: str = "accessRights"
    ) -> dict[str, Any]:
        """Change a user's access rights.

        access_rights: e.g. ['ADMIN'] or ['STANDARD', 'PERFORMANCE_REPORTING', 'READ_ONLY'].
        """
        before = client.snapshot(f"accounts/v1/{acct}/users/{email}")
        return client.request(
            "PATCH",
            f"accounts/v1/{acct}/users/{email}",
            params={"updateMask": update_mask},
            json_body={"accessRights": access_rights},
            op="update_user",
            before=before,
        )

    @mcp.tool()
    def gmc_verify_self() -> dict[str, Any]:
        """Move the calling user (users/me) from PENDING to VERIFIED on this account."""
        return client.request(
            "PATCH",
            f"accounts/v1/{acct}/users/me:verifySelf",
            json_body={},
            op="verify_self",
        )

    @mcp.tool()
    def gmc_get_shipping_settings() -> dict[str, Any]:
        """Get shipping settings (services, rate groups, delivery times)."""
        return client.request(
            "GET", f"accounts/v1/{acct}/shippingSettings"
        )

    @mcp.tool()
    def gmc_update_shipping_settings(shipping_settings: dict[str, Any]) -> dict[str, Any]:
        """Update shipping settings. Body must be a complete ShippingSettings object."""
        before = client.snapshot(f"accounts/v1/{acct}/shippingSettings")
        return client.request(
            "POST",
            f"accounts/v1/{acct}/shippingSettings:insert",
            json_body=shipping_settings,
            op="update_shipping_settings",
            before=before,
        )

    @mcp.tool()
    def gmc_list_programs(max_pages: int = 3) -> dict[str, Any]:
        """List participation in Merchant Center programs (Shopping Ads, Free Listings, etc.)."""
        items = list(
            client.paginate(
                "GET",
                f"accounts/v1/{acct}/programs",
                items_key="programs",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "programs": items}

    @mcp.tool()
    def gmc_get_program(program_id: str) -> dict[str, Any]:
        """Get one program's state for this account (state, active regions, unmet requirements).

        program_id: e.g. 'free-listings', 'shopping-ads', 'youtube-shopping-checkout'.
        """
        return client.request("GET", f"accounts/v1/{acct}/programs/{program_id}")

    @mcp.tool()
    def gmc_enable_program(program_id: str) -> dict[str, Any]:
        """Enable participation in a program (e.g. 'free-listings') for this account."""
        before = client.snapshot(f"accounts/v1/{acct}/programs/{program_id}")
        return client.request(
            "POST",
            f"accounts/v1/{acct}/programs/{program_id}:enable",
            json_body={},
            op="enable_program",
            before=before,
        )

    @mcp.tool()
    def gmc_disable_program(program_id: str) -> dict[str, Any]:
        """Disable participation in a program (e.g. 'shopping-ads') for this account.

        Products stop serving on that program's surfaces. Re-enable with gmc_enable_program.
        """
        before = client.snapshot(f"accounts/v1/{acct}/programs/{program_id}")
        return client.request(
            "POST",
            f"accounts/v1/{acct}/programs/{program_id}:disable",
            json_body={},
            op="disable_program",
            before=before,
        )

    # ---------------- Developer registration ----------------

    @mcp.tool()
    def gmc_get_developer_registration() -> dict[str, Any]:
        """Get the developer registration (which GCP project IDs are registered) for this account."""
        return client.request("GET", f"accounts/v1/{acct}/developerRegistration")

    @mcp.tool()
    def gmc_register_gcp(developer_email: str) -> dict[str, Any]:
        """Register the calling GCP project with this Merchant Center account.

        Required once per GCP project before most Merchant API v1 calls succeed.
        developer_email: email of a developer contact; added to the account as an
            API developer user if not already present.
        """
        return client.request(
            "POST",
            f"accounts/v1/{acct}/developerRegistration:registerGcp",
            json_body={"developerEmail": developer_email},
            op="register_gcp",
        )

    @mcp.tool()
    def gmc_unregister_gcp() -> dict[str, Any]:
        """Unregister the calling GCP project from this account. Subsequent API calls
        from the project will fail until it is registered again."""
        before = client.snapshot(f"accounts/v1/{acct}/developerRegistration")
        return client.request(
            "POST",
            f"accounts/v1/{acct}/developerRegistration:unregisterGcp",
            json_body={},
            op="unregister_gcp",
            before=before,
        )

    @mcp.tool()
    def gmc_get_account_for_gcp_registration() -> dict[str, Any]:
        """Return the Merchant Center account the calling GCP project is registered with."""
        return client.request(
            "GET", "accounts/v1/accounts:getAccountForGcpRegistration"
        )

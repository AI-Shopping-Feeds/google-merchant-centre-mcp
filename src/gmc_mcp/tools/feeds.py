from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    @mcp.tool()
    def gmc_list_datasources(max_pages: int = 5) -> dict[str, Any]:
        """List all data sources (primary, supplemental, file-based, API-based)."""
        items = list(
            client.paginate(
                "GET",
                f"datasources/v1/{acct}/dataSources",
                items_key="dataSources",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "data_sources": items}

    @mcp.tool()
    def gmc_get_datasource(datasource_id: str) -> dict[str, Any]:
        """Get a single data source by its ID (numeric)."""
        return client.request(
            "GET", f"datasources/v1/{acct}/dataSources/{datasource_id}"
        )

    @mcp.tool()
    def gmc_create_supplemental_feed(
        display_name: str,
        content_language: str,
        feed_label: str,
    ) -> dict[str, Any]:
        """Create an API-based supplemental product feed.

        display_name: human-readable name shown in the Merchant Center UI
        content_language: e.g. 'en', 'ko'
        feed_label: usually a country code like 'US', 'KR'

        Use the returned data source name when calling gmc_insert_product to write into this feed.
        """
        body = {
            "displayName": display_name,
            "supplementalProductDataSource": {
                "contentLanguage": content_language,
                "feedLabel": feed_label,
            },
        }
        return client.request(
            "POST",
            f"datasources/v1/{acct}/dataSources",
            json_body=body,
            op="create_supplemental_feed",
        )

    @mcp.tool()
    def gmc_create_primary_feed(
        display_name: str,
        content_language: str,
        feed_label: str,
        countries: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an API-based primary product feed.

        countries: list of ISO country codes the feed targets (e.g. ['US', 'CA'])
        """
        primary: dict[str, Any] = {
            "contentLanguage": content_language,
            "feedLabel": feed_label,
        }
        if countries:
            primary["countries"] = countries
        body = {
            "displayName": display_name,
            "primaryProductDataSource": primary,
        }
        return client.request(
            "POST",
            f"datasources/v1/{acct}/dataSources",
            json_body=body,
            op="create_primary_feed",
        )

    @mcp.tool()
    def gmc_create_datasource(data_source: dict[str, Any]) -> dict[str, Any]:
        """Create any type of data source from a full DataSource body.

        Use this for types not covered by gmc_create_primary_feed /
        gmc_create_supplemental_feed, e.g.:
            {"displayName": "Store stock",
             "localInventoryDataSource": {"feedLabel": "US", "contentLanguage": "en"}}
            {"displayName": "Regional prices",
             "regionalInventoryDataSource": {"feedLabel": "US", "contentLanguage": "en"}}
            {"displayName": "Promos", "promotionDataSource": {
                "targetCountry": "US", "contentLanguage": "en"}}
            {"displayName": "Product reviews", "productReviewDataSource": {}}
        Add "fileInput": {"fetchSettings": {...}} for a scheduled-fetch file feed.
        """
        return client.request(
            "POST",
            f"datasources/v1/{acct}/dataSources",
            json_body=data_source,
            op="create_datasource",
        )

    @mcp.tool()
    def gmc_update_datasource(
        datasource_id: str, data_source: dict[str, Any], update_mask: str
    ) -> dict[str, Any]:
        """Patch a data source (display name, fetch settings, default rule, etc.).

        data_source: partial DataSource body, e.g. {"displayName": "Main feed (US)"}
        update_mask: comma-separated fields, e.g. 'displayName' or
            'fileInput.fetchSettings.timeOfDay'.
        """
        before = client.snapshot(f"datasources/v1/{acct}/dataSources/{datasource_id}")
        return client.request(
            "PATCH",
            f"datasources/v1/{acct}/dataSources/{datasource_id}",
            params={"updateMask": update_mask},
            json_body=data_source,
            op="update_datasource",
            before=before,
        )

    @mcp.tool()
    def gmc_get_datasource_file_upload(
        datasource_id: str, file_upload_id: str = "latest"
    ) -> dict[str, Any]:
        """Get the processing result of a file-based data source upload/fetch
        (state, items created/updated/total, issues).

        file_upload_id: only 'latest' is currently supported by the API.
        """
        return client.request(
            "GET",
            f"datasources/v1/{acct}/dataSources/{datasource_id}/fileUploads/{file_upload_id}",
        )

    @mcp.tool()
    def gmc_delete_datasource(datasource_id: str) -> dict[str, Any]:
        """Delete a data source. Cannot delete a primary feed if products depend on it."""
        before = client.snapshot(f"datasources/v1/{acct}/dataSources/{datasource_id}")
        client.request(
            "DELETE",
            f"datasources/v1/{acct}/dataSources/{datasource_id}",
            op="delete_datasource",
            before=before,
        )
        return {"deleted": datasource_id}

    @mcp.tool()
    def gmc_fetch_datasource(datasource_id: str) -> dict[str, Any]:
        """Trigger an immediate fetch of a file-based data source (must have a fetch URL)."""
        return client.request(
            "POST",
            f"datasources/v1/{acct}/dataSources/{datasource_id}:fetch",
            json_body={},
            op="fetch_datasource",
        )

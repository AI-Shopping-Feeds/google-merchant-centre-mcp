from __future__ import annotations

from typing import Any

from ..client import MerchantClient

REPORTING_STATUSES = {"ELIGIBLE", "ELIGIBLE_LIMITED", "NOT_ELIGIBLE_OR_DISAPPROVED", "PENDING"}


def _product_key(p: dict[str, Any]) -> tuple[str, str, str]:
    return (p.get("offerId") or "", p.get("feedLabel") or "", p.get("contentLanguage") or "")


def _keys_with_status(client: MerchantClient, acct: str, status: str) -> set[tuple[str, str, str]]:
    """(offerId, feedLabel, contentLanguage) for every product_view row with `status`."""
    query = (
        "SELECT id, offer_id, feed_label, language_code "
        "FROM product_view "
        f"WHERE aggregated_reporting_context_status = '{status}'"
    )
    keys: set[tuple[str, str, str]] = set()
    body: dict[str, Any] = {"query": query}
    while True:
        payload = client.request(
            "POST", f"reports/v1/{acct}/reports:search", json_body=body, read_only=True
        )
        for row in payload.get("results", []) or []:
            pv = row.get("productView") or {}
            keys.add(
                (pv.get("offerId") or "", pv.get("feedLabel") or "", pv.get("languageCode") or "")
            )
        token = payload.get("nextPageToken")
        if not token:
            return keys
        body = {"query": query, "pageToken": token}


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    @mcp.tool()
    def gmc_list_products(
        max_pages: int = 10,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List all products in the Merchant Center account.

        Returns up to max_pages * page_size items. Use page_size=None for the configured default.
        """
        params: dict[str, Any] = {}
        if page_size:
            params["pageSize"] = page_size
        items = list(
            client.paginate(
                "GET",
                f"products/v1/{acct}/products",
                params=params,
                items_key="products",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "products": items}

    @mcp.tool()
    def gmc_get_product(product_id: str) -> dict[str, Any]:
        """Get a single product by its full product ID.

        Product ID format: channel~contentLanguage~feedLabel~offerId
        e.g. online~en~US~SKU123
        """
        return client.request("GET", f"products/v1/{acct}/products/{product_id}")

    @mcp.tool()
    def gmc_insert_product(product: dict[str, Any], data_source: str) -> dict[str, Any]:
        """Insert or update a product via productInputs (Merchant API v1).

        product: full product input object. v1 field-name changes vs v1beta:
          - 'gtin' -> 'gtins' (list)
          - 'attributes' -> 'productAttributes'
          - 'channel' removed; use 'legacyLocal' (bool) for local-only products
          - 'taxes', 'taxCategory' removed
          - 'availability', 'condition', 'gender', 'includedDestinations',
            'excludedDestinations' are enums (UPPER_CASE strings) in v1
        data_source: full data source name like 'accounts/123/dataSources/456'
                     (use gmc_list_datasources to find one).

        Upsert semantics: if a product with the same offerId exists, it's overwritten.
        """
        return client.request(
            "POST",
            f"products/v1/{acct}/productInputs:insert",
            params={"dataSource": data_source},
            json_body=product,
            op="insert_product",
        )

    @mcp.tool()
    def gmc_update_product(
        product_id: str,
        product: dict[str, Any],
        data_source: str,
    ) -> dict[str, Any]:
        """Update a product. Implemented as productInputs:insert (upsert).

        product_id: existing product ID (channel~lang~feedLabel~offerId)
        product: new product input — full body, since insert overwrites
        data_source: full data source name
        """
        before = client.snapshot(f"products/v1/{acct}/products/{product_id}")
        return client.request(
            "POST",
            f"products/v1/{acct}/productInputs:insert",
            params={"dataSource": data_source},
            json_body=product,
            op="update_product",
            before=before,
        )

    @mcp.tool()
    def gmc_patch_product(
        product_id: str,
        product: dict[str, Any],
        data_source: str,
        update_mask: str,
    ) -> dict[str, Any]:
        """Partially update a product input via productInputs.patch (Merchant API v1).

        Unlike gmc_update_product (insert = full overwrite), only the fields named in
        update_mask are changed.

        product_id: existing product input ID (contentLanguage~feedLabel~offerId, or the
            legacy channel~contentLanguage~feedLabel~offerId form).
        product: ProductInput body containing the new values, e.g.
            {"productAttributes": {"title": "New title", "price": {
                "amountMicros": "19990000", "currencyCode": "USD"}}}
        data_source: data source the product input belongs to. Only API data sources
            (primary or supplemental) can be patched.
        update_mask: comma-separated field paths, e.g. 'productAttributes.title,
            productAttributes.price'. Use 'customAttributes' for custom attributes.
        """
        before = client.snapshot(f"products/v1/{acct}/products/{product_id}")
        return client.request(
            "PATCH",
            f"products/v1/{acct}/productInputs/{product_id}",
            params={"dataSource": data_source, "updateMask": update_mask},
            json_body=product,
            op="patch_product",
            before=before,
        )

    @mcp.tool()
    def gmc_delete_product(product_id: str, data_source: str) -> dict[str, Any]:
        """Delete a product input.

        product_id: full product ID (channel~lang~feedLabel~offerId)
        data_source: data source the product belongs to
        """
        before = client.snapshot(f"products/v1/{acct}/products/{product_id}")
        client.request(
            "DELETE",
            f"products/v1/{acct}/productInputs/{product_id}",
            params={"dataSource": data_source},
            op="delete_product",
            before=before,
        )
        return {"deleted": product_id}

    @mcp.tool()
    def gmc_bulk_delete_products(
        confirm: str = "",
        filter_status: str | None = None,
        max_delete: int = 5000,
    ) -> dict[str, Any]:
        """Bulk-delete product inputs. DESTRUCTIVE — requires confirm='DELETE'.

        confirm: must be the exact string 'DELETE' (case-sensitive) or this tool refuses.
        filter_status: only delete products whose Reports `aggregated_reporting_context_status`
            matches this value: 'ELIGIBLE' | 'ELIGIBLE_LIMITED' | 'NOT_ELIGIBLE_OR_DISAPPROVED'
            | 'PENDING'. Matching is done on (offerId, feedLabel, contentLanguage) via a
            product_view query. None = delete ALL.
        max_delete: hard cap on deletions to prevent runaway calls.

        Each product's own `dataSource` field is used as the dataSource query parameter,
        so this works even for orphan products whose source was already deleted.
        Every deletion is recorded in the audit log with `before` snapshot for rollback.
        """
        if confirm != "DELETE":
            return {
                "error": "Refused: pass confirm='DELETE' (case-sensitive) to execute.",
                "would_delete_filter_status": filter_status,
                "max_delete": max_delete,
            }

        wanted: set[tuple[str, str, str]] | None = None
        if filter_status:
            status = filter_status.upper()
            if status not in REPORTING_STATUSES:
                return {
                    "error": f"filter_status must be one of {sorted(REPORTING_STATUSES)}",
                }
            wanted = _keys_with_status(client, acct, status)

        # Collect products
        candidates: list[dict[str, Any]] = []
        params: dict[str, Any] = {"pageSize": 250}
        while len(candidates) < max_delete:
            page = client.request("GET", f"products/v1/{acct}/products", params=params)
            for p in page.get("products", []) or []:
                if wanted is not None and _product_key(p) not in wanted:
                    continue
                candidates.append(p)
                if len(candidates) >= max_delete:
                    break
            token = page.get("nextPageToken")
            if not token:
                break
            params["pageToken"] = token

        deleted: list[str] = []
        failed: list[dict[str, Any]] = []
        for p in candidates:
            name = p.get("name", "")
            ds = p.get("dataSource")
            if not name or not ds:
                failed.append({"name": name, "reason": "missing name or dataSource"})
                continue
            pid = name.split("/")[-1]
            try:
                client.request(
                    "DELETE",
                    f"products/v1/{acct}/productInputs/{pid}",
                    params={"dataSource": ds},
                    op="bulk_delete_product",
                    before=p,
                )
                deleted.append(pid)
            except Exception as e:
                failed.append({"name": name, "reason": str(e)[:200]})

        return {
            "scanned": len(candidates),
            "deleted_count": len(deleted),
            "failed_count": len(failed),
            "failed_samples": failed[:10],
        }

    @mcp.tool()
    def gmc_list_disapproved_products(max_pages: int = 20) -> dict[str, Any]:
        """List products that are currently disapproved on Google Shopping.

        Uses Reports API for efficiency over scanning every product status.
        Note: Reports API requires `id` in the SELECT clause for product_view.
        """
        query = (
            "SELECT id, offer_id, title, aggregated_reporting_context_status "
            "FROM product_view "
            "WHERE aggregated_reporting_context_status = 'NOT_ELIGIBLE_OR_DISAPPROVED'"
        )
        results: list[dict[str, Any]] = []
        body: dict[str, Any] = {"query": query}
        path = f"reports/v1/{acct}/reports:search"
        page_count = 0
        while page_count < max_pages:
            payload = client.request("POST", path, json_body=body, read_only=True)
            results.extend(payload.get("results", []) or [])
            page_count += 1
            token = payload.get("nextPageToken")
            if not token:
                break
            body = {"query": query, "pageToken": token}
        return {"count": len(results), "results": results, "_query": query}

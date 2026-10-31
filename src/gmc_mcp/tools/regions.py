"""Regions CRUD — required for setting up regional inventory targeting.

A region is a named bundle of postal codes / sub-areas you can later target
with `gmc_update_regional_inventory(region=...)`.
"""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()
    base = f"accounts/v1/{acct}/regions"

    @mcp.tool()
    def gmc_list_regions(max_pages: int = 5) -> dict[str, Any]:
        """List all regions configured on the account."""
        items = list(
            client.paginate(
                "GET", base, items_key="regions", max_pages=max_pages
            )
        )
        return {"count": len(items), "regions": items}

    @mcp.tool()
    def gmc_get_region(region_id: str) -> dict[str, Any]:
        """Get one region by ID."""
        return client.request("GET", f"{base}/{region_id}")

    @mcp.tool()
    def gmc_create_region(
        region_id: str,
        display_name: str,
        postal_code_prefixes: list[str] | None = None,
        postal_code_ranges: list[dict[str, str]] | None = None,
        postal_region_code: str | None = None,
        geotarget_criteria_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new region.

        region_id: short ID like 'us-west', 'kr-seoul'.
        Provide ONE kind of area:
          - postal_code_prefixes: ['90', '91']  (sent as '90*', '91*')
          - postal_code_ranges: [{'begin': '90001', 'end': '92899'}]
            ('firstPostalCode'/'lastPostalCode' keys are also accepted)
            Postal areas also need postal_region_code (CLDR country, e.g. 'US').
          - geotarget_criteria_ids: ['1014044']  (Google Ads geotargets)
        """
        body: dict[str, Any] = {"displayName": display_name}
        if postal_code_prefixes or postal_code_ranges:
            if not postal_region_code:
                return {"error": "postal_region_code is required for postal-code regions"}
            codes: list[dict[str, str]] = [
                {"begin": p if p.endswith("*") else f"{p}*"}
                for p in (postal_code_prefixes or [])
            ]
            for r in postal_code_ranges or []:
                rng = {"begin": r.get("begin") or r.get("firstPostalCode", "")}
                end = r.get("end") or r.get("lastPostalCode")
                if end:
                    rng["end"] = end
                codes.append(rng)
            body["postalCodeArea"] = {"regionCode": postal_region_code, "postalCodes": codes}
        if geotarget_criteria_ids:
            body["geotargetArea"] = {"geotargetCriteriaIds": geotarget_criteria_ids}

        return client.request(
            "POST",
            base,
            params={"regionId": region_id},
            json_body=body,
            op="create_region",
        )

    @mcp.tool()
    def gmc_update_region(
        region_id: str, region: dict[str, Any], update_mask: str | None = None
    ) -> dict[str, Any]:
        """Patch a region. update_mask example: 'displayName,postalCodeArea'."""
        before = client.snapshot(f"{base}/{region_id}")
        params = {"updateMask": update_mask} if update_mask else None
        return client.request(
            "PATCH",
            f"{base}/{region_id}",
            params=params,
            json_body=region,
            op="update_region",
            before=before,
        )

    @mcp.tool()
    def gmc_delete_region(region_id: str) -> dict[str, Any]:
        """Delete a region (and any regional inventories that reference it)."""
        before = client.snapshot(f"{base}/{region_id}")
        client.request(
            "DELETE", f"{base}/{region_id}", op="delete_region", before=before
        )
        return {"deleted_region_id": region_id}

    @mcp.tool()
    def gmc_batch_create_regions(regions: list[dict[str, Any]]) -> dict[str, Any]:
        """Create several regions in one call.

        regions: list of {"regionId": "us-west", "region": {Region body}}.
        """
        requests = [
            {"regionId": r["regionId"], "region": r["region"]} for r in regions
        ]
        return client.request(
            "POST",
            f"{base}:batchCreate",
            json_body={"requests": requests},
            op="batch_create_regions",
        )

    @mcp.tool()
    def gmc_batch_update_regions(updates: list[dict[str, Any]]) -> dict[str, Any]:
        """Patch several regions in one call.

        updates: list of {"region_id": "us-west", "region": {...}, "update_mask": "displayName"}.
        update_mask is optional per item.
        """
        requests = []
        for u in updates:
            region = dict(u["region"])
            region["name"] = f"{acct}/regions/{u['region_id']}"
            req: dict[str, Any] = {"region": region}
            if u.get("update_mask"):
                req["updateMask"] = u["update_mask"]
            requests.append(req)
        return client.request(
            "POST",
            f"{base}:batchUpdate",
            json_body={"requests": requests},
            op="batch_update_regions",
        )

    @mcp.tool()
    def gmc_batch_delete_regions(region_ids: list[str], confirm: str = "") -> dict[str, Any]:
        """Delete several regions in one call. DESTRUCTIVE — requires confirm='DELETE'.

        Regional inventories that reference these regions stop applying.
        `before` snapshots of each region are stored in the audit entry.
        """
        if confirm != "DELETE":
            return {
                "error": "Refused: pass confirm='DELETE' (case-sensitive) to execute.",
                "would_delete": region_ids,
            }
        before = [client.snapshot(f"{base}/{rid}") for rid in region_ids]
        client.request(
            "POST",
            f"{base}:batchDelete",
            json_body={"requests": [{"name": f"{acct}/regions/{rid}"} for rid in region_ids]},
            op="batch_delete_regions",
            before=before,
        )
        return {"deleted_region_ids": region_ids}

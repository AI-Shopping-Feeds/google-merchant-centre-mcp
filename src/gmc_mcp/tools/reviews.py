"""Product reviews (Merchant API v1) + merchant reviews (v1beta only)."""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()
    # merchantReviews only exists in reviews_v1beta; productReviews is GA in v1.
    mr_base = f"reviews/v1beta/{acct}/merchantReviews"
    pr_base = f"reviews/v1/{acct}/productReviews"

    # ---- Merchant reviews (v1beta) ----

    @mcp.tool()
    def gmc_list_merchant_reviews(max_pages: int = 5) -> dict[str, Any]:
        """[v1beta] List merchant (store) reviews — used for seller ratings.

        Merchant reviews are only available on reviews_v1beta (no v1 endpoint yet).
        """
        items = list(
            client.paginate(
                "GET", mr_base, items_key="merchantReviews", max_pages=max_pages
            )
        )
        return {"count": len(items), "reviews": items}

    @mcp.tool()
    def gmc_get_merchant_review(review_id: str) -> dict[str, Any]:
        """[v1beta] Get one merchant review by ID."""
        return client.request("GET", f"{mr_base}/{review_id}")

    @mcp.tool()
    def gmc_insert_merchant_review(
        review: dict[str, Any], data_source: str
    ) -> dict[str, Any]:
        """[v1beta] Insert / upsert a merchant review.

        review: full MerchantReview body (merchantReviewId, merchantReviewAttributes, ...)
        data_source: merchant-review data source name like 'accounts/X/dataSources/Y'.
        """
        return client.request(
            "POST",
            f"{mr_base}:insert",
            params={"dataSource": data_source},
            json_body=review,
            op="insert_merchant_review",
        )

    @mcp.tool()
    def gmc_delete_merchant_review(review_id: str) -> dict[str, Any]:
        """[v1beta] Delete a merchant review."""
        before = client.snapshot(f"{mr_base}/{review_id}")
        client.request(
            "DELETE", f"{mr_base}/{review_id}", op="delete_merchant_review", before=before
        )
        return {"deleted": review_id}

    # ---- Product reviews (v1) ----

    @mcp.tool()
    def gmc_list_product_reviews(max_pages: int = 10) -> dict[str, Any]:
        """List product reviews."""
        items = list(
            client.paginate(
                "GET", pr_base, items_key="productReviews", max_pages=max_pages
            )
        )
        return {"count": len(items), "reviews": items}

    @mcp.tool()
    def gmc_get_product_review(review_id: str) -> dict[str, Any]:
        """Get one product review by ID."""
        return client.request("GET", f"{pr_base}/{review_id}")

    @mcp.tool()
    def gmc_insert_product_review(
        review: dict[str, Any], data_source: str
    ) -> dict[str, Any]:
        """Insert / upsert a product review.

        review: ProductReview body (productReviewId, productReviewAttributes, ...).
        data_source: product-review data source name like 'accounts/X/dataSources/Y'.
        """
        return client.request(
            "POST",
            f"{pr_base}:insert",
            params={"dataSource": data_source},
            json_body=review,
            op="insert_product_review",
        )

    @mcp.tool()
    def gmc_delete_product_review(review_id: str) -> dict[str, Any]:
        """Delete a product review."""
        before = client.snapshot(f"{pr_base}/{review_id}")
        client.request(
            "DELETE", f"{pr_base}/{review_id}", op="delete_product_review", before=before
        )
        return {"deleted": review_id}

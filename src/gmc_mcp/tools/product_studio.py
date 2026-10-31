"""Product Studio sub-API — ALPHA (productstudio/v1alpha).

There is no v1 (or v1beta) Product Studio API; these tools call v1alpha, which
Google may change or withdraw without notice and which may require allowlisting.
They generate content and do not modify your Merchant Center data, so they run
as read-only requests (allowed in dry-run, not written to the audit log).
"""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def _image(image_uri: str | None, image_bytes: str | None) -> dict[str, str]:
    if image_uri:
        return {"imageUri": image_uri}
    if image_bytes:
        return {"imageBytes": image_bytes}
    raise ValueError("Provide image_uri or image_bytes (base64).")


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()
    base = f"productstudio/v1alpha/{acct}"

    @mcp.tool()
    def gmc_generate_product_text_suggestions(
        product_attributes: dict[str, str],
        product_image_uri: str | None = None,
        output_spec: dict[str, Any] | None = None,
        title_examples: list[dict[str, Any]] | None = None,
        low_quality_title_filtering: bool | None = None,
    ) -> dict[str, Any]:
        """[ALPHA v1alpha] Generate AI title/description suggestions for a product.

        product_attributes: e.g. {"title": "Red shirt", "brand": "Acme",
                                  "description": "...", "color": "red"}
        product_image_uri: optional product image URL to ground the suggestions.
        output_spec: optional, e.g. {"workflowId": "title", "tone": "playful",
                                     "targetLanguage": "en"}
        title_examples: optional few-shot examples of good titles.
        Does not change any product; apply suggestions with gmc_patch_product.
        """
        product_info: dict[str, Any] = {"productAttributes": product_attributes}
        if product_image_uri:
            product_info["productImage"] = {"uri": product_image_uri}
        body: dict[str, Any] = {"productInfo": product_info}
        if output_spec:
            body["outputSpec"] = output_spec
        if title_examples:
            body["titleExamples"] = title_examples
        if low_quality_title_filtering is not None:
            body["lowQualityTitleFilteringEnabled"] = low_quality_title_filtering
        return client.request(
            "POST",
            f"{base}:generateProductTextSuggestions",
            json_body=body,
            read_only=True,
        )

    @mcp.tool()
    def gmc_generate_product_image_background(
        product_description: str,
        background_description: str,
        image_uri: str | None = None,
        image_bytes: str | None = None,
        return_image_uri: bool = True,
    ) -> dict[str, Any]:
        """[ALPHA v1alpha] Replace a product image's background with an AI-generated scene.

        product_description: e.g. 'a white ceramic mug'.
        background_description: e.g. 'on a wooden kitchen table, morning light'.
        image_uri / image_bytes: the input image (URL, or base64 bytes).
        return_image_uri: True to get a hosted URL back instead of bytes.
        """
        return client.request(
            "POST",
            f"{base}/generatedImages:generateProductImageBackground",
            json_body={
                "inputImage": _image(image_uri, image_bytes),
                "config": {
                    "productDescription": product_description,
                    "backgroundDescription": background_description,
                },
                "outputConfig": {"returnImageUri": return_image_uri},
            },
            read_only=True,
        )

    @mcp.tool()
    def gmc_remove_product_image_background(
        image_uri: str | None = None,
        image_bytes: str | None = None,
        background_color: dict[str, int] | None = None,
        return_image_uri: bool = True,
    ) -> dict[str, Any]:
        """[ALPHA v1alpha] Remove a product image's background.

        background_color: optional RGB fill, e.g. {"red": 255, "green": 255, "blue": 255};
            omit for a transparent background.
        """
        body: dict[str, Any] = {
            "inputImage": _image(image_uri, image_bytes),
            "outputConfig": {"returnImageUri": return_image_uri},
        }
        if background_color:
            body["config"] = {"backgroundColor": background_color}
        return client.request(
            "POST",
            f"{base}/generatedImages:removeProductImageBackground",
            json_body=body,
            read_only=True,
        )

    @mcp.tool()
    def gmc_upscale_product_image(
        image_uri: str | None = None,
        image_bytes: str | None = None,
        return_image_uri: bool = True,
    ) -> dict[str, Any]:
        """[ALPHA v1alpha] Upscale a low-resolution product image."""
        return client.request(
            "POST",
            f"{base}/generatedImages:upscaleProductImage",
            json_body={
                "inputImage": _image(image_uri, image_bytes),
                "outputConfig": {"returnImageUri": return_image_uri},
            },
            read_only=True,
        )

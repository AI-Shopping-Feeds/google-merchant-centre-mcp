"""Issue Resolution sub-API (Merchant API v1): rendered issue explanations with
actions, triggering built-in actions, and aggregate product statuses."""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def _render_params(language_code: str, time_zone: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {"languageCode": language_code}
    if time_zone:
        params["timeZone"] = time_zone
    return params


def _render_body(content_option: str, user_input_action_option: str) -> dict[str, Any]:
    return {
        "contentOption": content_option,
        "userInputActionOption": user_input_action_option,
    }


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()
    base = f"issueresolution/v1/{acct}"

    @mcp.tool()
    def gmc_render_account_issues(
        language_code: str = "en",
        time_zone: str | None = None,
        content_option: str = "PRE_RENDERED_HTML",
        user_input_action_option: str = "REDIRECT_TO_MERCHANT_CENTER",
    ) -> dict[str, Any]:
        """Render account-level issues with Google's explanations and suggested actions.

        content_option: 'PRE_RENDERED_HTML' (default) for ready-to-show HTML.
        user_input_action_option: 'REDIRECT_TO_MERCHANT_CENTER' (default) or
            'BUILT_IN_USER_INPUT_ACTIONS' to get actions you can run via
            gmc_trigger_issue_action.
        Read-only: works in dry-run mode and is not audited.
        """
        return client.request(
            "POST",
            f"{base}:renderaccountissues",
            params=_render_params(language_code, time_zone),
            json_body=_render_body(content_option, user_input_action_option),
            read_only=True,
        )

    @mcp.tool()
    def gmc_render_product_issues(
        product_id: str,
        language_code: str = "en",
        time_zone: str | None = None,
        content_option: str = "PRE_RENDERED_HTML",
        user_input_action_option: str = "REDIRECT_TO_MERCHANT_CENTER",
    ) -> dict[str, Any]:
        """Render one product's issues with explanations and suggested actions.

        product_id: full product ID (e.g. 'online~en~US~SKU1' or 'en~US~SKU1').
        Read-only: works in dry-run mode and is not audited.
        """
        return client.request(
            "POST",
            f"{base}/products/{product_id}:renderproductissues",
            params=_render_params(language_code, time_zone),
            json_body=_render_body(content_option, user_input_action_option),
            read_only=True,
        )

    @mcp.tool()
    def gmc_trigger_issue_action(
        action_context: str,
        action_input: dict[str, Any],
        language_code: str = "en",
    ) -> dict[str, Any]:
        """Start a built-in action (e.g. request a re-review) returned by
        gmc_render_*_issues with user_input_action_option='BUILT_IN_USER_INPUT_ACTIONS'.

        action_context: the `actionContext` token from the rendered action.
        action_input: {"actionFlowId": "...", "inputValues": [
            {"inputFieldId": "...", "checkboxInputValue": {"value": true}}]}
        This is a write: it is audited and skipped in dry-run mode.
        """
        return client.request(
            "POST",
            f"{base}:triggeraction",
            params={"languageCode": language_code},
            json_body={"actionContext": action_context, "actionInput": action_input},
            op="trigger_issue_action",
        )

    @mcp.tool()
    def gmc_list_aggregate_product_statuses(
        filter: str | None = None, max_pages: int = 5
    ) -> dict[str, Any]:
        """Counts of products by status and issue, per reporting context and country.

        filter: optional, only `reporting_context` and `country` are supported, e.g.
            'reporting_context = "SHOPPING_ADS" AND country = "US"'.
        """
        params = {"filter": filter} if filter else None
        items = list(
            client.paginate(
                "GET",
                f"issueresolution/v1/{acct}/aggregateProductStatuses",
                params=params,
                items_key="aggregateProductStatuses",
                max_pages=max_pages,
            )
        )
        return {"count": len(items), "aggregate_product_statuses": items}

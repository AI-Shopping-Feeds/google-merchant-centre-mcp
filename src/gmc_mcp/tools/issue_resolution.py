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


def _text(value: dict[str, Any] | None) -> str | None:
    """Plain text of a TextWithTooltip, with its tooltip appended."""
    if not value:
        return None
    text = value.get("simpleValue")
    tip = value.get("simpleTooltipValue")
    return f"{text} ({tip})" if text and tip else text or tip


def _input_field(field: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "field_id": field.get("id"),
        "label": _text(field.get("label")),
        "required": bool(field.get("required")),
    }
    if "checkboxInput" in field:
        out["answer_with"] = "true or false"
    elif "choiceInput" in field:
        out["answer_with"] = '{"choice": "<option_id>"}'
        out["options"] = [
            {
                "option_id": opt.get("id"),
                "label": _text(opt.get("label")),
                **(
                    {"additional_input": _input_field(opt["additionalInput"])}
                    if opt.get("additionalInput")
                    else {}
                ),
            }
            for opt in field["choiceInput"].get("options", [])
        ]
    else:
        text_input = field.get("textInput", {})
        out["answer_with"] = "a string"
        if text_input.get("formatInfo"):
            out["format"] = text_input["formatInfo"]
        if text_input.get("additionalInfo"):
            out["note"] = _text(text_input["additionalInfo"])
    return out


# External actions that are reviews or appeals done outside the API.
_EXTERNAL_REVIEW_TYPES = {
    "REVIEW_PRODUCT_ISSUE_IN_MERCHANT_CENTER",
    "REVIEW_ACCOUNT_ISSUE_IN_MERCHANT_CENTER",
    "LEGAL_APPEAL_IN_HELP_CENTER",
}


def _review_action(action: dict[str, Any]) -> dict[str, Any] | None:
    """Simplifies one rendered action, or returns None if it isn't a review-type action."""
    base = {
        "label": action.get("buttonLabel"),
        "available": bool(action.get("isAvailable")),
        "unavailable_reasons": [
            r.get("message") for r in action.get("reasons", []) if r.get("message")
        ],
    }
    builtin = action.get("builtinUserInputAction")
    if builtin:
        return {
            **base,
            "kind": "request_in_api",
            "action_context": builtin.get("actionContext"),
            "flows": [
                {
                    "flow_id": flow.get("id"),
                    "label": flow.get("label"),
                    "dialog_title": flow.get("dialogTitle"),
                    "dialog_message": _text(flow.get("dialogMessage")),
                    "warning": _text((flow.get("dialogCallout") or {}).get("fullMessage")),
                    "inputs": [_input_field(f) for f in flow.get("inputs", [])],
                }
                for flow in builtin.get("flows", [])
            ],
        }
    external = action.get("externalAction")
    if external and external.get("type") in _EXTERNAL_REVIEW_TYPES:
        return {
            **base,
            "kind": "external",
            "type": external.get("type"),
            "url": external.get("uri"),
        }
    return None


def _review_options(payload: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for issue in payload.get("renderedIssues", []) or []:
        actions = [a for a in map(_review_action, issue.get("actions", [])) if a]
        if not actions:
            continue
        impact = issue.get("impact") or {}
        issues.append(
            {
                "issue": issue.get("title"),
                "severity": impact.get("severity"),
                "impact": impact.get("message"),
                "actions": actions,
            }
        )
    return issues


def _input_value(field_id: str, answer: Any) -> dict[str, Any]:
    if isinstance(answer, bool):
        return {"inputFieldId": field_id, "checkboxInputValue": {"value": answer}}
    if isinstance(answer, dict) and "choice" in answer:
        return {
            "inputFieldId": field_id,
            "choiceInputValue": {"choiceInputOptionId": str(answer["choice"])},
        }
    if isinstance(answer, str):
        return {"inputFieldId": field_id, "textInputValue": {"value": answer}}
    raise ValueError(
        f'Answer for \'{field_id}\' must be true/false, a string, or {{"choice": "<option_id>"}}.'
    )


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

    def _render_for_review(product_id: str | None, language_code: str, time_zone: str | None):
        path = (
            f"{base}/products/{product_id}:renderproductissues"
            if product_id
            else f"{base}:renderaccountissues"
        )
        return client.request(
            "POST",
            path,
            params=_render_params(language_code, time_zone),
            json_body=_render_body("PRE_RENDERED_HTML", "BUILT_IN_USER_INPUT_ACTIONS"),
            read_only=True,
        )

    @mcp.tool()
    def gmc_list_review_options(
        product_id: str | None = None,
        language_code: str = "en",
        time_zone: str | None = None,
    ) -> dict[str, Any]:
        """List the review / appeal actions available for a product's or the account's issues.

        Use this before gmc_request_review. For each issue it returns the actions
        Google offers (e.g. "Request review"), whether each is available right now
        and why not (e.g. a review was already requested, or you must wait 7 days),
        and for API-requestable actions the `action_context`, the flows to choose
        from (e.g. "I fixed the issue" / "I disagree") and the questions to answer.
        Actions with kind 'external' can only be done at the returned Merchant
        Center or Help Center `url`.

        product_id: product ID such as 'en~US~SKU1' to check one product (get IDs
            from gmc_list_disapproved_products). Omit for account-level issues.
        Read-only: works in dry-run mode and is not audited.
        """
        payload = _render_for_review(product_id, language_code, time_zone)
        issues = _review_options(payload)
        return {
            "target": product_id or "account",
            "issues_with_review_actions": len(issues),
            "issues": issues,
        }

    @mcp.tool()
    def gmc_request_review(
        action_context: str,
        flow_id: str,
        answers: dict[str, Any] | None = None,
        language_code: str = "en",
    ) -> dict[str, Any]:
        """Request a review (or appeal) of a disapproval or account issue.

        Call gmc_list_review_options first and use the `action_context`, a
        `flow_id` from that action, and answers for the flow's inputs. Only
        request a review after the issue is fixed or if the business disagrees:
        some issues allow only one review, and a failed review can block new
        requests for days.

        answers: {field_id: value} for the flow's inputs. Use true/false for a
            checkbox, a string for a text field, and {"choice": "<option_id>"} for
            a choice field. Every required field needs an answer.
        This is a write: it is audited and skipped in dry-run mode.
        """
        input_values = [_input_value(fid, value) for fid, value in (answers or {}).items()]
        return client.request(
            "POST",
            f"{base}:triggeraction",
            params={"languageCode": language_code},
            json_body={
                "actionContext": action_context,
                "actionInput": {"actionFlowId": flow_id, "inputValues": input_values},
            },
            op="request_review",
        )

    @mcp.tool()
    def gmc_list_disapproved_review_options(
        max_products: int = 25, language_code: str = "en"
    ) -> dict[str, Any]:
        """Check review options for many disapproved products at once.

        Finds disapproved products with a Reports query, then runs
        gmc_list_review_options on each (one API call per product, up to
        max_products). Returns only products that have a review-type action,
        with counts of how many can be requested now. Request each review with
        gmc_request_review after the user confirms.
        Read-only: works in dry-run mode and is not audited.
        """
        query = (
            "SELECT id, offer_id, title FROM product_view "
            "WHERE aggregated_reporting_context_status = 'NOT_ELIGIBLE_OR_DISAPPROVED' "
            f"LIMIT {int(max_products)}"
        )
        payload = client.request(
            "POST",
            f"reports/v1/{acct}/reports:search",
            json_body={"query": query},
            read_only=True,
        )
        products_out = []
        requestable = 0
        for row in payload.get("results", []) or []:
            view = row.get("productView") or {}
            product_id = view.get("id")
            if not product_id:
                continue
            issues = _review_options(_render_for_review(product_id, language_code, None))
            if not issues:
                continue
            requestable += sum(
                1
                for issue in issues
                for a in issue["actions"]
                if a["kind"] == "request_in_api" and a["available"]
            )
            products_out.append(
                {
                    "product_id": product_id,
                    "offer_id": view.get("offerId"),
                    "title": view.get("title"),
                    "issues": issues,
                }
            )
        return {
            "products_checked": len(payload.get("results", []) or []),
            "products_with_review_actions": len(products_out),
            "reviews_requestable_now": requestable,
            "products": products_out,
        }

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

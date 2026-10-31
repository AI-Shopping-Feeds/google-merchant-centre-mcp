"""Tests for the guided review-request tools in the issue_resolution module.
The rendered-issue payloads follow the Issue Resolution v1 schema. All HTTP is
mocked with respx."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from gmc_mcp.client import BASE_URL, MerchantClient
from gmc_mcp.tools import issue_resolution

ACCT = "accounts/1234567890"
IR = f"{BASE_URL}/issueresolution/v1/{ACCT}"

RENDERED = {
    "renderedIssues": [
        {
            "title": "Misrepresentation",
            "impact": {"severity": "ERROR", "message": "Not showing on Shopping ads"},
            "actions": [
                {
                    "buttonLabel": "Request review",
                    "isAvailable": True,
                    "builtinUserInputAction": {
                        "actionContext": "CTX-1",
                        "flows": [
                            {
                                "id": "fixed",
                                "label": "I fixed the issue",
                                "dialogTitle": "Before you request a review",
                                "dialogCallout": {
                                    "fullMessage": {"simpleValue": "You can only request once."}
                                },
                                "inputs": [
                                    {
                                        "id": "confirm",
                                        "required": True,
                                        "label": {"simpleValue": "I fixed it"},
                                        "checkboxInput": {},
                                    },
                                    {
                                        "id": "reason",
                                        "required": True,
                                        "label": {"simpleValue": "What changed?"},
                                        "choiceInput": {
                                            "options": [
                                                {"id": "price", "label": {"simpleValue": "Price"}},
                                                {
                                                    "id": "other",
                                                    "label": {"simpleValue": "Other"},
                                                    "additionalInput": {
                                                        "id": "details",
                                                        "label": {"simpleValue": "Details"},
                                                        "textInput": {
                                                            "type": "GENERIC_LONG_TEXT",
                                                            "formatInfo": "Max 1000 chars",
                                                        },
                                                    },
                                                },
                                            ]
                                        },
                                    },
                                ],
                            }
                        ],
                    },
                },
                {
                    "buttonLabel": "Edit product",
                    "isAvailable": True,
                    "builtinSimpleAction": {"type": "EDIT_ITEM_ATTRIBUTE"},
                },
            ],
        },
        {
            "title": "Policy violation",
            "impact": {"severity": "ERROR"},
            "actions": [
                {
                    "buttonLabel": "Appeal",
                    "isAvailable": False,
                    "reasons": [{"message": "Review requested on Jan 03."}],
                    "externalAction": {
                        "type": "REVIEW_PRODUCT_ISSUE_IN_MERCHANT_CENTER",
                        "uri": "https://merchants.google.com/x",
                    },
                }
            ],
        },
        {
            "title": "Missing GTIN",
            "impact": {"severity": "WARNING"},
            "actions": [{"buttonLabel": "Learn more", "isAvailable": True, "externalAction": {}}],
        },
    ]
}


def _build(client: MerchantClient) -> dict:
    mcp = FastMCP("test")
    issue_resolution.register(mcp, client)
    return {name: tool.fn for name, tool in mcp._tool_manager._tools.items()}


def _audit_entries(client: MerchantClient) -> list[dict]:
    if not client.audit.path.exists():
        return []
    return [json.loads(x) for x in client.audit.path.read_text(encoding="utf-8").splitlines()]


@respx.mock
def test_list_review_options_for_product(client: MerchantClient) -> None:
    client.config.dry_run = True  # reads must still go through
    route = respx.post(f"{IR}/products/en~US~SKU1:renderproductissues").mock(
        return_value=httpx.Response(200, json=RENDERED)
    )

    out = _build(client)["gmc_list_review_options"](product_id="en~US~SKU1")

    body = json.loads(route.calls.last.request.content)
    assert body["userInputActionOption"] == "BUILT_IN_USER_INPUT_ACTIONS"
    # The GTIN issue has no review-type action, so it is left out.
    assert out["target"] == "en~US~SKU1"
    assert out["issues_with_review_actions"] == 2

    first = out["issues"][0]
    assert first["issue"] == "Misrepresentation"
    assert first["severity"] == "ERROR"
    assert len(first["actions"]) == 1  # the simple "Edit product" action is dropped
    action = first["actions"][0]
    assert action["kind"] == "request_in_api"
    assert action["available"] is True
    assert action["action_context"] == "CTX-1"
    flow = action["flows"][0]
    assert flow["flow_id"] == "fixed"
    assert flow["warning"] == "You can only request once."
    checkbox, choice = flow["inputs"]
    assert checkbox == {
        "field_id": "confirm",
        "label": "I fixed it",
        "required": True,
        "answer_with": "true or false",
    }
    assert [o["option_id"] for o in choice["options"]] == ["price", "other"]
    assert choice["options"][1]["additional_input"]["format"] == "Max 1000 chars"

    external = out["issues"][1]["actions"][0]
    assert external["kind"] == "external"
    assert external["available"] is False
    assert external["unavailable_reasons"] == ["Review requested on Jan 03."]
    assert external["url"] == "https://merchants.google.com/x"
    assert _audit_entries(client) == []


@respx.mock
def test_list_review_options_for_account(client: MerchantClient) -> None:
    route = respx.post(f"{IR}:renderaccountissues").mock(
        return_value=httpx.Response(200, json={"renderedIssues": []})
    )

    out = _build(client)["gmc_list_review_options"]()

    assert route.called
    assert out == {"target": "account", "issues_with_review_actions": 0, "issues": []}


@respx.mock
def test_request_review_builds_input_values_and_audits(client: MerchantClient) -> None:
    route = respx.post(f"{IR}:triggeraction").mock(
        return_value=httpx.Response(200, json={"message": "Review requested"})
    )

    out = _build(client)["gmc_request_review"](
        action_context="CTX-1",
        flow_id="fixed",
        answers={"confirm": True, "reason": {"choice": "other"}, "details": "New prices"},
    )

    assert out == {"message": "Review requested"}
    assert json.loads(route.calls.last.request.content) == {
        "actionContext": "CTX-1",
        "actionInput": {
            "actionFlowId": "fixed",
            "inputValues": [
                {"inputFieldId": "confirm", "checkboxInputValue": {"value": True}},
                {"inputFieldId": "reason", "choiceInputValue": {"choiceInputOptionId": "other"}},
                {"inputFieldId": "details", "textInputValue": {"value": "New prices"}},
            ],
        },
    }
    assert _audit_entries(client)[-1]["op"] == "request_review"


@respx.mock
def test_request_review_skipped_in_dry_run(client: MerchantClient) -> None:
    client.config.dry_run = True
    route = respx.post(f"{IR}:triggeraction").mock(return_value=httpx.Response(200, json={}))

    out = _build(client)["gmc_request_review"](action_context="CTX", flow_id="f")

    assert not route.called
    assert out.get("_dry_run") is True


def test_request_review_rejects_bad_answer(client: MerchantClient) -> None:
    with pytest.raises(ValueError):
        _build(client)["gmc_request_review"](action_context="CTX", flow_id="f", answers={"x": 3})


@respx.mock
def test_disapprovals_overview(client: MerchantClient) -> None:
    client.config.dry_run = True  # reads must still go through
    issue = {
        "type": {"code": "price_mismatch", "canonicalAttribute": "price"},
        "severity": {
            "aggregatedSeverity": "DISAPPROVED",
            "severityPerReportingContext": [
                {"reportingContext": "SHOPPING_ADS", "disapprovedCountries": ["GB"]}
            ],
        },
        "resolution": "MERCHANT_ACTION",
    }
    search = respx.post(f"{BASE_URL}/reports/v1/{ACCT}/reports:search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "productView": {
                            "id": "online~en~GB~SKU2",
                            "offerId": "SKU2",
                            "clickPotentialRank": "900",
                            "itemIssues": [issue],
                        }
                    },
                    {
                        "productView": {
                            "id": "online~en~GB~SKU1",
                            "offerId": "SKU1",
                            "title": "A",
                            "clickPotential": "HIGH",
                            "clickPotentialRank": "3",
                            "itemIssues": [issue],
                        }
                    },
                ]
            },
        )
    )
    respx.post(f"{IR}/products/online~en~GB~SKU1:renderproductissues").mock(
        return_value=httpx.Response(200, json=RENDERED)
    )
    respx.post(f"{IR}/products/online~en~GB~SKU2:renderproductissues").mock(
        return_value=httpx.Response(200, json={"renderedIssues": []})
    )

    out = _build(client)["gmc_disapprovals_overview"](max_products=10)

    query = json.loads(search.calls.last.request.content)["query"]
    assert "item_issues" in query
    assert query.endswith("LIMIT 10")
    # Highest click potential (lowest rank) comes first.
    assert [p["offer_id"] for p in out["products"]] == ["SKU1", "SKU2"]
    first = out["products"][0]
    assert first["reasons"] == [
        {
            "code": "price_mismatch",
            "attribute": "price",
            "severity": "DISAPPROVED",
            "resolution": "MERCHANT_ACTION",
            "where": {"SHOPPING_ADS": {"disapproved": ["GB"]}},
        }
    ]
    assert first["review_options"][0]["actions"][0]["action_context"] == "CTX-1"
    assert out["summary"]["top_reasons"] == [
        {"code": "price_mismatch", "attribute": "price", "products": 2}
    ]
    assert out["summary"]["reviews_requestable_now"] == 1
    assert _audit_entries(client) == []


@respx.mock
def test_disapprovals_overview_without_review_options(client: MerchantClient) -> None:
    respx.post(f"{BASE_URL}/reports/v1/{ACCT}/reports:search").mock(
        return_value=httpx.Response(
            200, json={"results": [{"productView": {"id": "en~GB~SKU1", "offerId": "SKU1"}}]}
        )
    )
    render = respx.post(f"{IR}/products/en~GB~SKU1:renderproductissues")

    out = _build(client)["gmc_disapprovals_overview"](include_review_options=False)

    assert not render.called
    assert "review_options" not in out["products"][0]
    assert "reviews_requestable_now" not in out["summary"]

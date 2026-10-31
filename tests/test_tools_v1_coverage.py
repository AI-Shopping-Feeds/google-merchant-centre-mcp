"""Tests for the Merchant API v1 coverage pass: new tools, corrected endpoint
paths, and read-only POST handling. All HTTP is mocked with respx."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from gmc_mcp.client import BASE_URL, MerchantClient
from gmc_mcp.tools import (
    account_config,
    accounts,
    diagnostics,
    feeds,
    homepage,
    inventory,
    issue_resolution,
    mca,
    notifications,
    omnichannel,
    order_tracking,
    product_studio,
    products,
    promotions,
    quotas,
    regions,
    return_policies,
    reviews,
)

ACCT = "accounts/1234567890"


def _build(module, client: MerchantClient) -> dict:
    mcp = FastMCP("test")
    module.register(mcp, client)
    return {name: tool.fn for name, tool in mcp._tool_manager._tools.items()}


def _audit_entries(client: MerchantClient) -> list[dict]:
    if not client.audit.path.exists():
        return []
    return [json.loads(x) for x in client.audit.path.read_text(encoding="utf-8").splitlines()]


def _body(route: respx.Route) -> dict:
    return json.loads(route.calls.last.request.content)


# ---------------------------------------------------------------- client


@respx.mock
def test_read_only_post_bypasses_dry_run_and_audit(client: MerchantClient) -> None:
    client.config.dry_run = True
    route = respx.post(f"{BASE_URL}/reports/v1/{ACCT}/reports:search").mock(
        return_value=httpx.Response(200, json={"results": [{"x": 1}]})
    )
    out = client.request(
        "POST", f"reports/v1/{ACCT}/reports:search", json_body={"query": "q"}, read_only=True
    )
    assert out == {"results": [{"x": 1}]}
    assert route.called
    assert _audit_entries(client) == []


def test_write_in_dry_run_is_not_sent(client: MerchantClient) -> None:
    client.config.dry_run = True
    with respx.mock(assert_all_called=False) as router:
        route = router.post(f"{BASE_URL}/accounts/v1/termsOfService/1:accept")
        fns = _build(account_config, client)
        out = fns["gmc_accept_tos"](tos_name="termsOfService/1")
    assert out["_dry_run"] is True
    assert not route.called
    assert _audit_entries(client)[-1]["dry_run"] is True


@respx.mock
def test_snapshot_returns_none_on_error(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/{ACCT}/missing").mock(
        return_value=httpx.Response(404, json={"error": "nope"})
    )
    assert client.snapshot(f"accounts/v1/{ACCT}/missing") is None


# ---------------------------------------------------------------- products


@respx.mock
def test_patch_product_sends_update_mask_and_audits_before(client: MerchantClient) -> None:
    pid = "en~US~SKU1"
    respx.get(f"{BASE_URL}/products/v1/{ACCT}/products/{pid}").mock(
        return_value=httpx.Response(200, json={"name": pid, "productAttributes": {"title": "Old"}})
    )
    route = respx.patch(f"{BASE_URL}/products/v1/{ACCT}/productInputs/{pid}").mock(
        return_value=httpx.Response(200, json={"name": pid})
    )
    fns = _build(products, client)
    fns["gmc_patch_product"](
        product_id=pid,
        product={"productAttributes": {"title": "New"}},
        data_source=f"{ACCT}/dataSources/42",
        update_mask="productAttributes.title",
    )
    params = route.calls.last.request.url.params
    assert params["updateMask"] == "productAttributes.title"
    assert params["dataSource"] == f"{ACCT}/dataSources/42"
    entry = _audit_entries(client)[-1]
    assert entry["op"] == "patch_product"
    assert entry["before"]["productAttributes"]["title"] == "Old"


@respx.mock
def test_bulk_delete_filter_status_only_deletes_matches(client: MerchantClient) -> None:
    respx.post(f"{BASE_URL}/reports/v1/{ACCT}/reports:search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"productView": {"offerId": "BAD", "feedLabel": "US", "languageCode": "en"}}
                ]
            },
        )
    )
    respx.get(f"{BASE_URL}/products/v1/{ACCT}/products").mock(
        return_value=httpx.Response(
            200,
            json={
                "products": [
                    {
                        "name": f"{ACCT}/products/en~US~BAD",
                        "offerId": "BAD",
                        "feedLabel": "US",
                        "contentLanguage": "en",
                        "dataSource": f"{ACCT}/dataSources/1",
                    },
                    {
                        "name": f"{ACCT}/products/en~US~GOOD",
                        "offerId": "GOOD",
                        "feedLabel": "US",
                        "contentLanguage": "en",
                        "dataSource": f"{ACCT}/dataSources/1",
                    },
                ]
            },
        )
    )
    bad = respx.delete(f"{BASE_URL}/products/v1/{ACCT}/productInputs/en~US~BAD").mock(
        return_value=httpx.Response(204)
    )
    good = respx.delete(f"{BASE_URL}/products/v1/{ACCT}/productInputs/en~US~GOOD").mock(
        return_value=httpx.Response(204)
    )
    fns = _build(products, client)
    out = fns["gmc_bulk_delete_products"](
        confirm="DELETE", filter_status="NOT_ELIGIBLE_OR_DISAPPROVED"
    )
    assert out["deleted_count"] == 1
    assert bad.called and not good.called


def test_bulk_delete_rejects_unknown_status(client: MerchantClient) -> None:
    fns = _build(products, client)
    out = fns["gmc_bulk_delete_products"](confirm="DELETE", filter_status="X' OR '1'='1")
    assert "filter_status must be one of" in out["error"]


@respx.mock
def test_rollback_patch_product_reinserts_snapshot(client: MerchantClient) -> None:
    before = {"offerId": "SKU1", "dataSource": f"{ACCT}/dataSources/9"}
    audit_id = client.audit.record(
        op="patch_product",
        resource="x",
        method="PATCH",
        url=f"{BASE_URL}/products/v1/{ACCT}/productInputs/en~US~SKU1",
        before=before,
    )
    route = respx.post(f"{BASE_URL}/products/v1/{ACCT}/productInputs:insert").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    fns = _build(diagnostics, client)
    fns["gmc_rollback"](audit_id=audit_id, confirm="ROLLBACK")
    assert route.calls.last.request.url.params["dataSource"] == f"{ACCT}/dataSources/9"


# ---------------------------------------------------------------- accounts


@respx.mock
def test_list_accounts_passes_filter(client: MerchantClient) -> None:
    route = respx.get(f"{BASE_URL}/accounts/v1/accounts").mock(
        return_value=httpx.Response(200, json={"accounts": [{"name": "a"}]})
    )
    fns = _build(accounts, client)
    out = fns["gmc_list_accounts"](filter='accountName = "*shop*"')
    assert out["count"] == 1
    assert route.calls.last.request.url.params["filter"] == 'accountName = "*shop*"'


@respx.mock
def test_list_subaccounts(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/{ACCT}:listSubaccounts").mock(
        return_value=httpx.Response(200, json={"accounts": [{"name": "a"}, {"name": "b"}]})
    )
    assert _build(accounts, client)["gmc_list_subaccounts"]()["count"] == 2


@respx.mock
def test_update_account(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/{ACCT}").mock(
        return_value=httpx.Response(200, json={"accountName": "Old"})
    )
    route = respx.patch(f"{BASE_URL}/accounts/v1/{ACCT}").mock(
        return_value=httpx.Response(200, json={"accountName": "New"})
    )
    fns = _build(accounts, client)
    fns["gmc_update_account"](account={"accountName": "New"}, update_mask="accountName")
    assert route.calls.last.request.url.params["updateMask"] == "accountName"
    assert _audit_entries(client)[-1]["before"] == {"accountName": "Old"}


def test_delete_account_refuses_without_confirm(client: MerchantClient) -> None:
    out = _build(accounts, client)["gmc_delete_account"]()
    assert "Refused" in out["error"]
    assert out["would_delete"] == ACCT


@respx.mock
def test_delete_account_with_confirm_and_force(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/accounts/555").mock(
        return_value=httpx.Response(200, json={"name": "accounts/555"})
    )
    route = respx.delete(f"{BASE_URL}/accounts/v1/accounts/555").mock(
        return_value=httpx.Response(204)
    )
    out = _build(accounts, client)["gmc_delete_account"](
        confirm="DELETE", account_id="555", force=True
    )
    assert out == {"deleted": "accounts/555"}
    assert route.calls.last.request.url.params["force"] == "true"


@respx.mock
def test_create_and_configure_account_body(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/accounts/v1/accounts:createAndConfigure").mock(
        return_value=httpx.Response(200, json={"name": "accounts/777"})
    )
    _build(accounts, client)["gmc_create_and_configure_account"](
        account={"accountName": "Client A"},
        users=[{"userId": "a@b.com", "user": {"accessRights": ["ADMIN"]}}],
        services=[{"provider": ACCT, "accountAggregation": {}}],
    )
    body = _body(route)
    assert body["account"] == {"accountName": "Client A"}
    assert body["user"][0]["userId"] == "a@b.com"
    assert body["service"][0]["accountAggregation"] == {}
    assert "setAlias" not in body


@respx.mock
def test_create_test_account(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/accounts/v1/{ACCT}:createTestAccount").mock(
        return_value=httpx.Response(200, json={"name": "accounts/888"})
    )
    _build(accounts, client)["gmc_create_test_account"](account={"accountName": "t"})
    assert route.called
    assert _audit_entries(client)[-1]["op"] == "create_test_account"


@respx.mock
def test_users_get_update_verify(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/{ACCT}/users/a@b.com").mock(
        return_value=httpx.Response(200, json={"accessRights": ["STANDARD"]})
    )
    patch = respx.patch(f"{BASE_URL}/accounts/v1/{ACCT}/users/a@b.com").mock(
        return_value=httpx.Response(200, json={"accessRights": ["ADMIN"]})
    )
    verify = respx.patch(f"{BASE_URL}/accounts/v1/{ACCT}/users/me:verifySelf").mock(
        return_value=httpx.Response(200, json={"state": "VERIFIED"})
    )
    fns = _build(accounts, client)
    assert fns["gmc_get_user"](email="a@b.com")["accessRights"] == ["STANDARD"]
    fns["gmc_update_user"](email="a@b.com", access_rights=["ADMIN"])
    assert patch.calls.last.request.url.params["updateMask"] == "accessRights"
    assert _body(patch) == {"accessRights": ["ADMIN"]}
    assert fns["gmc_verify_self"]()["state"] == "VERIFIED"
    assert verify.called


@respx.mock
def test_programs_get_enable_disable(client: MerchantClient) -> None:
    base = f"{BASE_URL}/accounts/v1/{ACCT}/programs/free-listings"
    respx.get(base).mock(return_value=httpx.Response(200, json={"state": "ENABLED"}))
    enable = respx.post(f"{base}:enable").mock(return_value=httpx.Response(200, json={}))
    disable = respx.post(f"{base}:disable").mock(return_value=httpx.Response(200, json={}))
    fns = _build(accounts, client)
    assert fns["gmc_get_program"](program_id="free-listings")["state"] == "ENABLED"
    fns["gmc_enable_program"](program_id="free-listings")
    fns["gmc_disable_program"](program_id="free-listings")
    assert enable.called and disable.called
    ops = [e["op"] for e in _audit_entries(client)]
    assert ops == ["enable_program", "disable_program"]


@respx.mock
def test_developer_registration(client: MerchantClient) -> None:
    base = f"{BASE_URL}/accounts/v1/{ACCT}/developerRegistration"
    respx.get(base).mock(return_value=httpx.Response(200, json={"gcpIds": ["1"]}))
    reg = respx.post(f"{base}:registerGcp").mock(return_value=httpx.Response(200, json={}))
    unreg = respx.post(f"{base}:unregisterGcp").mock(return_value=httpx.Response(200, json={}))
    which = respx.get(f"{BASE_URL}/accounts/v1/accounts:getAccountForGcpRegistration").mock(
        return_value=httpx.Response(200, json={"name": ACCT})
    )
    fns = _build(accounts, client)
    assert fns["gmc_get_developer_registration"]()["gcpIds"] == ["1"]
    fns["gmc_register_gcp"](developer_email="dev@example.com")
    assert _body(reg) == {"developerEmail": "dev@example.com"}
    fns["gmc_unregister_gcp"]()
    assert unreg.called
    assert fns["gmc_get_account_for_gcp_registration"]()["name"] == ACCT
    assert which.called


# ---------------------------------------------------------------- account_config / ToS


@respx.mock
def test_tos_endpoints(client: MerchantClient) -> None:
    latest = respx.get(f"{BASE_URL}/accounts/v1/termsOfService:retrieveLatest").mock(
        return_value=httpx.Response(200, json={"name": "termsOfService/132"})
    )
    get = respx.get(f"{BASE_URL}/accounts/v1/termsOfService/132").mock(
        return_value=httpx.Response(200, json={"name": "termsOfService/132"})
    )
    state = respx.get(
        f"{BASE_URL}/accounts/v1/{ACCT}/termsOfServiceAgreementStates/MERCHANT_CENTER-US"
    ).mock(return_value=httpx.Response(200, json={"regionCode": "US"}))
    app = respx.get(
        f"{BASE_URL}/accounts/v1/{ACCT}/termsOfServiceAgreementStates:retrieveForApplication"
    ).mock(return_value=httpx.Response(200, json={"regionCode": "001"}))
    accept = respx.post(f"{BASE_URL}/accounts/v1/termsOfService/132:accept").mock(
        return_value=httpx.Response(200, json={})
    )
    fns = _build(account_config, client)
    fns["gmc_get_latest_tos"](region_code="US")
    assert latest.calls.last.request.url.params["kind"] == "MERCHANT_CENTER"
    fns["gmc_get_tos"](tos_name="132")
    fns["gmc_get_tos_agreement_state"]()
    fns["gmc_retrieve_tos_agreement_for_application"]()
    fns["gmc_accept_tos"](tos_name="termsOfService/132", region_code="US")
    params = accept.calls.last.request.url.params
    assert params["account"] == ACCT
    assert params["regionCode"] == "US"
    assert get.called and state.called and app.called


def test_account_tax_tools_removed(client: MerchantClient) -> None:
    fns = _build(account_config, client)
    assert "gmc_get_account_tax" not in fns
    assert "gmc_update_account_tax" not in fns


# ---------------------------------------------------------------- feeds / datasources


@respx.mock
def test_datasource_create_patch_file_upload(client: MerchantClient) -> None:
    base = f"{BASE_URL}/datasources/v1/{ACCT}/dataSources"
    create = respx.post(base).mock(return_value=httpx.Response(200, json={"name": "ds"}))
    respx.get(f"{base}/42").mock(return_value=httpx.Response(200, json={"displayName": "Old"}))
    patch = respx.patch(f"{base}/42").mock(return_value=httpx.Response(200, json={}))
    upload = respx.get(f"{base}/42/fileUploads/latest").mock(
        return_value=httpx.Response(200, json={"processingState": "SUCCEEDED"})
    )
    fns = _build(feeds, client)
    fns["gmc_create_datasource"](
        data_source={"displayName": "Stock", "localInventoryDataSource": {"feedLabel": "US"}}
    )
    assert "localInventoryDataSource" in _body(create)
    fns["gmc_update_datasource"](
        datasource_id="42", data_source={"displayName": "New"}, update_mask="displayName"
    )
    assert patch.calls.last.request.url.params["updateMask"] == "displayName"
    assert _audit_entries(client)[-1]["before"] == {"displayName": "Old"}
    assert fns["gmc_get_datasource_file_upload"](datasource_id="42")["processingState"] == (
        "SUCCEEDED"
    )
    assert upload.called


# ---------------------------------------------------------------- inventory


@respx.mock
def test_delete_local_and_regional_inventory(client: MerchantClient) -> None:
    pid = "en~US~SKU1"
    base = f"{BASE_URL}/inventories/v1/{ACCT}/products/{pid}"
    respx.get(f"{base}/localInventories").mock(
        return_value=httpx.Response(200, json={"localInventories": [{"storeCode": "S1"}]})
    )
    respx.get(f"{base}/regionalInventories").mock(
        return_value=httpx.Response(200, json={"regionalInventories": [{"region": "R1"}]})
    )
    local = respx.delete(f"{base}/localInventories/S1").mock(return_value=httpx.Response(204))
    regional = respx.delete(f"{base}/regionalInventories/R1").mock(
        return_value=httpx.Response(204)
    )
    fns = _build(inventory, client)
    fns["gmc_delete_local_inventory"](product_id=pid, store_code="S1")
    fns["gmc_delete_regional_inventory"](product_id=pid, region="R1")
    assert local.called and regional.called
    entries = _audit_entries(client)
    assert entries[0]["before"] == {"storeCode": "S1"}
    assert entries[1]["before"] == {"region": "R1"}


# ---------------------------------------------------------------- issue resolution


@respx.mock
def test_render_issues_are_read_only(client: MerchantClient) -> None:
    client.config.dry_run = True
    base = f"{BASE_URL}/issueresolution/v1/{ACCT}"
    acc = respx.post(f"{base}:renderaccountissues").mock(
        return_value=httpx.Response(200, json={"issues": [{"title": "x"}]})
    )
    prod = respx.post(f"{base}/products/en~US~SKU1:renderproductissues").mock(
        return_value=httpx.Response(200, json={"issues": []})
    )
    fns = _build(issue_resolution, client)
    out = fns["gmc_render_account_issues"](time_zone="America/New_York")
    assert out["issues"][0]["title"] == "x"
    assert acc.calls.last.request.url.params["timeZone"] == "America/New_York"
    assert _body(acc)["userInputActionOption"] == "REDIRECT_TO_MERCHANT_CENTER"
    fns["gmc_render_product_issues"](product_id="en~US~SKU1")
    assert prod.called
    assert _audit_entries(client) == []


@respx.mock
def test_trigger_issue_action_is_audited(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/issueresolution/v1/{ACCT}:triggeraction").mock(
        return_value=httpx.Response(200, json={"message": "ok"})
    )
    fns = _build(issue_resolution, client)
    fns["gmc_trigger_issue_action"](action_context="ctx", action_input={"actionFlowId": "f"})
    assert _body(route) == {"actionContext": "ctx", "actionInput": {"actionFlowId": "f"}}
    assert _audit_entries(client)[-1]["op"] == "trigger_issue_action"


@respx.mock
def test_list_aggregate_product_statuses(client: MerchantClient) -> None:
    route = respx.get(f"{BASE_URL}/issueresolution/v1/{ACCT}/aggregateProductStatuses").mock(
        return_value=httpx.Response(200, json={"aggregateProductStatuses": [{"country": "US"}]})
    )
    fns = _build(issue_resolution, client)
    out = fns["gmc_list_aggregate_product_statuses"](filter='country = "US"')
    assert out["count"] == 1
    assert route.calls.last.request.url.params["filter"] == 'country = "US"'


# ---------------------------------------------------------------- mca


@respx.mock
def test_propose_account_service_body(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/accounts/v1/{ACCT}/services:propose").mock(
        return_value=httpx.Response(200, json={"name": "s"})
    )
    fns = _build(mca, client)
    fns["gmc_propose_account_service"](
        provider="accounts/999", service_type="account_aggregation", external_account_id="ext"
    )
    assert _body(route) == {
        "provider": "accounts/999",
        "accountService": {"accountAggregation": {}, "externalAccountId": "ext"},
    }
    assert "error" in fns["gmc_propose_account_service"](provider="x", service_type="BOGUS")


@respx.mock
def test_account_services_list_and_get(client: MerchantClient) -> None:
    base = f"{BASE_URL}/accounts/v1/{ACCT}/services"
    respx.get(base).mock(
        return_value=httpx.Response(200, json={"accountServices": [{"name": "a"}]})
    )
    respx.get(f"{base}/s1").mock(return_value=httpx.Response(200, json={"name": "s1"}))
    fns = _build(mca, client)
    assert fns["gmc_list_account_services"]()["count"] == 1
    assert fns["gmc_get_account_service"](service_id="s1")["name"] == "s1"
    assert "gmc_create_aggregation" not in fns


# ---------------------------------------------------------------- omnichannel


@respx.mock
def test_gbp_and_lfp_provider_links(client: MerchantClient) -> None:
    base = f"{BASE_URL}/accounts/v1/{ACCT}"
    gbp = respx.post(f"{base}/gbpAccounts:linkGbpAccount").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get(f"{base}/omnichannelSettings/US/lfpProviders:find").mock(
        return_value=httpx.Response(200, json={"lfpProviders": [{"name": "p"}]})
    )
    respx.get(f"{base}/omnichannelSettings/US").mock(
        return_value=httpx.Response(200, json={"regionCode": "US"})
    )
    link = respx.post(f"{base}/omnichannelSettings/US/lfpProviders/123:linkLfpProvider").mock(
        return_value=httpx.Response(200, json={})
    )
    fns = _build(omnichannel, client)
    fns["gmc_link_gbp_account"](gbp_email="owner@example.com")
    assert _body(gbp) == {"gbpEmail": "owner@example.com"}
    assert fns["gmc_find_lfp_providers"](region_code="US")["count"] == 1
    fns["gmc_link_lfp_provider"](
        region_code="US", lfp_provider_id="123", external_account_id="m-1"
    )
    assert _body(link) == {"externalAccountId": "m-1"}


# ---------------------------------------------------------------- notifications


@respx.mock
def test_notification_get_and_update(client: MerchantClient) -> None:
    path = f"{BASE_URL}/notifications/v1/{ACCT}/notificationsubscriptions/7"
    respx.get(path).mock(return_value=httpx.Response(200, json={"callBackUri": "https://old"}))
    route = respx.patch(path).mock(return_value=httpx.Response(200, json={}))
    fns = _build(notifications, client)
    assert fns["gmc_get_subscription"](subscription_id="7")["callBackUri"] == "https://old"
    fns["gmc_update_subscription"](
        subscription_id="7", subscription={"callBackUri": "https://new"}
    )
    assert route.calls.last.request.url.params["updateMask"] == "callBackUri"
    assert _audit_entries(client)[-1]["before"] == {"callBackUri": "https://old"}


# ---------------------------------------------------------------- promotions


@respx.mock
def test_insert_promotion_sends_request_body(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/promotions/v1/{ACCT}/promotions:insert").mock(
        return_value=httpx.Response(200, json={})
    )
    fns = _build(promotions, client)
    fns["gmc_insert_promotion"](
        promotion={"promotionId": "P1"}, data_source=f"{ACCT}/dataSources/5"
    )
    assert _body(route) == {
        "promotion": {"promotionId": "P1"},
        "dataSource": f"{ACCT}/dataSources/5",
    }
    assert "dataSource" not in route.calls.last.request.url.params


# ---------------------------------------------------------------- quotas


@respx.mock
def test_account_limits(client: MerchantClient) -> None:
    lst = respx.get(f"{BASE_URL}/quota/v1/{ACCT}/limits").mock(
        return_value=httpx.Response(200, json={"accountLimits": [{"name": "l"}]})
    )
    respx.get(f"{BASE_URL}/quota/v1/{ACCT}/limits/products~ADS_NON_EEA").mock(
        return_value=httpx.Response(200, json={"name": "products~ADS_NON_EEA"})
    )
    fns = _build(quotas, client)
    assert fns["gmc_list_account_limits"]()["count"] == 1
    assert lst.calls.last.request.url.params["filter"] == 'type = "products"'
    assert fns["gmc_get_account_limit"](limit_id="products~ADS_NON_EEA")["name"]


# ---------------------------------------------------------------- regions


@respx.mock
def test_create_region_postal_body(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/accounts/v1/{ACCT}/regions").mock(
        return_value=httpx.Response(200, json={})
    )
    fns = _build(regions, client)
    assert "error" in fns["gmc_create_region"](
        region_id="r", display_name="R", postal_code_prefixes=["90"]
    )
    fns["gmc_create_region"](
        region_id="us-west",
        display_name="West",
        postal_code_prefixes=["90"],
        postal_code_ranges=[{"firstPostalCode": "94000", "lastPostalCode": "94999"}],
        postal_region_code="US",
    )
    assert route.calls.last.request.url.params["regionId"] == "us-west"
    assert _body(route)["postalCodeArea"] == {
        "regionCode": "US",
        "postalCodes": [{"begin": "90*"}, {"begin": "94000", "end": "94999"}],
    }


@respx.mock
def test_batch_regions(client: MerchantClient) -> None:
    base = f"{BASE_URL}/accounts/v1/{ACCT}/regions"
    create = respx.post(f"{base}:batchCreate").mock(return_value=httpx.Response(200, json={}))
    update = respx.post(f"{base}:batchUpdate").mock(return_value=httpx.Response(200, json={}))
    delete = respx.post(f"{base}:batchDelete").mock(return_value=httpx.Response(200, json={}))
    respx.get(f"{base}/a").mock(return_value=httpx.Response(200, json={"displayName": "A"}))
    fns = _build(regions, client)
    fns["gmc_batch_create_regions"](
        regions=[{"regionId": "a", "region": {"displayName": "A"}}]
    )
    assert _body(create) == {"requests": [{"regionId": "a", "region": {"displayName": "A"}}]}
    fns["gmc_batch_update_regions"](
        updates=[{"region_id": "a", "region": {"displayName": "B"}, "update_mask": "displayName"}]
    )
    assert _body(update)["requests"][0] == {
        "region": {"displayName": "B", "name": f"{ACCT}/regions/a"},
        "updateMask": "displayName",
    }
    assert "Refused" in fns["gmc_batch_delete_regions"](region_ids=["a"])["error"]
    assert not delete.called
    fns["gmc_batch_delete_regions"](region_ids=["a"], confirm="DELETE")
    assert _body(delete) == {"requests": [{"name": f"{ACCT}/regions/a"}]}
    assert _audit_entries(client)[-1]["before"] == [{"displayName": "A"}]


# ---------------------------------------------------------------- return policies / reviews


@respx.mock
def test_update_return_policy_uses_v1beta(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/{ACCT}/onlineReturnPolicies/p1").mock(
        return_value=httpx.Response(200, json={"label": "old"})
    )
    route = respx.patch(f"{BASE_URL}/accounts/v1beta/{ACCT}/onlineReturnPolicies/p1").mock(
        return_value=httpx.Response(200, json={"label": "new"})
    )
    fns = _build(return_policies, client)
    fns["gmc_update_return_policy"](policy_id="p1", policy={"label": "new"}, update_mask="label")
    assert route.called
    assert _audit_entries(client)[-1]["before"] == {"label": "old"}


@respx.mock
def test_product_review_insert_uses_reviews_v1(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/reviews/v1/{ACCT}/productReviews:insert").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get(f"{BASE_URL}/reviews/v1/{ACCT}/productReviews").mock(
        return_value=httpx.Response(200, json={"productReviews": [{"name": "r"}]})
    )
    fns = _build(reviews, client)
    fns["gmc_insert_product_review"](
        review={"productReviewId": "r1"}, data_source=f"{ACCT}/dataSources/3"
    )
    assert route.calls.last.request.url.params["dataSource"] == f"{ACCT}/dataSources/3"
    assert fns["gmc_list_product_reviews"]()["count"] == 1


@respx.mock
def test_merchant_review_insert_uses_v1beta(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/reviews/v1beta/{ACCT}/merchantReviews:insert").mock(
        return_value=httpx.Response(200, json={})
    )
    fns = _build(reviews, client)
    fns["gmc_insert_merchant_review"](
        review={"merchantReviewId": "m1"}, data_source=f"{ACCT}/dataSources/4"
    )
    assert route.called


# ---------------------------------------------------------------- homepage


@respx.mock
def test_unclaim_homepage_captures_before(client: MerchantClient) -> None:
    respx.get(f"{BASE_URL}/accounts/v1/{ACCT}/homepage").mock(
        return_value=httpx.Response(200, json={"claimed": True})
    )
    respx.post(f"{BASE_URL}/accounts/v1/{ACCT}/homepage:unclaim").mock(
        return_value=httpx.Response(200, json={"claimed": False})
    )
    _build(homepage, client)["gmc_unclaim_homepage"]()
    assert _audit_entries(client)[-1]["before"] == {"claimed": True}


# ---------------------------------------------------------------- order tracking


@respx.mock
def test_create_order_tracking_signal(client: MerchantClient) -> None:
    route = respx.post(f"{BASE_URL}/ordertracking/v1/{ACCT}/orderTrackingSignals").mock(
        return_value=httpx.Response(200, json={"orderTrackingSignalId": "1"})
    )
    fns = _build(order_tracking, client)
    fns["gmc_create_order_tracking_signal"](
        signal={"orderId": "O1"}, order_tracking_signal_id="sig-1"
    )
    assert route.calls.last.request.url.params["orderTrackingSignalId"] == "sig-1"
    assert _body(route) == {"orderId": "O1"}
    assert _audit_entries(client)[-1]["op"] == "create_order_tracking_signal"


# ---------------------------------------------------------------- product studio (alpha)


@respx.mock
def test_product_studio_calls(client: MerchantClient) -> None:
    base = f"{BASE_URL}/productstudio/v1alpha/{ACCT}"
    text = respx.post(f"{base}:generateProductTextSuggestions").mock(
        return_value=httpx.Response(200, json={"title": {"text": "T"}})
    )
    bg = respx.post(f"{base}/generatedImages:generateProductImageBackground").mock(
        return_value=httpx.Response(200, json={})
    )
    rm = respx.post(f"{base}/generatedImages:removeProductImageBackground").mock(
        return_value=httpx.Response(200, json={})
    )
    up = respx.post(f"{base}/generatedImages:upscaleProductImage").mock(
        return_value=httpx.Response(200, json={})
    )
    fns = _build(product_studio, client)
    out = fns["gmc_generate_product_text_suggestions"](
        product_attributes={"title": "Shirt"},
        product_image_uri="https://x/img.jpg",
        output_spec={"workflowId": "title"},
    )
    assert out["title"]["text"] == "T"
    assert _body(text)["productInfo"] == {
        "productAttributes": {"title": "Shirt"},
        "productImage": {"uri": "https://x/img.jpg"},
    }
    fns["gmc_generate_product_image_background"](
        product_description="mug", background_description="table", image_uri="https://x/m.jpg"
    )
    assert _body(bg)["config"]["backgroundDescription"] == "table"
    fns["gmc_remove_product_image_background"](
        image_uri="https://x/m.jpg", background_color={"red": 255, "green": 255, "blue": 255}
    )
    assert _body(rm)["config"]["backgroundColor"]["red"] == 255
    fns["gmc_upscale_product_image"](image_bytes="aGVsbG8=")
    assert _body(up)["inputImage"] == {"imageBytes": "aGVsbG8="}
    assert _audit_entries(client) == []


def test_product_studio_requires_image(client: MerchantClient) -> None:
    fns = _build(product_studio, client)
    with pytest.raises(ValueError):
        fns["gmc_upscale_product_image"]()


# ---------------------------------------------------------------- registry


def test_all_modules_register_unique_gmc_tools(client: MerchantClient) -> None:
    from gmc_mcp import tools

    mcp = FastMCP("test")
    for name in tools.__all__:
        getattr(tools, name).register(mcp, client)
    names = list(mcp._tool_manager._tools)
    assert all(n.startswith("gmc_") for n in names)
    assert len(names) == 159  # FastMCP drops duplicates, so this also proves uniqueness


def test_build_server_registers_every_tool(config, monkeypatch) -> None:
    from gmc_mcp import server

    from .conftest import FakeAuth

    monkeypatch.setattr(server, "load_auth", lambda **_: FakeAuth())
    mcp = server.build_server(config)
    names = set(mcp._tool_manager._tools)
    assert len(names) == 163  # 159 module tools + 4 meta tools
    assert {"gmc_render_account_issues", "gmc_create_order_tracking_signal",
            "gmc_upscale_product_image", "gmc_describe_server"} <= names

"""Title and MCP annotations for every gmc_* tool.

`GmcMCPServer.tool()` looks each tool up here by name, so the tool modules stay
free of metadata. Every tool must have an entry: tests/test_mcp_client.py fails
if a registered tool is missing or an entry has no tool.

Annotation kinds (all API tools are open-world: they call the Merchant API):

* READ: no change to the Merchant Center account. Includes read-only POSTs
  such as reports:search, issue rendering and Product Studio generation.
* WRITE: creates something or triggers an action; repeating it has an effect.
* UPSERT: an update, insert-or-update or toggle; repeating it changes nothing.
* DESTRUCTIVE: deletes, removes, revokes or is otherwise hard to undo.
* LOCAL_*: touches only this server (audit log, session settings, local files).
"""

from __future__ import annotations

from typing import NamedTuple

from mcp.types import ToolAnnotations


def _ann(*, read_only: bool, destructive: bool, idempotent: bool, open_world: bool = True):
    return ToolAnnotations(
        read_only_hint=read_only,
        destructive_hint=destructive,
        idempotent_hint=idempotent,
        open_world_hint=open_world,
    )


READ = _ann(read_only=True, destructive=False, idempotent=True)
# Read-only but non-deterministic (AI generation): same input, different output.
GENERATE = _ann(read_only=True, destructive=False, idempotent=False)
WRITE = _ann(read_only=False, destructive=False, idempotent=False)
UPSERT = _ann(read_only=False, destructive=False, idempotent=True)
DESTRUCTIVE = _ann(read_only=False, destructive=True, idempotent=True)
DESTRUCTIVE_ONCE = _ann(read_only=False, destructive=True, idempotent=False)
LOCAL_READ = _ann(read_only=True, destructive=False, idempotent=True, open_world=False)
LOCAL_SETTING = _ann(read_only=False, destructive=False, idempotent=True, open_world=False)
# Reads the API and writes JSON files on this machine (overwriting earlier exports).
LOCAL_EXPORT = _ann(read_only=False, destructive=False, idempotent=True)


class ToolSpec(NamedTuple):
    title: str
    annotations: ToolAnnotations


# Registered regardless of GMC_TOOL_GROUPS and GMC_READ_ONLY.
ALWAYS_REGISTERED = frozenset(
    {"gmc_describe_server", "gmc_audit_lookup", "gmc_audit_tail", "gmc_set_dry_run"}
)

_CATALOG: dict[str, tuple[str, ToolAnnotations]] = {
    # server (meta)
    "gmc_describe_server": ("Describe the server configuration", LOCAL_READ),
    "gmc_audit_lookup": ("Look up an audit log entry", LOCAL_READ),
    "gmc_audit_tail": ("Show recent audit log entries", LOCAL_READ),
    "gmc_set_dry_run": ("Turn dry-run mode on or off", LOCAL_SETTING),
    # products
    "gmc_list_products": ("List products", READ),
    "gmc_get_product": ("Get a product", READ),
    "gmc_insert_product": ("Insert or update a product", UPSERT),
    "gmc_update_product": ("Update a product", UPSERT),
    "gmc_patch_product": ("Patch a product", UPSERT),
    "gmc_delete_product": ("Delete a product", DESTRUCTIVE),
    "gmc_bulk_delete_products": ("Bulk-delete products", DESTRUCTIVE),
    "gmc_list_disapproved_products": ("List disapproved products", READ),
    # inventory
    "gmc_update_regional_inventory": ("Set a product's regional inventory", UPSERT),
    "gmc_update_local_inventory": ("Set a product's local inventory", UPSERT),
    "gmc_list_regional_inventories": ("List a product's regional inventories", READ),
    "gmc_list_local_inventories": ("List a product's local inventories", READ),
    "gmc_delete_local_inventory": ("Delete a product's local inventory", DESTRUCTIVE),
    "gmc_delete_regional_inventory": ("Delete a product's regional inventory", DESTRUCTIVE),
    # issues
    "gmc_list_account_issues": ("List account issues", READ),
    "gmc_get_product_status": ("Get a product's status", READ),
    "gmc_summarize_product_issues": ("Summarize product issues", READ),
    # reports
    "gmc_query_report": ("Run a reports query", READ),
    "gmc_product_performance": ("Report product performance", READ),
    "gmc_price_competitiveness": ("Report price competitiveness", READ),
    "gmc_best_sellers": ("Report best sellers", READ),
    "gmc_zero_click_products": ("Find products with impressions but no clicks", READ),
    "gmc_revenue_by_brand": ("Report revenue by brand", READ),
    "gmc_category_performance": ("Report performance by category", READ),
    "gmc_competitive_visibility_top_merchants": ("Report top competing merchants", READ),
    "gmc_price_insights": ("Report suggested prices", READ),
    "gmc_demoted_products": ("Find demoted products", READ),
    # promotions
    "gmc_list_promotions": ("List promotions", READ),
    "gmc_get_promotion": ("Get a promotion", READ),
    "gmc_insert_promotion": ("Insert or update a promotion", UPSERT),
    # accounts
    "gmc_get_account": ("Get the account", READ),
    "gmc_list_accounts": ("List accessible accounts", READ),
    "gmc_list_subaccounts": ("List sub-accounts", READ),
    "gmc_update_account": ("Update the account", UPSERT),
    "gmc_delete_account": ("Delete an account", DESTRUCTIVE),
    "gmc_create_and_configure_account": ("Create and configure an account", WRITE),
    "gmc_create_test_account": ("Create a test account", WRITE),
    "gmc_get_business_info": ("Get business info", READ),
    "gmc_update_business_info": ("Update business info", UPSERT),
    "gmc_list_users": ("List users", READ),
    "gmc_add_user": ("Add a user", WRITE),
    "gmc_remove_user": ("Remove a user", DESTRUCTIVE),
    "gmc_get_user": ("Get a user", READ),
    "gmc_update_user": ("Update a user's access", UPSERT),
    "gmc_verify_self": ("Verify the calling user", UPSERT),
    "gmc_get_shipping_settings": ("Get shipping settings", READ),
    "gmc_update_shipping_settings": ("Replace shipping settings", UPSERT),
    "gmc_list_programs": ("List programs", READ),
    "gmc_get_program": ("Get a program", READ),
    "gmc_enable_program": ("Enable a program", UPSERT),
    # Stops listings in that program (e.g. Shopping ads) until re-enabled.
    "gmc_disable_program": ("Disable a program", DESTRUCTIVE),
    "gmc_get_developer_registration": ("Get the developer registration", READ),
    "gmc_register_gcp": ("Register the GCP project", UPSERT),
    # Cuts off this project's API access to the account.
    "gmc_unregister_gcp": ("Unregister the GCP project", DESTRUCTIVE),
    "gmc_get_account_for_gcp_registration": (
        "Get the account registered to this GCP project",
        READ,
    ),
    # notifications
    "gmc_list_subscriptions": ("List notification subscriptions", READ),
    "gmc_subscribe": ("Subscribe to notifications", WRITE),
    "gmc_unsubscribe": ("Delete a notification subscription", DESTRUCTIVE),
    "gmc_get_subscription": ("Get a notification subscription", READ),
    "gmc_update_subscription": ("Update a notification subscription", UPSERT),
    # feeds
    "gmc_list_datasources": ("List data sources", READ),
    "gmc_get_datasource": ("Get a data source", READ),
    "gmc_create_supplemental_feed": ("Create a supplemental feed", WRITE),
    "gmc_create_primary_feed": ("Create a primary feed", WRITE),
    "gmc_create_datasource": ("Create a data source", WRITE),
    "gmc_update_datasource": ("Update a data source", UPSERT),
    "gmc_get_datasource_file_upload": ("Get a data source's latest file upload", READ),
    "gmc_delete_datasource": ("Delete a data source", DESTRUCTIVE),
    "gmc_fetch_datasource": ("Fetch a data source now", WRITE),
    # return policies
    "gmc_list_return_policies": ("List return policies", READ),
    "gmc_get_return_policy": ("Get a return policy", READ),
    "gmc_create_return_policy": ("Create a return policy", WRITE),
    "gmc_update_return_policy": ("Update a return policy", UPSERT),
    "gmc_delete_return_policy": ("Delete a return policy", DESTRUCTIVE),
    # homepage
    "gmc_get_homepage": ("Get the homepage", READ),
    "gmc_update_homepage": ("Update the homepage", UPSERT),
    "gmc_claim_homepage": ("Claim the homepage", UPSERT),
    "gmc_unclaim_homepage": ("Unclaim the homepage", DESTRUCTIVE),
    # account config
    "gmc_get_business_identity": ("Get business identity", READ),
    "gmc_update_business_identity": ("Update business identity", UPSERT),
    "gmc_get_checkout_settings": ("Get checkout settings", READ),
    "gmc_create_checkout_settings": ("Create checkout settings", WRITE),
    "gmc_update_checkout_settings": ("Update checkout settings", UPSERT),
    "gmc_delete_checkout_settings": ("Delete checkout settings", DESTRUCTIVE),
    "gmc_get_automatic_improvements": ("Get automatic improvements", READ),
    "gmc_update_automatic_improvements": ("Update automatic improvements", UPSERT),
    "gmc_get_autofeed_settings": ("Get autofeed settings", READ),
    "gmc_update_autofeed_settings": ("Update autofeed settings", UPSERT),
    "gmc_get_email_preferences": ("Get email preferences", READ),
    "gmc_update_email_preferences": ("Update email preferences", UPSERT),
    "gmc_get_latest_tos": ("Get the latest terms of service", READ),
    "gmc_get_tos": ("Get a terms of service version", READ),
    "gmc_get_tos_agreement_state": ("Get the terms of service agreement state", READ),
    "gmc_retrieve_tos_agreement_for_application": (
        "Get the Merchant Center terms of service agreement",
        READ,
    ),
    # Accepting terms of service is a legal agreement that cannot be withdrawn here.
    "gmc_accept_tos": ("Accept terms of service", DESTRUCTIVE),
    # quotas
    "gmc_list_quotas": ("List API quotas", READ),
    "gmc_list_account_limits": ("List account limits", READ),
    "gmc_get_account_limit": ("Get an account limit", READ),
    # reviews
    "gmc_list_merchant_reviews": ("List merchant reviews", READ),
    "gmc_get_merchant_review": ("Get a merchant review", READ),
    "gmc_insert_merchant_review": ("Insert or update a merchant review", UPSERT),
    "gmc_delete_merchant_review": ("Delete a merchant review", DESTRUCTIVE),
    "gmc_list_product_reviews": ("List product reviews", READ),
    "gmc_get_product_review": ("Get a product review", READ),
    "gmc_insert_product_review": ("Insert or update a product review", UPSERT),
    "gmc_delete_product_review": ("Delete a product review", DESTRUCTIVE),
    # conversions
    "gmc_list_conversion_sources": ("List conversion sources", READ),
    "gmc_get_conversion_source": ("Get a conversion source", READ),
    "gmc_create_conversion_source": ("Create a conversion source", WRITE),
    "gmc_update_conversion_source": ("Update a conversion source", UPSERT),
    "gmc_delete_conversion_source": ("Delete a conversion source", DESTRUCTIVE),
    "gmc_undelete_conversion_source": ("Restore a deleted conversion source", UPSERT),
    # omnichannel
    "gmc_list_omnichannel_settings": ("List omnichannel settings", READ),
    "gmc_get_omnichannel_settings": ("Get omnichannel settings", READ),
    "gmc_create_omnichannel_settings": ("Create omnichannel settings", WRITE),
    "gmc_update_omnichannel_settings": ("Update omnichannel settings", UPSERT),
    "gmc_request_inventory_verification": ("Request inventory verification", WRITE),
    "gmc_find_lfp_providers": ("Find local feed partners", READ),
    "gmc_link_lfp_provider": ("Link a local feed partner", UPSERT),
    "gmc_link_gbp_account": ("Link a Business Profile account", UPSERT),
    "gmc_list_gbp_accounts": ("List linked Business Profile accounts", READ),
    # lfp
    "gmc_lfp_list_stores": ("List LFP stores", READ),
    "gmc_lfp_get_store": ("Get an LFP store", READ),
    "gmc_lfp_insert_store": ("Insert or update an LFP store", UPSERT),
    "gmc_lfp_delete_store": ("Delete an LFP store", DESTRUCTIVE),
    "gmc_lfp_insert_inventory": ("Push an LFP inventory record", UPSERT),
    "gmc_lfp_insert_sale": ("Push an LFP sale", WRITE),
    "gmc_lfp_get_merchant_state": ("Get a merchant's LFP state", READ),
    # mca
    "gmc_list_relationships": ("List account relationships", READ),
    "gmc_get_relationship": ("Get an account relationship", READ),
    "gmc_update_relationship": ("Update an account relationship", UPSERT),
    "gmc_list_account_services": ("List account services", READ),
    "gmc_get_account_service": ("Get an account service", READ),
    "gmc_propose_account_service": ("Propose an account service", WRITE),
    "gmc_approve_account_service": ("Approve an account service", UPSERT),
    "gmc_reject_account_service": ("Reject or end an account service", DESTRUCTIVE),
    # bulk
    "gmc_bulk_update_regional_prices": ("Bulk-update regional prices", UPSERT),
    "gmc_bulk_set_availability": ("Bulk-set availability", UPSERT),
    # diagnostics
    "gmc_health_check": ("Check API health", READ),
    "gmc_rollback": ("Roll back a write", DESTRUCTIVE_ONCE),
    "gmc_export_all": ("Export account data to files", LOCAL_EXPORT),
    "gmc_diff_with_shopify": ("Compare products with a Shopify export", READ),
    # regions
    "gmc_list_regions": ("List regions", READ),
    "gmc_get_region": ("Get a region", READ),
    "gmc_create_region": ("Create a region", WRITE),
    "gmc_update_region": ("Update a region", UPSERT),
    "gmc_delete_region": ("Delete a region", DESTRUCTIVE),
    "gmc_batch_create_regions": ("Create regions in a batch", WRITE),
    "gmc_batch_update_regions": ("Update regions in a batch", UPSERT),
    "gmc_batch_delete_regions": ("Delete regions in a batch", DESTRUCTIVE),
    # issue resolution
    "gmc_render_account_issues": ("Explain account issues", READ),
    "gmc_render_product_issues": ("Explain a product's issues", READ),
    "gmc_trigger_issue_action": ("Trigger an issue action", WRITE),
    "gmc_list_review_options": ("List review options for issues", READ),
    "gmc_request_review": ("Request a review of a disapproval", WRITE),
    "gmc_disapprovals_overview": ("Show a disapprovals overview", READ),
    "gmc_list_aggregate_product_statuses": ("Count products by status", READ),
    # order tracking
    "gmc_create_order_tracking_signal": ("Create an order tracking signal", WRITE),
    # product studio
    "gmc_generate_product_text_suggestions": ("Suggest product titles and descriptions", GENERATE),
    "gmc_generate_product_image_background": ("Generate a product image background", GENERATE),
    "gmc_remove_product_image_background": ("Remove a product image background", GENERATE),
    "gmc_upscale_product_image": ("Upscale a product image", GENERATE),
}

TOOL_SPECS: dict[str, ToolSpec] = {
    name: ToolSpec(title, annotations) for name, (title, annotations) in _CATALOG.items()
}

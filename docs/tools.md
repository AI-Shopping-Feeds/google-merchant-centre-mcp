# All tools

**166 tools: 162 across 23 modules + 4 meta tools.**

Every Merchant API v1 resource method is covered (accounts, conversions,
datasources, inventories, issueresolution, lfp, notifications, ordertracking,
products, promotions, quota, reports, reviews). A few tools deliberately call a
pre-GA version because v1 has no equivalent; their descriptions start with the
version tag:

- `[v1beta]` `gmc_update_return_policy` (v1 has no `onlineReturnPolicies.patch`)
  and the four `*_merchant_review*` tools (merchant reviews are v1beta-only).
- `[ALPHA v1alpha]` the four **product_studio** tools (Product Studio has no
  v1/v1beta API; may need allowlisting).

| Module | Tools |
|---|---|
| **products** | `gmc_list_products`, `gmc_get_product`, `gmc_insert_product`, `gmc_update_product`, `gmc_patch_product`, `gmc_delete_product`, `gmc_bulk_delete_products`, `gmc_list_disapproved_products` |
| **inventory** | `gmc_update_regional_inventory`, `gmc_update_local_inventory`, `gmc_list_regional_inventories`, `gmc_list_local_inventories`, `gmc_delete_local_inventory`, `gmc_delete_regional_inventory` |
| **issues** | `gmc_list_account_issues`, `gmc_get_product_status`, `gmc_summarize_product_issues` |
| **issue_resolution** | `gmc_render_account_issues`, `gmc_render_product_issues`, `gmc_trigger_issue_action`, `gmc_list_review_options`, `gmc_request_review`, `gmc_disapprovals_overview`, `gmc_list_aggregate_product_statuses` |
| **reports** | `gmc_query_report`, `gmc_product_performance`, `gmc_price_competitiveness`, `gmc_best_sellers`, `gmc_zero_click_products`, `gmc_revenue_by_brand`, `gmc_category_performance`, `gmc_competitive_visibility_top_merchants`, `gmc_price_insights`, `gmc_demoted_products` |
| **promotions** | `gmc_list_promotions`, `gmc_get_promotion`, `gmc_insert_promotion` |
| **accounts** | `gmc_get_account`, `gmc_list_accounts`, `gmc_list_subaccounts`, `gmc_update_account`, `gmc_delete_account`, `gmc_create_and_configure_account`, `gmc_create_test_account`, `gmc_get_business_info`, `gmc_update_business_info`, `gmc_list_users`, `gmc_add_user`, `gmc_remove_user`, `gmc_get_user`, `gmc_update_user`, `gmc_verify_self`, `gmc_get_shipping_settings`, `gmc_update_shipping_settings`, `gmc_list_programs`, `gmc_get_program`, `gmc_enable_program`, `gmc_disable_program`, `gmc_get_developer_registration`, `gmc_register_gcp`, `gmc_unregister_gcp`, `gmc_get_account_for_gcp_registration` |
| **regions** | `gmc_list_regions`, `gmc_get_region`, `gmc_create_region`, `gmc_update_region`, `gmc_delete_region`, `gmc_batch_create_regions`, `gmc_batch_update_regions`, `gmc_batch_delete_regions` |
| **notifications** | `gmc_list_subscriptions`, `gmc_subscribe`, `gmc_unsubscribe`, `gmc_get_subscription`, `gmc_update_subscription` |
| **feeds** | `gmc_list_datasources`, `gmc_get_datasource`, `gmc_create_supplemental_feed`, `gmc_create_primary_feed`, `gmc_create_datasource`, `gmc_update_datasource`, `gmc_get_datasource_file_upload`, `gmc_delete_datasource`, `gmc_fetch_datasource` |
| **return_policies** | `gmc_list_return_policies`, `gmc_get_return_policy`, `gmc_create_return_policy`, `gmc_update_return_policy`, `gmc_delete_return_policy` |
| **homepage** | `gmc_get_homepage`, `gmc_update_homepage`, `gmc_claim_homepage`, `gmc_unclaim_homepage` |
| **account_config** | `gmc_get_business_identity`, `gmc_update_business_identity`, `gmc_get_checkout_settings`, `gmc_create_checkout_settings`, `gmc_update_checkout_settings`, `gmc_delete_checkout_settings`, `gmc_get_automatic_improvements`, `gmc_update_automatic_improvements`, `gmc_get_autofeed_settings`, `gmc_update_autofeed_settings`, `gmc_get_email_preferences`, `gmc_update_email_preferences`, `gmc_get_latest_tos`, `gmc_get_tos`, `gmc_get_tos_agreement_state`, `gmc_retrieve_tos_agreement_for_application`, `gmc_accept_tos` |
| **quotas** | `gmc_list_quotas`, `gmc_list_account_limits`, `gmc_get_account_limit` |
| **reviews** | `gmc_list_merchant_reviews`, `gmc_get_merchant_review`, `gmc_insert_merchant_review`, `gmc_delete_merchant_review`, `gmc_list_product_reviews`, `gmc_get_product_review`, `gmc_insert_product_review`, `gmc_delete_product_review` |
| **conversions** | `gmc_list_conversion_sources`, `gmc_get_conversion_source`, `gmc_create_conversion_source`, `gmc_update_conversion_source`, `gmc_delete_conversion_source`, `gmc_undelete_conversion_source` |
| **omnichannel** | `gmc_list_omnichannel_settings`, `gmc_get_omnichannel_settings`, `gmc_create_omnichannel_settings`, `gmc_update_omnichannel_settings`, `gmc_request_inventory_verification`, `gmc_find_lfp_providers`, `gmc_link_lfp_provider`, `gmc_link_gbp_account`, `gmc_list_gbp_accounts` |
| **lfp** | `gmc_lfp_list_stores`, `gmc_lfp_get_store`, `gmc_lfp_insert_store`, `gmc_lfp_delete_store`, `gmc_lfp_insert_inventory`, `gmc_lfp_insert_sale`, `gmc_lfp_get_merchant_state` |
| **mca** | `gmc_list_relationships`, `gmc_get_relationship`, `gmc_update_relationship`, `gmc_list_account_services`, `gmc_get_account_service`, `gmc_propose_account_service`, `gmc_approve_account_service`, `gmc_reject_account_service` |
| **order_tracking** | `gmc_create_order_tracking_signal` |
| **product_studio** | `gmc_generate_product_text_suggestions`, `gmc_generate_product_image_background`, `gmc_remove_product_image_background`, `gmc_upscale_product_image` |
| **bulk** | `gmc_bulk_update_regional_prices`, `gmc_bulk_set_availability` |
| **diagnostics** | `gmc_health_check`, `gmc_rollback`, `gmc_export_all`, `gmc_diff_with_shopify` |
| **meta** | `gmc_describe_server`, `gmc_audit_lookup`, `gmc_audit_tail`, `gmc_set_dry_run` |

CLI also exposes: `gmc-mcp run`, `auth-init`, `register-gcp`, `webhook`, `describe`, `version`.

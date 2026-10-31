# Changelog — Google Merchant Center MCP (`google-merchant-centre-mcp`)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — MCP SDK 2
- Requires `mcp>=2.3.0,<3` (was `<2`). The server is built on the SDK's
  `MCPServer` (the successor to `mcp.server.fastmcp.FastMCP`, which SDK 2
  removed). Tools, names and behaviour are unchanged. SSE host and port are now
  passed to `run()`.
- Tool errors such as a missing `confirm`, bad arguments, Merchant API errors
  and config problems are re-raised as `ToolError`, so clients still see their
  message. SDK 2 hides the text of other exceptions.

### Changed — published as this fork
- PyPI package renamed from `gmc-mcp` to **`google-merchant-centre-mcp`**, and the MCP
  Registry name from `io.github.kiwoongeom/gmc-mcp` to
  **`io.github.AI-Shopping-Feeds/google-merchant-centre-mcp`**. The `gmc-mcp`
  command and the `gmc_mcp` import package are unchanged.
- Project URLs, badges and `server.json` now point at
  https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp. The original
  author keeps their copyright line and author credit.
- Version 0.3.0.

Full coverage pass against the Merchant API v1 discovery documents. Tool count
goes from 126 to 166 (162 module tools across 23 modules + 4 meta tools).

### Added
- **Disapprovals overview**: `gmc_disapprovals_overview` returns disapproved
  products (by click potential) with each issue's code, attribute, severity,
  resolution and the destinations/countries affected, a top-reasons summary,
  and optionally each product's review options.
- **Disapproval review requests**: `gmc_list_review_options` and `gmc_request_review`.
  They wrap Issue Resolution
  `render*issues` (with `BUILT_IN_USER_INPUT_ACTIONS`) and `triggeraction`,
  returning only review/appeal actions with their availability, flows and
  questions, and building the `inputValues` payload from plain answers.
- **products**: `gmc_patch_product` (`productInputs.patch` with `updateMask`).
- **inventory**: `gmc_delete_local_inventory`, `gmc_delete_regional_inventory`.
- **accounts**: `gmc_list_accounts`, `gmc_list_subaccounts`, `gmc_update_account`,
  `gmc_delete_account` (requires `confirm='DELETE'`), `gmc_create_and_configure_account`,
  `gmc_create_test_account`, `gmc_get_user`, `gmc_update_user`, `gmc_verify_self`,
  `gmc_get_program`, `gmc_enable_program`, `gmc_disable_program`,
  `gmc_get_developer_registration`, `gmc_register_gcp`, `gmc_unregister_gcp`,
  `gmc_get_account_for_gcp_registration`.
- **account_config**: `gmc_get_tos`, `gmc_get_tos_agreement_state`,
  `gmc_retrieve_tos_agreement_for_application`.
- **feeds**: `gmc_create_datasource` (any data source type), `gmc_update_datasource`,
  `gmc_get_datasource_file_upload`.
- **regions**: `gmc_batch_create_regions`, `gmc_batch_update_regions`,
  `gmc_batch_delete_regions` (requires `confirm='DELETE'`).
- **notifications**: `gmc_get_subscription`, `gmc_update_subscription`.
- **omnichannel**: `gmc_find_lfp_providers`, `gmc_link_lfp_provider`.
- **mca**: `gmc_get_account_service`.
- **quotas**: `gmc_list_account_limits`, `gmc_get_account_limit`.
- New module **issue_resolution**: `gmc_render_account_issues`,
  `gmc_render_product_issues`, `gmc_trigger_issue_action`,
  `gmc_list_aggregate_product_statuses`.
- New module **order_tracking**: `gmc_create_order_tracking_signal`.
- New module **product_studio** (labelled `[ALPHA v1alpha]`; no v1 API exists):
  `gmc_generate_product_text_suggestions`, `gmc_generate_product_image_background`,
  `gmc_remove_product_image_background`, `gmc_upscale_product_image`.
- `MerchantClient.request(read_only=True)` for POST endpoints that don't mutate
  state, and `MerchantClient.snapshot()` for best-effort `before` captures.

### Fixed
- Reports `search` calls (and the health check) were treated as writes, so in
  dry-run mode they returned a fake payload instead of data. They are now read-only.
- `gmc_bulk_delete_products(filter_status=...)` ignored the filter and deleted
  every product. It now matches products via a `product_view` query, and rejects
  unknown status values.
- Terms of Service: `gmc_get_latest_tos` / `gmc_accept_tos` used a non-existent
  `termsOfService/v1/...` path; they now call `accounts/v1/termsOfService...` and
  `accept` sends the required `account` and `regionCode` parameters.
- Reviews: product reviews now use `reviews/v1/.../productReviews` (`:insert`);
  merchant reviews use `reviews/v1beta/...` (v1beta-only, labelled).
- MCA: relationships path is `relationships` (was `accountRelationships`); account
  services list key is `accountServices`; `gmc_propose_account_service` now sends
  a valid `accountService` body.
- `gmc_insert_promotion` sends `InsertPromotionRequest` (`promotion` + `dataSource`
  in the body) instead of a query parameter.
- `gmc_link_gbp_account` sends `gbpEmail` (was `gbpAccount`).
- `gmc_create_region` builds a valid `postalCodeArea` (`regionCode` + `begin`/`end`);
  new `postal_region_code` argument.
- `gmc_update_return_policy` now calls v1beta (v1 has no `patch`), labelled `[v1beta]`.
- `gmc_list_account_issues` accepts `time_zone`.
- Rollback can now restore `update_product` / `patch_product` writes.
- More writes capture a `before` snapshot (unsubscribe, unclaim homepage, delete
  checkout settings, reject service, program enable/disable).
- `mcp` dependency pinned to `<2` (mcp 2.x removed `mcp.server.fastmcp`, which
  broke import on a fresh install). `cli.py` missing `Any` import fixed. Ruff clean.

### Removed
- `gmc_get_account_tax`, `gmc_update_account_tax`: `accountTax` does not exist in
  Merchant API (v1, v1beta or v1alpha).
- `gmc_request_program_review`, `gmc_get_program_review`: no such endpoints in
  Merchant API; replaced by `gmc_get_program` / `gmc_enable_program` / `gmc_disable_program`.
- `gmc_create_aggregation`, `gmc_delete_aggregation`: no `accountAggregation`
  endpoints exist; aggregation is an account service
  (`gmc_propose_account_service(service_type='ACCOUNT_AGGREGATION')`).
- `gmc_list_tos_agreement_states`: there is no list method; use
  `gmc_get_tos_agreement_state` / `gmc_retrieve_tos_agreement_for_application`.

## [0.2.5] - 2026-05-02

### Changed — positioning corrected (second time)
After publication, discovered another prior-art self-hosted GMC MCP server:
[`archpeng/GMC-mcp-server`](https://github.com/archpeng/GMC-mcp-server),
created 2026-02-23 (10 weeks before this package). My original "first
open-source self-hosted" claim was inaccurate.

The correct, verifiable framing:
- Both `archpeng/GMC-mcp-server` and this package are self-hosted Python.
- `archpeng/GMC-mcp-server` is on **Content API v2.1** (deprecated, Google
  retires August 2026), **no LICENSE file** (default copyright = not OSS),
  **not on PyPI**, 34 tools, last updated 2026-02-24.
- `gmc-mcp` is on **Merchant API v1** (current/future-proof), **MIT-licensed**,
  **on PyPI** (`pip install gmc-mcp`), 126 tools, audit log + rollback +
  dry-run + CI to PyPI/Registry.

README, pyproject description, and server.json description rewritten to
remove the "first" overclaim and present a comparison table instead.

## [0.2.4] - 2026-05-02

### Fixed
- Removed `runtimeArguments` from `server.json` (was triggering MCP Registry
  semantic validation on the `default` field). The CLI invokes the `run`
  subcommand automatically when called with no arguments, so the runtime
  argument was redundant anyway.

## [0.2.3] - 2026-05-02

### Fixed
- `server.json` description shortened to ≤100 characters to satisfy the
  MCP Registry validation rule. v0.2.2 publish to the registry failed on
  this constraint; v0.2.3 retries with a compliant description.

## [0.2.2] - 2026-05-02

### Added
- Published to the official **MCP Registry** at
  [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io)
  under the namespace `io.github.kiwoongeom/gmc-mcp`. Discoverable from Claude
  Desktop's MCP Registry browser and any other MCP-Registry-aware client.
- New file `server.json` — MCP Registry manifest with package + transport +
  environment-variable schema.
- New CI workflow `.github/workflows/publish-mcp-registry.yml` — auto-publishes
  to the MCP Registry on every `v*` tag push, using GitHub OIDC (no tokens).
- README now contains a `mcp-name:` HTML comment as required for PyPI-package
  ownership verification by the MCP Registry.

## [0.2.1] - 2026-05-02

### Changed
- README, CHANGELOG, and PyPI description updated for accurate positioning:
  this is the first **free, open-source, self-hosted** MCP server for Google
  Merchant Center. All known prior alternatives (Adzviser, Catchr, Windsor.ai,
  Pipedream) are paid hosted SaaS; Google's MAPI Docs MCP is documentation-
  lookup only. Differentiators of this package:
  1. Free (MIT) vs paid SaaS
  2. Open source — auditable, forkable
  3. Self-hosted — credentials never leave your machine
  4. `pip install`-able (no third-party signup)
  5. 126 tools mapping the full Merchant API v1 surface

### Added (carried over from unreleased)
- `tools/regions.py`: regions CRUD (list / get / create / update / delete) —
  required to set up regional inventory targeting.
- `tools/accounts.py`: `gmc_update_business_info` (PATCH businessInfo —
  address, phone, customer service, KR business registration number).
- `tools/accounts.py`: `gmc_request_program_review` and `gmc_get_program_review`
  for re-requesting Shopping Ads / Free Listings approval after fixing issues.

## [0.2.0] - 2026-05-01

### Positioning
- **First open-source, self-hosted MCP server for Google Merchant Center.**
- Existing alternatives at the time of release (Adzviser, Catchr, Windsor.ai,
  Pipedream, Google's MAPI Docs MCP) are all commercial hosted SaaS or
  documentation-lookup helpers. This is the first one you can `pip install`,
  audit the source of, and run with your credentials staying local.

### Added — full Merchant API v1 surface
- `tools/return_policies.py`: list / get / create / update / delete `onlineReturnPolicies` (Google now requires a return policy in US/EU).
- `tools/homepage.py`: get / update / `claim` / `unclaim` the registered homepage.
- `tools/account_config.py`: business identity, checkout settings (per program),
  automatic improvements, autofeed settings, account tax, email preferences,
  Terms of Service (latest / agreement states / accept).
- `tools/quotas.py`: list per-method quota usage and limits.
- `tools/reviews.py`: merchant + product reviews CRUD.
- `tools/conversions.py`: conversion sources CRUD + undelete.
- `tools/omnichannel.py`: omnichannel settings, GBP account linkage,
  `requestInventoryVerification`.
- `tools/lfp.py`: full Local Feed Partnership API
  (lfpStores / lfpInventories / lfpSales / lfpMerchantStates).
- `tools/mca.py`: relationships, account aggregation, account services delegation
  (propose / approve / reject).
- `tools/bulk.py`: `gmc_bulk_update_regional_prices`,
  `gmc_bulk_set_availability` — both gated by `confirm='APPLY'`.
- `tools/diagnostics.py`: `gmc_health_check`, `gmc_rollback(audit_id)`,
  `gmc_export_all(output_dir)`, `gmc_diff_with_shopify(shopify_csv)`.
- `tools/products.py`: `gmc_bulk_delete_products` with `confirm='DELETE'` gate
  and automatic `dataSource` extraction (works on orphan products).
- `tools/reports.py`: 6 new canned queries — revenue by brand, category
  performance, competitive visibility, price insights, demoted products.
- CLI: `gmc-mcp webhook` — tiny HTTP receiver that decodes Pub/Sub push
  notifications from `gmc_subscribe`. Logs to JSONL with `--out`.

### Fixed
- `gmc_summarize_product_issues` now reads the v1 `itemIssues` schema
  (`type.code`, `type.canonicalAttribute`, `severity.aggregatedSeverity`,
  `resolution`) instead of the v1beta flat shape.
- `gmc_list_disapproved_products` now includes the required `id` field in the
  Reports SELECT (v1 requirement).
- `gmc_update_regional_inventory` / `gmc_update_local_inventory` build the
  `regionalInventoryAttributes` / `localInventoryAttributes` envelope required
  by v1 (v1beta flat fields are no longer accepted).

## [0.1.0] - 2026-04-30

### Added
- Initial release. Targets **Merchant API v1** (v1beta was shut down 2026-02-28).
- `gmc-mcp register-gcp` CLI: one-time link of GCP project to Merchant Center,
  required before any v1 call works.
- 42 MCP tools across 8 modules covering products, inventory, issues, reports,
  promotions, accounts, notifications, and data sources (feeds).
- Service-account authentication with auto-refresh.
- OAuth 2.0 user-credential authentication as an alternative.
- Append-only audit log for every write operation, with `gmc_audit_lookup`
  and `gmc_audit_tail` for inspection.
- Dry-run mode (`GMC_DRY_RUN=true` or `gmc_set_dry_run`) for safe testing.
- Both stdio and HTTP/SSE transports.
- CLI entrypoint `gmc-mcp` with `--transport`, `--host`, `--port`, `--env`.
- Reports API helpers: raw SQL queries, top performers, price competitiveness,
  best sellers, zero-click outliers.
- Issue summarization that aggregates problem codes across all products.

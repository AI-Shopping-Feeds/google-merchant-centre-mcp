# Safety, dry-run and disapprovals

## Audit log + rollback

Every write logs a JSONL entry to `GMC_AUDIT_LOG` (default: `./logs/audit.jsonl`). Each entry contains:

- `audit_id` — UUID for lookup
- `op`, `method`, `url`, `request_body`, `response_status`, `response_body`
- `before` — pre-write snapshot when the tool fetched it (used by `update_*` and `delete_*`)
- `dry_run` — whether the request was actually sent

Inspect from inside Claude:

```
> Show me my last 5 GMC writes.
[gmc_audit_tail(limit=5) → ...]

> Look up audit ID abc123.
[gmc_audit_lookup(audit_id="abc123") → ...]

> Roll back audit ID abc123, that update was wrong.
[gmc_rollback(audit_id="abc123", confirm="ROLLBACK") → ...]
```

## Dry-run

Two ways to enable:

```bash
GMC_DRY_RUN=true gmc-mcp run
```

```
> Set dry-run on and update the price of SKU1 to $19.99.
[gmc_set_dry_run(enabled=True) → ok]
[gmc_update_regional_inventory(...) → {"_dry_run": true, ...}]
```

Reads always go through; only writes are skipped. POST endpoints that don't
change anything (Reports `search`, Issue Resolution `render*`, Product Studio
generation) are treated as reads, so they also run in dry-run mode.

## Disapprovals: reasons and review requests

`gmc_disapprovals_overview` gives you everything in one call. It returns your
disapproved products, most valuable first (by click potential). Each product
shows:

- why it's disapproved: issue code, affected attribute, severity, whether the
  fix is yours to make, and where it's disapproved (destination and countries)
- its review options

A summary counts products per issue so the biggest problems stand out.

The Merchant API has no single "request review" endpoint. Google returns review
and appeal actions with each rendered issue, and you submit them with
`triggeraction`. These tools wrap that flow:

1. `gmc_disapprovals_overview` checks disapproved products in bulk, or
   `gmc_list_review_options(product_id=...)` checks one product (leave out
   `product_id` for account issues). Each issue shows its review actions,
   whether they're available now, why not if they aren't (e.g. a review is
   already pending), the flows to pick from ("I fixed it", "I disagree") and the
   questions to answer.
2. `gmc_request_review(action_context, flow_id, answers)` submits the request.
   It's audited and respects dry-run.

```
> Show me my disapproved products and why, and which ones I can request a review for.
[gmc_disapprovals_overview() → 40 products, top reason price_mismatch (18), 6 requestable now]

> I've fixed the price mismatch on SKU1, request a review.
[gmc_request_review(action_context="...", flow_id="...", answers={"...": true})]
```

Some issues allow only one review, and a failed review can block new requests
for several days, so only request a review once the issue is fixed or the
business disagrees with it. Actions marked `external` have to be done in
Merchant Center or the Help Center via the returned `url`.

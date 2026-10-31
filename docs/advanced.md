# Advanced

## Reports query examples

Paste into `gmc_query_report`:

```sql
-- Top 50 by clicks last 7 days
SELECT offer_id, title, clicks, impressions, ctr
FROM product_performance_view
WHERE date BETWEEN '2026-04-23' AND '2026-04-30'
ORDER BY clicks DESC LIMIT 50

-- Disapproved products with reason codes
SELECT id, offer_id, title, item_issues
FROM product_view
WHERE aggregated_reporting_context_status = 'NOT_ELIGIBLE_OR_DISAPPROVED'

-- You're priced higher than the benchmark
SELECT offer_id, title, price, benchmark_price
FROM price_competitiveness_product_view
WHERE price > benchmark_price LIMIT 100
```

## OAuth instead of a service account

For acting on behalf of an end user (e.g. multi-tenant SaaS):

```bash
# 1. In GCP, create OAuth client credentials (type: Desktop), download client_secret.json.
gmc-mcp auth-init --client-secrets ./client_secret.json
# follow the browser flow; a token JSON is saved to secrets/oauth-token.json.

# 2. Use it
export GMC_OAUTH_TOKEN=./secrets/oauth-token.json
gmc-mcp run
```

## Transports

```bash
gmc-mcp run                              # stdio (Claude Desktop default)
gmc-mcp run --transport sse --port 8000  # SSE / HTTP (remote, Docker, hosted)
```

Or via Docker:

```bash
docker build -t gmc-mcp .
docker run --rm -p 8000:8000 \
    -e GMC_ACCOUNT_ID=1234567890 \
    -v $PWD/secrets:/secrets \
    -e GMC_SERVICE_ACCOUNT_KEY=/secrets/service-account.json \
    gmc-mcp
```

## Architecture

```
Claude (any MCP client)
    │  JSON-RPC over stdio or SSE
    ▼
gmc-mcp server  ──►  audit.jsonl
    │
    │  HTTP + Bearer token
    ▼
merchantapi.googleapis.com  ──►  Google Merchant Center
```

- `auth.py` — `ServiceAccountAuth` and `OAuthUserAuth` share an `Auth` protocol.
- `client.py` — single `MerchantClient` with retries (5x w/ jitter), pagination helper, and write-audit hook.
- `tools/*.py` — each module exposes a `register(mcp, client)` that registers `@mcp.tool()` functions.
- `audit.py` — append-only JSONL, lookup by ID, supports `before` snapshots.
- `cli.py` — `gmc-mcp run | auth-init | register-gcp | webhook | describe | version`.

## Testing

```bash
pytest                       # 100% offline; uses respx to mock HTTP
pytest --cov=gmc_mcp         # with coverage
ruff check src tests
mypy src/gmc_mcp
```

## Roadmap

- v0.3: webhook handler scaffolding (auto-respond to `gmc_subscribe` callbacks)
- v0.3: native Merchant API v1 GA migration when Google releases it
- v0.4: BigQuery export of Reports queries
- v0.4: rule-based auto-fixers ("on disapproval, retry with corrected attribute")

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
gmc-mcp run                                          # stdio (default; local clients)
gmc-mcp run --transport streamable-http --port 8000  # Streamable HTTP at http://127.0.0.1:8000/mcp
gmc-mcp run --transport sse --port 8000              # HTTP+SSE (deprecated)
```

`GMC_TRANSPORT`, `GMC_HOST` and `GMC_PORT` set the same options from the
environment; the CLI flags win.

- **stdio** is what local clients (Claude Code, Claude Desktop, Cursor and so
  on) use. They start the server themselves.
- **streamable-http** is the MCP spec's HTTP transport. Point a client at
  `http://HOST:PORT/mcp`. Use it for a shared or containerised server.
- **sse** is the older HTTP+SSE transport, which the MCP spec deprecates. It
  still works, but logs a deprecation warning at startup. Move clients to
  `streamable-http`.

The server binds to `127.0.0.1` by default, and on localhost the SDK also
checks `Host` and `Origin` headers against DNS rebinding. The HTTP transports
have **no sign-in**: anyone who can reach the port can act on your Merchant
Center account with the server's credentials. Binding to any other host (such
as `0.0.0.0`) logs a warning. Only do it on a private network or behind an
authenticating proxy.

To narrow what a shared server exposes, combine it with `GMC_READ_ONLY=true`
and `GMC_TOOL_GROUPS`, for example
`GMC_TOOL_GROUPS=products,issues,issue_resolution,reports`.

Or via Docker (the image serves `streamable-http` on port 8000):

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
    │  JSON-RPC over stdio or Streamable HTTP
    ▼
gmc-mcp server  ──►  audit.jsonl
    │
    │  HTTP + Bearer token
    ▼
merchantapi.googleapis.com  ──►  Google Merchant Center
```

- `auth.py` — `ServiceAccountAuth` and `OAuthUserAuth` share an `Auth` protocol.
- `client.py` — single `MerchantClient` with retries (5x w/ jitter), pagination helper, and write-audit hook.
- `tools/*.py` — each module exposes a `register(mcp, client)` that registers `@mcp.tool()` functions. Each module is a tool group for `GMC_TOOL_GROUPS`.
- `tool_catalog.py` — the title and annotations (read-only, destructive, idempotent, open-world) of every tool, applied by name when it registers.
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

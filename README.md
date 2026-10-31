<!-- mcp-name: io.github.AI-Shopping-Feeds/google-merchant-centre-mcp -->

# Google Merchant Centre MCP Server (read + write)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/) [![Fork of kiwoongeom/gmc-mcp](https://img.shields.io/badge/fork%20of-kiwoongeom%2Fgmc--mcp-lightgrey.svg)](https://github.com/kiwoongeom/gmc-mcp)

An [MCP](https://modelcontextprotocol.io) server for
[Google Merchant Center](https://merchants.google.com), built on
[Merchant API v1](https://developers.google.com/merchant/api). Use it from Claude,
ChatGPT, Cursor, Codex or any MCP client to manage products, prices, inventory,
feeds, promotions, shipping and returns, find disapprovals and request reviews,
and report on Shopping performance.

This is a fork of [kiwoongeom/gmc-mcp](https://github.com/kiwoongeom/gmc-mcp), maintained by [AI Shopping Feeds](https://github.com/AI-Shopping-Feeds). Upstream covers most of Merchant API v1 with an audit log, rollback and dry-run. This fork adds:

- **every Merchant API v1 method** (128), including accounts, issue resolution, order tracking and Product Studio
- a one-call **disapprovals overview** with reasons, and guided **review requests**
- **fixes** for tools that called endpoints that don't exist, and a bulk delete that ignored its filter
- read-only Reports calls that work in **dry-run** mode

Part of the AI Shopping Feeds MCP family: [Google Ads](https://github.com/AI-Shopping-Feeds/google-ads-mcp) · **Google Merchant Centre** · [Google Analytics](https://github.com/AI-Shopping-Feeds/google-analytics-mcp) · [YouTube Studio](https://github.com/AI-Shopping-Feeds/youtube-studio-mcp).

## Let your agent set it up

Paste this into Claude Code, Codex, Cursor or any agent that can read web pages and edit files:

```text
Set up the Google Merchant Centre MCP server for me by following https://raw.githubusercontent.com/AI-Shopping-Feeds/google-merchant-centre-mcp/main/skills/gmc-mcp/SKILL.md
```

The agent checks whether it's already connected, installs the runner if you
agree, walks you through the service account and Merchant Center access, adds the server to your
client's config without touching your other servers, and checks it works by
calling `gmc_describe_server`.

The same file is an [Agent Skill](https://agentskills.io), so your agent can keep it as a guide to using the tools well. For Claude Code, copy the folder into your skills:

```bash
git clone --depth 1 https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp.git /tmp/google-merchant-centre-mcp
cp -r /tmp/google-merchant-centre-mcp/skills/gmc-mcp ~/.claude/skills/
```

Other agents that support skills load the same `skills/gmc-mcp` folder from their own skills directory.

## What it can do

166 tools, all prefixed `gmc_`. The full list is in [docs/tools.md](docs/tools.md).

### Read

| Area | Tools |
|---|---|
| Products | `list_products`, `get_product`, `list_disapproved_products`, `get_product_status` |
| Disapprovals | `disapprovals_overview` (reasons, top issues, review options), `list_review_options`, `summarize_product_issues`, `render_product_issues`, `render_account_issues` |
| Reports | `query_report` plus `product_performance`, `best_sellers`, `price_competitiveness`, `price_insights`, `zero_click_products`, `demoted_products` and more |
| Feeds and inventory | `list_datasources`, `get_datasource`, `list_regional_inventories`, `list_local_inventories` |
| Account | `get_account`, users, programs, shipping, business info, homepage, terms of service, regions, return policies, quotas |
| Server | `describe_server`, `health_check`, `audit_tail`, `audit_lookup`, `export_all`, `diff_with_shopify` |

### Write

| Area | Tools |
|---|---|
| Products | `insert_product`, `update_product`, `patch_product`, `delete_product`, `bulk_delete_products` |
| Prices and stock | `update_regional_inventory`, `update_local_inventory`, `bulk_update_regional_prices`, `bulk_set_availability` |
| Reviews of disapprovals | `request_review`, `trigger_issue_action` |
| Feeds | `create_primary_feed`, `create_supplemental_feed`, `create_datasource`, `update_datasource`, `fetch_datasource`, `delete_datasource` |
| Promotions and reviews | `insert_promotion`, merchant and product review tools |
| Account | shipping, business info and identity, users, programs, regions, return policies, checkout, conversion sources, omnichannel, local feeds partnership, linked accounts |
| Undo | `rollback`, using the audit log's before-snapshots |

### Safety

- Every write is recorded in an append-only audit log with a before-snapshot, and `gmc_rollback` can undo it.
- Dry-run (`GMC_DRY_RUN=true` or `gmc_set_dry_run`) logs writes without sending them. Reads and reports still work.
- Destructive bulk and account operations need an explicit `confirm` value, such as `DELETE`.
- Details: [docs/safety-and-disapprovals.md](docs/safety-and-disapprovals.md).

## Supported clients

| Client | Works? | How |
|---|---|---|
| Claude Code | ✅ | Local server, `claude mcp add` (below) |
| Claude Desktop | ✅ | Local server, `claude_desktop_config.json` |
| Cursor | ✅ | Local server, `~/.cursor/mcp.json` |
| VS Code (Copilot) | ✅ | Local server, `.vscode/mcp.json` (uses `servers` instead of `mcpServers`) |
| Codex | ✅ | Local server, `~/.codex/config.toml` |
| Gemini CLI | ✅ | Local server, `~/.gemini/settings.json` |
| Windsurf and other local clients | ✅ | Local server, same JSON entry |
| Claude.ai and ChatGPT | ❌ not yet | These need a remote server with sign-in. This server's HTTP mode (`--transport sse`) has no sign-in, so don't expose it publicly. Use a local client. |

## Setup

### 1. Install uv

The server runs with `uvx` from [uv](https://docs.astral.sh/uv/getting-started/installation/)
(`brew install uv` on macOS) and needs Python 3.10 or later. It installs straight
from this repository:

```shell
uvx --from git+https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp.git gmc-mcp run
```

The command it installs is `gmc-mcp`. It isn't on PyPI under this fork's name yet (the upstream `gmc-mcp` package doesn't have these changes). Pin a release by adding `@vX.Y.Z` to the URL.

### 2. Get credentials

1. **Google Cloud:** enable the **Merchant API**, create a service account and
   download its JSON key.
2. **Merchant Center:** in Settings → Account access → People, add the service
   account's email with **Admin** access. Note your Merchant Center ID (top right).
3. **Register the Cloud project once** (needed before any Merchant API v1 call):

   ```shell
   GMC_ACCOUNT_ID=1234567890 GMC_SERVICE_ACCOUNT_KEY=/abs/path/key.json \
     uvx --from git+https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp.git \
     gmc-mcp register-gcp --developer-email you@example.com
   ```

To act as a person instead of a service account, use OAuth: see
[docs/advanced.md](docs/advanced.md#oauth-instead-of-a-service-account).

### 3. Add it to your client

Replace the placeholders. Keep your other servers in each file.

**Claude Code**

```bash
claude mcp add --scope user gmc \
  --env GMC_ACCOUNT_ID=1234567890 \
  --env GMC_SERVICE_ACCOUNT_KEY=/abs/path/service-account.json \
  -- uvx --from git+https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp.git gmc-mcp run
```

**Claude Desktop, Cursor, Gemini CLI, Windsurf** (and VS Code under `servers`)

```json
{
  "mcpServers": {
    "gmc": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp.git", "gmc-mcp", "run"],
      "env": {
        "GMC_ACCOUNT_ID": "1234567890",
        "GMC_SERVICE_ACCOUNT_KEY": "/abs/path/service-account.json"
      }
    }
  }
}
```

Desktop apps often can't find `uvx` on the PATH; if the server doesn't start, use
the full path from `which uvx` as the `command`.

**Codex** (`~/.codex/config.toml`)

```toml
[mcp_servers.gmc]
command = "uvx"
args = ["--from", "git+https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp.git", "gmc-mcp", "run"]
env = { GMC_ACCOUNT_ID = "1234567890", GMC_SERVICE_ACCOUNT_KEY = "/abs/path/service-account.json" }
```

### 4. Check it works

Restart or reload the client, then ask it to "which Merchant Center account are you connected to?". It should
call `gmc_describe_server`.

## Configuration

| Variable | Required | What it does |
|---|---|---|
| `GMC_ACCOUNT_ID` | yes | Your 10-digit Merchant Center ID |
| `GMC_SERVICE_ACCOUNT_KEY` | one of | Path to a service-account JSON key |
| `GMC_OAUTH_TOKEN` | one of | Path to an OAuth token from `gmc-mcp auth-init` |
| `GMC_SUBACCOUNT_ID` | no | Sub-account ID when using an advanced (multi-client) account |
| `GMC_DRY_RUN` | no | `true` logs writes without sending them |
| `GMC_AUDIT_LOG` | no | Audit log path (default `./logs/audit.jsonl`) |
| `GMC_PAGE_SIZE` | no | Default list page size (default 100) |
| `GMC_TIMEOUT` | no | Per-request timeout in seconds (default 30) |
| `GMC_LOG_LEVEL` | no | `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `GMC_TRANSPORT`, `GMC_HOST`, `GMC_PORT` | no | `stdio` (default) or `sse`, and its bind address |

## Example prompts

```text
Show me my disapproved products and why, and which ones I can request a review for.
```

```text
Which products had impressions but no clicks last week?
```

```text
Raise UK prices by 5% on these 40 SKUs. Use dry-run first and show me the changes.
```

```text
Roll back my last change, it was wrong.
```

## More docs

- [All tools](docs/tools.md)
- [Safety, dry-run and disapprovals](docs/safety-and-disapprovals.md)
- [Advanced](docs/advanced.md): report query examples, OAuth, HTTP transport, architecture and testing
- [Agent skill](skills/gmc-mcp/SKILL.md): setup and usage guide for agents
- [Changelog](CHANGELOG.md)

## Contributing and licence

Issues and pull requests are welcome on [this repository](https://github.com/AI-Shopping-Feeds/google-merchant-centre-mcp). See
[CONTRIBUTING.md](CONTRIBUTING.md).

Licensed under the [MIT License](LICENSE). Based on [kiwoongeom/gmc-mcp](https://github.com/kiwoongeom/gmc-mcp) by eric.eom.

# GitCode MCP server

An MCP server that reads pull requests from [GitCode](https://gitcode.com) repositories through the
GitCode REST API v5 (`https://api.gitcode.com/api/v5`). It works for any `owner/repo` your token can see,
for example `Ascend/AscendNPU-IR-Dev` and `Ascend/AscendNPU-IR`.

## Tools

| Tool | Description |
| --- | --- |
| `list_pull_requests` | Lists PRs, following every page. Filters: `state` (`open`, `closed`, `merged`, `all`), `base`, `author`, `since`, `sort`, `direction`, `limit`, `include_body`. |
| `get_pull_request` | Full API object for one PR. |
| `list_pull_request_commits` | Commits in a PR. |
| `list_pull_request_files` | Files changed in a PR, with additions, deletions and patch. |

`repository` accepts `owner/repo` or a URL such as `https://gitcode.com/Ascend/AscendNPU-IR`.
With `state="merged"` the server also drops any PR that has no `merged_at`, so only merged PRs come back
even if the API returns closed-but-unmerged PRs.

## Authentication

1. In GitCode, open your avatar menu, then **Settings > Access Tokens**, and create a personal access token
   with read access to repositories / pull requests.
2. Provide it as `GITCODE_TOKEN` (`GITCODE_ACCESS_TOKEN` also works). The token is sent in the
   `Authorization: Bearer` header, never in the URL.

Optionally set `GITCODE_API_URL` to point at a different API base URL.

Do not commit the token. Put it in your MCP client config, your shell profile, or a git-ignored `.env`
(see [`.env.example`](.env.example)).

## Install and run

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
cd gitcode
uv sync
GITCODE_TOKEN=... uv run gitcode-mcp   # starts the server on stdio
```

### Claude Code

```bash
claude mcp add gitcode -e GITCODE_TOKEN=your-token -- uv --directory /path/to/mcp/gitcode run gitcode-mcp
```

### Claude Desktop and other clients

```json
{
  "mcpServers": {
    "gitcode": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp/gitcode", "run", "gitcode-mcp"],
      "env": { "GITCODE_TOKEN": "your-token" }
    }
  }
}
```

Then ask, for example: "List all merged pull requests in Ascend/AscendNPU-IR-Dev".

## Command-line export

The same code is available as a CLI, handy for dumping everything to a file:

```bash
export GITCODE_TOKEN=your-token
uv run gitcode-prs Ascend/AscendNPU-IR-Dev --state merged -o ascendnpu-ir-dev-merged.json
uv run gitcode-prs https://gitcode.com/Ascend/AscendNPU-IR --state all -o ascendnpu-ir-all.json
```

Options: `--state`, `--base`, `--limit`, `--include-body`, `--raw` (unmodified API objects), `-o FILE`.

## Tests

```bash
uv run pytest
```

The tests use a mocked GitCode API, so they need no token or network access.

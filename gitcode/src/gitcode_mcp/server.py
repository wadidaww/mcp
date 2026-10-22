"""MCP server exposing GitCode pull request data."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from .client import GitCodeClient, is_merged, parse_repository

mcp = MCPServer(
    name="gitcode",
    instructions=(
        "Read pull requests from GitCode (gitcode.com) repositories. Repositories are given as "
        "'owner/repo' or a gitcode.com URL, e.g. 'Ascend/AscendNPU-IR'. Authenticates with the "
        "GITCODE_TOKEN environment variable."
    ),
)

State = Literal["open", "closed", "merged", "all"]


def _login(user: Any) -> str | None:
    if isinstance(user, dict):
        return user.get("login") or user.get("username") or user.get("name")
    return None


def _ref(side: Any) -> str | None:
    if isinstance(side, dict):
        return side.get("ref") or side.get("label")
    return None


def summarize_pr(pr: dict[str, Any], include_body: bool = False) -> dict[str, Any]:
    summary = {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "merged": is_merged(pr),
        "author": _login(pr.get("user")),
        "source_branch": _ref(pr.get("head")),
        "target_branch": _ref(pr.get("base")),
        "created_at": pr.get("created_at"),
        "updated_at": pr.get("updated_at"),
        "merged_at": pr.get("merged_at"),
        "closed_at": pr.get("closed_at"),
        "labels": [l.get("name") for l in pr.get("labels") or [] if isinstance(l, dict)],
        "url": pr.get("html_url") or pr.get("url"),
    }
    if include_body:
        summary["body"] = pr.get("body")
    return summary


@mcp.tool()
async def list_pull_requests(
    repository: str,
    state: State = "all",
    base: str | None = None,
    author: str | None = None,
    since: str | None = None,
    sort: Literal["created", "updated"] | None = None,
    direction: Literal["asc", "desc"] | None = None,
    limit: int | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """List pull requests of a GitCode repository, following all pages.

    Args:
        repository: 'owner/repo' or a gitcode.com URL, e.g. 'Ascend/AscendNPU-IR-Dev'.
        state: 'open', 'closed', 'merged' or 'all'. Use 'merged' for merged PRs only.
        base: Only PRs targeting this branch.
        author: Only PRs opened by this GitCode username.
        since: Only PRs updated at or after this ISO 8601 time, e.g. '2026-01-01T00:00:00+08:00'.
        sort: Sort field, 'created' or 'updated'.
        direction: 'asc' or 'desc'.
        limit: Stop after this many PRs. Omit to fetch every matching PR.
        include_body: Include each PR's description text.
    """
    owner, repo = parse_repository(repository)
    async with GitCodeClient() as client:
        prs = await client.list_pull_requests(
            owner,
            repo,
            state=state,
            limit=limit,
            base=base,
            author=author,
            since=since,
            sort=sort,
            direction=direction,
        )
    return {
        "repository": f"{owner}/{repo}",
        "state": state,
        "count": len(prs),
        "pull_requests": [summarize_pr(pr, include_body) for pr in prs],
    }


@mcp.tool()
async def get_pull_request(repository: str, number: int) -> dict[str, Any]:
    """Get the full details of one pull request, as returned by the GitCode API.

    Args:
        repository: 'owner/repo' or a gitcode.com URL.
        number: The pull request number.
    """
    owner, repo = parse_repository(repository)
    async with GitCodeClient() as client:
        return await client.get_pull_request(owner, repo, number)


@mcp.tool()
async def list_pull_request_commits(repository: str, number: int) -> dict[str, Any]:
    """List the commits of a pull request.

    Args:
        repository: 'owner/repo' or a gitcode.com URL.
        number: The pull request number.
    """
    owner, repo = parse_repository(repository)
    async with GitCodeClient() as client:
        commits = await client.list_pull_request_commits(owner, repo, number)
    return {
        "count": len(commits),
        "commits": [
            {
                "sha": c.get("sha"),
                "message": (c.get("commit") or {}).get("message"),
                "author": (((c.get("commit") or {}).get("author")) or {}).get("name"),
                "date": (((c.get("commit") or {}).get("author")) or {}).get("date"),
            }
            for c in commits
        ],
    }


@mcp.tool()
async def list_pull_request_files(repository: str, number: int) -> dict[str, Any]:
    """List the files changed by a pull request, with per-file additions/deletions and patch.

    Args:
        repository: 'owner/repo' or a gitcode.com URL.
        number: The pull request number.
    """
    owner, repo = parse_repository(repository)
    async with GitCodeClient() as client:
        files = await client.list_pull_request_files(owner, repo, number)
    return {"count": len(files), "files": files}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

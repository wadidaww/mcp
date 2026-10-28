"""Minimal async client for the GitCode REST API (v5)."""

from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

DEFAULT_API_URL = "https://api.gitcode.com/api/v5"
TOKEN_ENV_VARS = ("GITCODE_TOKEN", "GITCODE_ACCESS_TOKEN")
MAX_PER_PAGE = 100
PR_STATES = ("open", "closed", "merged", "all")

_REPO_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?gitcode\.(?:com|net)/(?P<owner>[^/\s]+)/(?P<repo>[^/\s?#]+)"
)
_REPO_SLUG_RE = re.compile(r"^(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)$")


class GitCodeError(ToolError):
    """Raised when the GitCode API returns an error or is misconfigured.

    Subclassing ToolError lets the MCP server pass the message through to the model.
    """


def parse_repository(repository: str) -> tuple[str, str]:
    """Accept ``owner/repo`` or a gitcode.com URL and return ``(owner, repo)``."""
    value = repository.strip().rstrip("/")
    match = _REPO_URL_RE.match(value) or _REPO_SLUG_RE.match(value)
    if not match:
        raise GitCodeError(
            f"Cannot parse repository {repository!r}; use 'owner/repo' or "
            "'https://gitcode.com/owner/repo'."
        )
    repo = match["repo"]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    return match["owner"], repo


def token_from_env() -> str | None:
    for name in TOKEN_ENV_VARS:
        if value := os.environ.get(name, "").strip():
            return value
    return None


def is_merged(pr: dict[str, Any]) -> bool:
    return bool(pr.get("merged_at")) or pr.get("state") == "merged"


class GitCodeClient:
    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.token = token if token is not None else token_from_env()
        self.base_url = (base_url or os.environ.get("GITCODE_API_URL") or DEFAULT_API_URL).rstrip("/")
        headers = {"Accept": "application/json", "User-Agent": "gitcode-mcp"}
        if self.token:
            # Header auth keeps the token out of URLs and therefore out of logs.
            headers["Authorization"] = f"Bearer {self.token}"
        self._http = httpx.AsyncClient(
            base_url=self.base_url, headers=headers, timeout=timeout, transport=transport
        )

    async def __aenter__(self) -> GitCodeClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            response = await self._http.get(path, params=clean)
        except httpx.HTTPError as exc:
            raise GitCodeError(f"Request to GitCode failed: {exc}") from exc
        if response.status_code >= 400:
            raise GitCodeError(self._describe_error(response))
        return response.json()

    def _describe_error(self, response: httpx.Response) -> str:
        try:
            detail = response.json().get("message") or response.text
        except ValueError:
            detail = response.text
        msg = f"GitCode API {response.status_code} for {response.request.url.path}: {detail}"
        if response.status_code in (401, 403) and not self.token:
            msg += f" (no token set; export one of {', '.join(TOKEN_ENV_VARS)})"
        elif response.status_code == 404:
            msg += " (repository or PR not found, or the token has no access to it)"
        return msg

    async def paginate(
        self, path: str, params: dict[str, Any] | None = None, per_page: int = MAX_PER_PAGE
    ) -> AsyncIterator[dict[str, Any]]:
        per_page = max(1, min(per_page, MAX_PER_PAGE))
        page = 1
        previous: list[Any] | None = None
        while True:
            items = await self.get(path, {**(params or {}), "page": page, "per_page": per_page})
            if not isinstance(items, list):
                raise GitCodeError(f"Expected a list from {path}, got {type(items).__name__}")
            # Guard against endpoints that ignore `page` and keep returning the same items.
            if items and items == previous:
                return
            for item in items:
                yield item
            if len(items) < per_page:
                return
            previous = items
            page += 1

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        limit: int | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        if state not in PR_STATES:
            raise GitCodeError(f"state must be one of {PR_STATES}, got {state!r}")
        path = f"/repos/{owner}/{repo}/pulls"
        results: list[dict[str, Any]] = []
        async for pr in self.paginate(path, {"state": state, **filters}):
            # Filter client-side as well, in case the server treats "merged" loosely
            # (e.g. returns all closed PRs).
            if state == "merged" and not is_merged(pr):
                continue
            results.append(pr)
            if limit is not None and len(results) >= limit:
                break
        return results

    async def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        return await self.get(f"/repos/{owner}/{repo}/pulls/{number}")

    async def list_pull_request_commits(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        return [c async for c in self.paginate(f"/repos/{owner}/{repo}/pulls/{number}/commits")]

    async def list_pull_request_files(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        return [f async for f in self.paginate(f"/repos/{owner}/{repo}/pulls/{number}/files")]

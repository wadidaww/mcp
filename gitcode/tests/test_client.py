import httpx
import pytest

from gitcode_mcp import server
from gitcode_mcp.client import GitCodeClient, GitCodeError, parse_repository


def make_prs(start: int, count: int, state: str = "merged") -> list[dict]:
    return [
        {
            "number": n,
            "title": f"PR {n}",
            "state": state,
            "merged_at": "2026-01-01T00:00:00+08:00" if state == "merged" else None,
            "user": {"login": "alice"},
            "head": {"ref": f"feature-{n}"},
            "base": {"ref": "master"},
            "labels": [{"name": "lgtm"}],
            "html_url": f"https://gitcode.com/Ascend/AscendNPU-IR/pulls/{n}",
        }
        for n in range(start, start + count)
    ]


class FakeGitCode:
    """Serves 250 PRs: 230 merged, 20 closed-unmerged, 100 per page."""

    def __init__(self, ignore_merged_filter: bool = False):
        self.prs = make_prs(1, 230) + make_prs(231, 20, state="closed")
        self.ignore_merged_filter = ignore_merged_filter
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.headers.get("Authorization") != "Bearer secret":
            return httpx.Response(401, json={"message": "401 Unauthorized"})
        if request.url.path != "/api/v5/repos/Ascend/AscendNPU-IR/pulls":
            return httpx.Response(404, json={"message": "Not Found"})
        state = request.url.params["state"]
        page = int(request.url.params["page"])
        per_page = int(request.url.params["per_page"])
        prs = self.prs
        if state == "merged" and not self.ignore_merged_filter:
            prs = [p for p in prs if p["state"] == "merged"]
        return httpx.Response(200, json=prs[(page - 1) * per_page : page * per_page])


def client_for(fake: FakeGitCode, token: str | None = "secret") -> GitCodeClient:
    return GitCodeClient(
        token=token, base_url="https://api.gitcode.com/api/v5", transport=httpx.MockTransport(fake)
    )


@pytest.mark.parametrize(
    "value",
    [
        "Ascend/AscendNPU-IR",
        "https://gitcode.com/Ascend/AscendNPU-IR",
        "https://gitcode.com/Ascend/AscendNPU-IR/pulls?state=merged",
        "gitcode.com/Ascend/AscendNPU-IR.git",
    ],
)
def test_parse_repository(value):
    assert parse_repository(value) == ("Ascend", "AscendNPU-IR")


def test_parse_repository_rejects_garbage():
    with pytest.raises(GitCodeError):
        parse_repository("not a repo")


async def test_lists_all_pages_of_merged_prs():
    fake = FakeGitCode()
    async with client_for(fake) as client:
        prs = await client.list_pull_requests("Ascend", "AscendNPU-IR", state="merged")
    assert [p["number"] for p in prs] == list(range(1, 231))
    assert [r.url.params["page"] for r in fake.requests] == ["1", "2", "3"]
    assert all("access_token" not in str(r.url) for r in fake.requests)


async def test_merged_filter_applied_client_side_when_server_ignores_it():
    fake = FakeGitCode(ignore_merged_filter=True)
    async with client_for(fake) as client:
        prs = await client.list_pull_requests("Ascend", "AscendNPU-IR", state="merged")
    assert len(prs) == 230


async def test_limit_and_all_state():
    async with client_for(FakeGitCode()) as client:
        assert len(await client.list_pull_requests("Ascend", "AscendNPU-IR", state="all")) == 250
        assert len(await client.list_pull_requests("Ascend", "AscendNPU-IR", limit=5)) == 5


async def test_unauthorized_error_mentions_env_var():
    async with client_for(FakeGitCode(), token="") as client:
        with pytest.raises(GitCodeError, match="GITCODE_TOKEN"):
            await client.list_pull_requests("Ascend", "AscendNPU-IR")


async def test_paginate_stops_when_server_ignores_page():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[{"sha": str(i)} for i in range(100)])

    async with GitCodeClient(token="t", transport=httpx.MockTransport(handler)) as client:
        items = await client.list_pull_request_commits("o", "r", 1)
    assert len(items) == 100 and len(calls) == 2


async def test_list_pull_requests_tool(monkeypatch):
    fake = FakeGitCode()
    monkeypatch.setattr(server, "GitCodeClient", lambda: client_for(fake))
    result = await server.list_pull_requests("https://gitcode.com/Ascend/AscendNPU-IR", state="merged")
    assert result["repository"] == "Ascend/AscendNPU-IR"
    assert result["count"] == 230
    first = result["pull_requests"][0]
    assert first == {
        "number": 1,
        "title": "PR 1",
        "state": "merged",
        "merged": True,
        "author": "alice",
        "source_branch": "feature-1",
        "target_branch": "master",
        "created_at": None,
        "updated_at": None,
        "merged_at": "2026-01-01T00:00:00+08:00",
        "closed_at": None,
        "labels": ["lgtm"],
        "url": "https://gitcode.com/Ascend/AscendNPU-IR/pulls/1",
    }

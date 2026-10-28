"""Command-line export of GitCode pull requests, sharing the MCP server's code path."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .client import PR_STATES, GitCodeClient, GitCodeError, parse_repository
from .server import summarize_pr


async def _run(args: argparse.Namespace) -> list[dict]:
    owner, repo = parse_repository(args.repository)
    async with GitCodeClient() as client:
        prs = await client.list_pull_requests(
            owner, repo, state=args.state, limit=args.limit, base=args.base
        )
    return prs if args.raw else [summarize_pr(pr, args.include_body) for pr in prs]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gitcode-prs", description="Export pull requests of a GitCode repository as JSON."
    )
    parser.add_argument("repository", help="'owner/repo' or https://gitcode.com/owner/repo")
    parser.add_argument("--state", choices=PR_STATES, default="all")
    parser.add_argument("--base", help="Only PRs targeting this branch")
    parser.add_argument("--limit", type=int, help="Maximum number of PRs")
    parser.add_argument("--include-body", action="store_true", help="Include PR descriptions")
    parser.add_argument("--raw", action="store_true", help="Output the API objects unchanged")
    parser.add_argument("-o", "--output", help="Write to this file instead of stdout")
    args = parser.parse_args(argv)

    try:
        data = asyncio.run(_run(args))
    except GitCodeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"Wrote {len(data)} pull requests to {args.output}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

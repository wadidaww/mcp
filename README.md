# MCP servers

A collection of [Model Context Protocol](https://modelcontextprotocol.io) servers for working with AI assistants.
Each server lives in its own directory with its own README, dependencies and tests.

| Server | What it does |
| --- | --- |
| [`gitcode/`](gitcode/) | Read pull requests (open, closed, merged or all) from any GitCode repository. |

## Claude agent config

[`claude/`](claude/) holds skills, rules and hooks for Claude agents. Tag a Claude Code prompt with
`[INTO-SKILL]` and Claude opens a PR here capturing what it learned in that session; see
[`claude/hooks/into-skill/`](claude/hooks/into-skill/) for setup.

## Secrets

Servers read credentials from environment variables. Never commit tokens: `.env` files are git-ignored,
and each server ships a `.env.example` that lists the variables it needs.

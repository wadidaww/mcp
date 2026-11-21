#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook for the [INTO-SKILL] tag.

When a prompt contains ``[INTO-SKILL]``, this hook adds instructions to the
turn that tell Claude to turn the lesson from the current session into an
improvement (a skill, a rule, a hook...) in the agent-config repository, on a
new branch, and to open a pull request for review.

Prompts without the tag pass through untouched (the hook prints nothing).

Configuration comes from environment variables, all optional:

  INTO_SKILL_REPO        GitHub repo that receives the PRs   (default: wadidaww/mcp)
  INTO_SKILL_CLONE       Local clone used for the edits      (default: the current project if it
                         is a checkout of INTO_SKILL_REPO, else ~/.claude/into-skill/repo)
  INTO_SKILL_BASE        Branch PRs are opened against       (default: main)
  INTO_SKILL_ROOT        Folder in that repo holding config  (default: claude)
  INTO_SKILL_TEMPLATE    Path to a custom instructions file  (default: instructions.md next to this script)

The hook only uses the Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

TAG_RE = re.compile(r"\[\s*into[-_ ]?skill\s*\]", re.IGNORECASE)

DEFAULTS = {
    "INTO_SKILL_REPO": "wadidaww/mcp",
    "INTO_SKILL_CLONE": "~/.claude/into-skill/repo",
    "INTO_SKILL_BASE": "main",
    "INTO_SKILL_ROOT": "claude",
}


def has_tag(prompt: str) -> bool:
    return bool(TAG_RE.search(prompt or ""))


def strip_tag(prompt: str) -> str:
    return TAG_RE.sub("", prompt or "").strip()


def remote_matches(url: str, repo: str) -> bool:
    """True if a git remote URL points at owner/name on any host or proxy."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.lower().endswith(("/" + repo.lower(), ":" + repo.lower()))


def git_origin(path: str) -> str | None:
    try:
        res = subprocess.run(
            ["git", "-C", path, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def project_dir(payload: dict, env: dict[str, str]) -> str:
    return env.get("CLAUDE_PROJECT_DIR") or str(payload.get("cwd") or os.getcwd())


def load_config(env: dict[str, str], payload: dict | None = None, origin=git_origin) -> dict[str, str]:
    cfg = {key: (env.get(key) or default) for key, default in DEFAULTS.items()}
    cfg["IN_PROJECT"] = ""
    if not env.get("INTO_SKILL_CLONE"):
        # In Claude Code on the web there is no lasting ~/.claude, so when the session is
        # already a checkout of the target repo, work there (in a git worktree).
        proj = project_dir(payload or {}, env)
        url = origin(proj)
        if url and remote_matches(url, cfg["INTO_SKILL_REPO"]):
            cfg["INTO_SKILL_CLONE"] = proj
            cfg["IN_PROJECT"] = "yes"
    cfg["INTO_SKILL_CLONE"] = os.path.expanduser(cfg["INTO_SKILL_CLONE"])
    return cfg


def prerequisite_warnings(which=shutil.which) -> list[str]:
    warnings = []
    if which("git") is None:
        warnings.append(
            "`git` was not found on PATH. Draft the change, tell the user git must be "
            "installed before the PR can be opened, and stop."
        )
    if which("gh") is None:
        warnings.append(
            "`gh` was not found on PATH. Push with git and open the PR with a GitHub tool "
            "if you have one (for example the GitHub MCP tools in Claude Code on the web). "
            "If you have neither, push the branch and give the user its compare URL."
        )
    return warnings


SEPARATE_CLONE = """```bash
# Clone once if missing
[ -d "{clone}/.git" ] || gh repo clone {repo} "{clone}"
cd "{clone}"
git status --porcelain          # must be clean; if not, stop and tell the user
git fetch origin {base}
git switch -c into-skill/<short-slug>-{today} origin/{base}
```"""

IN_PROJECT_WORKTREE = """The current project is itself a checkout of {repo}. Leave its working tree and branch
alone and use a separate git worktree:

```bash
cd "{clone}"
git fetch origin {base}
WT="${{TMPDIR:-/tmp}}/into-skill-<short-slug>"
git worktree add "$WT" -b into-skill/<short-slug>-{today} origin/{base}
cd "$WT"
```

When the PR is open, remove it with `git -C "{clone}" worktree remove "$WT"`."""


def render(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def build_context(payload: dict, env: dict[str, str], template: str, which=shutil.which) -> str | None:
    prompt = payload.get("prompt", "")
    if not has_tag(prompt):
        return None

    cfg = load_config(env, payload)
    note = strip_tag(prompt) or "(no note: infer the lesson from the session so far)"
    warnings = prerequisite_warnings(which)

    fmt = {
        "clone": cfg["INTO_SKILL_CLONE"],
        "repo": cfg["INTO_SKILL_REPO"],
        "base": cfg["INTO_SKILL_BASE"],
        "today": date.today().isoformat(),
    }
    setup = (IN_PROJECT_WORKTREE if cfg["IN_PROJECT"] else SEPARATE_CLONE).format(**fmt)

    values = {
        "BRANCH_SETUP": setup,
        "REPO": cfg["INTO_SKILL_REPO"],
        "CLONE": cfg["INTO_SKILL_CLONE"],
        "BASE": cfg["INTO_SKILL_BASE"],
        "ROOT": cfg["INTO_SKILL_ROOT"].strip("/"),
        "NOTE": note,
        "TODAY": date.today().isoformat(),
        "SESSION_ID": str(payload.get("session_id", "unknown")),
        "TRANSCRIPT": str(payload.get("transcript_path", "unknown")),
        "CWD": str(payload.get("cwd", os.getcwd())),
        "WARNINGS": "\n".join(f"- {w}" for w in warnings) if warnings else "- none",
    }
    return render(template, values)


def read_template(env: dict[str, str]) -> str:
    custom = env.get("INTO_SKILL_TEMPLATE")
    path = Path(os.path.expanduser(custom)) if custom else Path(__file__).with_name("instructions.md")
    return path.read_text(encoding="utf-8")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # Never block a prompt because of a malformed payload.

    if not has_tag(payload.get("prompt", "")):
        return 0

    env = dict(os.environ)
    try:
        template = read_template(env)
    except OSError as exc:
        print(f"[INTO-SKILL] hook could not read its instructions template: {exc}", file=sys.stderr)
        return 0

    context = build_context(payload, env, template)
    if context:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

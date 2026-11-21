#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook for the [INTO-SKILL] tag.

When a prompt contains ``[INTO-SKILL]``, this hook adds instructions to the
turn that tell Claude to turn the lesson from the current session into an
improvement (a skill, a rule, a hook...) in the agent-config repository, on a
new branch, and to open a pull request for review.

Prompts without the tag pass through untouched (the hook prints nothing).

Configuration comes from environment variables, all optional:

  INTO_SKILL_REPO        GitHub repo that receives the PRs   (default: wadidaww/mcp)
  INTO_SKILL_CLONE       Local clone used for the edits      (default: ~/.claude/into-skill/repo)
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


def load_config(env: dict[str, str]) -> dict[str, str]:
    cfg = {key: (env.get(key) or default) for key, default in DEFAULTS.items()}
    cfg["INTO_SKILL_CLONE"] = os.path.expanduser(cfg["INTO_SKILL_CLONE"])
    return cfg


def prerequisite_warnings(which=shutil.which) -> list[str]:
    warnings = []
    for tool in ("git", "gh"):
        if which(tool) is None:
            warnings.append(
                f"`{tool}` was not found on PATH. Tell the user it must be installed "
                "before the PR can be opened, and stop after drafting the change."
            )
    return warnings


def render(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def build_context(payload: dict, env: dict[str, str], template: str, which=shutil.which) -> str | None:
    prompt = payload.get("prompt", "")
    if not has_tag(prompt):
        return None

    cfg = load_config(env)
    note = strip_tag(prompt) or "(no note: infer the lesson from the session so far)"
    warnings = prerequisite_warnings(which)

    values = {
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

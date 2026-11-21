#!/usr/bin/env python3
"""Install the [INTO-SKILL] hook into a Claude Code config directory (default ~/.claude).

What it does, all idempotent:
  1. Copies into_skill.py and instructions.md to <claude-dir>/hooks/into-skill/.
  2. Adds the UserPromptSubmit hook entry to <claude-dir>/settings.json (keeps everything else).
  3. With --clone, clones the target repo to the local clone path if it is not there yet.
  4. With --link, symlinks every skill in <clone>/claude/skills/ into <claude-dir>/skills/
     and every rule in <clone>/claude/rules/ into <claude-dir>/rules/, so merged PRs take
     effect after a `git pull` in the clone.

Usage:
  python3 install.py [--claude-dir ~/.claude] [--clone] [--link]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK_FILES = ("into_skill.py", "instructions.md")
MARKER = "hooks/into-skill/into_skill.py"


def hook_command(claude_dir: Path) -> str:
    return f'python3 "{claude_dir / "hooks" / "into-skill" / "into_skill.py"}"'


def copy_hook(claude_dir: Path) -> Path:
    dest = claude_dir / "hooks" / "into-skill"
    dest.mkdir(parents=True, exist_ok=True)
    for name in HOOK_FILES:
        shutil.copy2(HERE / name, dest / name)
    (dest / "into_skill.py").chmod(0o755)
    return dest


def merge_settings(settings: dict, command: str) -> tuple[dict, bool]:
    """Return (settings, changed). Adds the hook once; replaces an older into-skill entry."""
    hooks = settings.setdefault("hooks", {})
    groups = hooks.setdefault("UserPromptSubmit", [])
    for group in groups:
        for hook in group.get("hooks", []):
            if MARKER in hook.get("command", ""):
                if hook["command"] == command:
                    return settings, False
                hook["command"] = command
                return settings, True
    groups.append({"hooks": [{"type": "command", "command": command, "timeout": 10}]})
    return settings, True


def update_settings(claude_dir: Path) -> bool:
    path = claude_dir / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    settings, changed = merge_settings(settings, hook_command(claude_dir))
    if changed:
        if path.exists():
            shutil.copy2(path, path.with_suffix(".json.bak"))
        path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return changed


def clone_repo(repo: str, clone: Path) -> None:
    if (clone / ".git").exists():
        print(f"clone already present: {clone}")
        return
    clone.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("gh"):
        cmd = ["gh", "repo", "clone", repo, str(clone)]
    else:
        cmd = ["git", "clone", f"https://github.com/{repo}.git", str(clone)]
    subprocess.run(cmd, check=True)


def link_dir_entries(src_dir: Path, dest_dir: Path, want) -> list[str]:
    linked = []
    if not src_dir.is_dir():
        return linked
    dest_dir.mkdir(parents=True, exist_ok=True)
    for entry in sorted(src_dir.iterdir()):
        if not want(entry):
            continue
        target = dest_dir / entry.name
        if target.is_symlink() and Path(os.readlink(target)) == entry:
            continue
        if target.exists() or target.is_symlink():
            print(f"skip {target}: already exists and is not our link")
            continue
        target.symlink_to(entry)
        linked.append(entry.name)
    return linked


def link_config(clone: Path, root: str, claude_dir: Path) -> None:
    base = clone / root
    skills = link_dir_entries(
        base / "skills", claude_dir / "skills", lambda p: p.is_dir() and (p / "SKILL.md").exists()
    )
    rules = link_dir_entries(
        base / "rules", claude_dir / "rules", lambda p: p.suffix == ".md" and p.name != "README.md"
    )
    print(f"linked skills: {skills or 'none new'}")
    print(f"linked rules:  {rules or 'none new'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude-dir", default="~/.claude", help="Claude Code config dir (default ~/.claude)")
    parser.add_argument("--clone", action="store_true", help="clone the target repo if missing")
    parser.add_argument("--link", action="store_true", help="symlink skills and rules from the clone")
    args = parser.parse_args(argv)

    claude_dir = Path(os.path.expanduser(args.claude_dir)).resolve()
    repo = os.environ.get("INTO_SKILL_REPO", "wadidaww/mcp")
    clone = Path(os.path.expanduser(os.environ.get("INTO_SKILL_CLONE", "~/.claude/into-skill/repo")))
    root = os.environ.get("INTO_SKILL_ROOT", "claude").strip("/")

    dest = copy_hook(claude_dir)
    print(f"hook installed: {dest}")
    print("settings.json: " + ("updated" if update_settings(claude_dir) else "already configured"))

    if args.clone:
        clone_repo(repo, clone)
    if args.link:
        if not (clone / ".git").exists():
            print(f"cannot link: no clone at {clone} (run with --clone)", file=sys.stderr)
            return 1
        link_config(clone, root, claude_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# `[INTO-SKILL]` hook

Put `[INTO-SKILL]` anywhere in a Claude Code prompt and Claude turns the lesson from that
session into a pull request against this repository: a new or edited skill, a standing rule,
or a hook. You review and merge it; nothing lands without you.

```text
> [INTO-SKILL] when a uv project has no lockfile, run `uv lock` before `uv sync`
```

Claude then works out the lesson, picks the right kind of change, writes it in a separate
clone on a new `into-skill/<slug>-<date>` branch, opens a PR titled `[INTO-SKILL] ...`, and
replies with the link. A bare `[INTO-SKILL]` with no note works too: Claude infers the lesson
from the session.

## How it works

`into_skill.py` is a [`UserPromptSubmit` hook](https://code.claude.com/docs/en/hooks). It reads
the prompt from stdin, and only when the tag is present it returns `additionalContext` built
from `instructions.md`. Prompts without the tag pass through with no output, and a malformed
payload never blocks a prompt. The tag is matched case-insensitively, so `[into-skill]`,
`[INTO_SKILL]` and `[into skill]` all work.

The hook itself makes no git or network calls. Claude does the work with `git` and `gh`
in the turn, so you see every command.

## Install

Requirements: Python 3.9+, `git`, and the [GitHub CLI](https://cli.github.com) signed in
(`gh auth login`) with push access to the target repo.

```bash
git clone https://github.com/wadidaww/mcp.git /tmp/mcp
python3 /tmp/mcp/claude/hooks/into-skill/install.py --clone --link
```

That:

1. copies the hook to `~/.claude/hooks/into-skill/`,
2. adds it to `~/.claude/settings.json` (other settings are kept, a `.bak` copy is written),
3. `--clone` clones the repo to `~/.claude/into-skill/repo`, the clone Claude edits for PRs,
4. `--link` symlinks each skill in `claude/skills/` into `~/.claude/skills/` and each rule in
   `claude/rules/` into `~/.claude/rules/`.

Re-running is safe. After you merge an `[INTO-SKILL]` PR, pull and re-link to pick it up:

```bash
git -C ~/.claude/into-skill/repo pull
python3 ~/.claude/into-skill/repo/claude/hooks/into-skill/install.py --link
```

Edits to existing skills and rules apply with just the `git pull`, since they are symlinks.

### Manual install

Copy `into_skill.py` and `instructions.md` to `~/.claude/hooks/into-skill/` and merge
[`settings.example.json`](settings.example.json) into `~/.claude/settings.json`. Use
`.claude/settings.json` in a project instead to enable it for that project only.

## Configuration

Set these in your shell or in the `env` block of `settings.json`. All are optional.

| Variable | Default | Meaning |
| --- | --- | --- |
| `INTO_SKILL_REPO` | `wadidaww/mcp` | GitHub repo that receives the PRs |
| `INTO_SKILL_CLONE` | `~/.claude/into-skill/repo` | Local clone Claude edits |
| `INTO_SKILL_BASE` | `main` | Base branch for PRs |
| `INTO_SKILL_ROOT` | `claude` | Folder in the repo holding skills, rules and hooks |
| `INTO_SKILL_TEMPLATE` | `instructions.md` beside the script | Your own instructions file; supports the `{{...}}` placeholders used in the default |

## Tests

```bash
cd claude/hooks/into-skill && python3 -m unittest -v
```

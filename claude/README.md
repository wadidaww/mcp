# Claude agent config

Skills, rules and hooks that improve how Claude agents work. Most changes here arrive as
`[INTO-SKILL]` pull requests: tag a Claude Code prompt with `[INTO-SKILL]` and Claude opens a
PR that captures what it learned in that session. See [`hooks/into-skill/`](hooks/into-skill/)
to set that up.

| Folder | What goes in it | Loaded by Claude Code from |
| --- | --- | --- |
| [`skills/`](skills/) | One folder per skill, each with a `SKILL.md` | `~/.claude/skills/<name>/` |
| [`rules/`](rules/) | Short standing guidance, one Markdown file per topic | `~/.claude/rules/*.md` |
| [`hooks/`](hooks/) | Deterministic automation, one folder per hook with its script, a `settings.example.json` and a README | `~/.claude/settings.json` |

`hooks/into-skill/install.py --link` symlinks every skill and rule from a local clone into
`~/.claude/`, so a `git pull` after merging a PR is all it takes to pick up changes.

## Choosing a kind

- **Skill**: a repeatable multi-step procedure, or knowledge only needed for some tasks.
  Claude loads it when its `description` matches the task.
- **Rule**: a preference or constraint that should hold in every session. Keep each one short.
- **Hook**: something that must always happen on an event, without relying on Claude's judgment.

Never commit secrets, tokens or personal data here.

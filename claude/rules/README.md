# Rules

Standing guidance Claude should follow in every session, one Markdown file per topic
(for example `testing.md`, `git.md`). Linked into `~/.claude/rules/`, where Claude Code loads
them at the start of each session.

Keep each rule short and specific, and say why it exists so Claude can apply it sensibly:

```markdown
# Testing

- Run only the failing tests while fixing them; run the full suite once at the end.
  Why: the full suite takes ten minutes.
```

This README is not linked by the installer.

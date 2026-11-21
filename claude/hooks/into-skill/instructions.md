<into-skill-request>
The user tagged this prompt with [INTO-SKILL]. Besides anything else the prompt asks for,
turn the lesson from this session into a lasting improvement for Claude agents and open a
pull request for the user to review. Do not merge it.

User's note: {{NOTE}}

Context:
- Target repository: {{REPO}} (base branch `{{BASE}}`)
- Local clone to edit: {{CLONE}}
- Agent config lives under `{{ROOT}}/` in that repository
- Current session: {{SESSION_ID}}, transcript at {{TRANSCRIPT}}, working directory {{CWD}}
- Prerequisite warnings:
{{WARNINGS}}

## 1. Work out the lesson

Use the user's note and this conversation. If earlier context was compacted, read the
transcript file above. Name the lesson in one sentence: what should a future Claude do
differently, and when? If the note and the session give nothing concrete to capture, ask the
user one question instead of guessing, and stop.

## 2. Pick the right kind of change

Choose the smallest change that makes the behavior stick:

| Kind | When | Where |
| --- | --- | --- |
| Skill | A repeatable multi-step procedure, or domain knowledge loaded on demand | `{{ROOT}}/skills/<kebab-name>/SKILL.md` (plus any helper files beside it) |
| Rule | A short standing preference or constraint that applies to every session | `{{ROOT}}/rules/<topic>.md` |
| Hook | Something that must happen deterministically on an event, not left to judgment | `{{ROOT}}/hooks/<name>/` with the script, a `settings.example.json` and a README |
| MCP server | A new tool or data source | a new top-level folder, following the existing servers' layout |

Prefer editing an existing file over adding a new one. Read `{{ROOT}}/README.md` and list the
existing skills and rules first. A skill's `SKILL.md` starts with YAML frontmatter holding
`name` (kebab-case) and `description` (one sentence saying when to use it), followed by
concise, imperative instructions.

## 3. Make the change on a branch, away from the user's current project

Do not touch the working directory {{CWD}} for this step unless it *is* the clone.

```bash
# Clone once if missing
[ -d "{{CLONE}}/.git" ] || gh repo clone {{REPO}} "{{CLONE}}"
cd "{{CLONE}}"
git status --porcelain          # must be clean; if not, stop and tell the user
git fetch origin {{BASE}}
git switch -c into-skill/<short-slug>-{{TODAY}} origin/{{BASE}}
```

Before writing, check for an open PR that already covers this lesson
(`gh pr list --repo {{REPO}} --label into-skill --state open`, or search titles for
`[INTO-SKILL]`). If one exists, push to its branch instead of opening a duplicate.

Write the change. Keep it free of secrets, tokens, personal data and project-specific paths
that would not make sense elsewhere.

## 4. Commit, push and open the PR

```bash
git add -A
git commit -m "into-skill: <one-line summary>"
git push -u origin HEAD
gh pr create --repo {{REPO}} --base {{BASE}} \
  --title "[INTO-SKILL] <one-line summary>" \
  --body "<body, see below>"
gh pr edit --add-label into-skill 2>/dev/null || true   # label is optional
```

The PR body should have: **Lesson** (one sentence), **Why** (what happened in the session
that prompted it), **Change** (which files and what kind), and **How to use** (any install
step, e.g. linking a skill into `~/.claude/skills/`).

## 5. Report back

Finish the rest of the user's prompt, then tell the user in two or three lines what you
captured, which kind of change you chose, and the PR link. If any step failed (no `gh`
auth, dirty clone, push refused), say exactly which step and leave the branch in place.
</into-skill-request>

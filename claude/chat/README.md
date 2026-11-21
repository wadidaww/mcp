# `[INTO-SKILL]` in the claude.ai chat

The regular claude.ai chat (web, desktop and mobile apps) does not run hooks, so the
[`into-skill` hook](../hooks/into-skill/) cannot fire there. You can get close with a
standing instruction in your preferences and a GitHub connector that can write. This
depends on Claude following the instruction, so it is less reliable than the hook.

## 1. Give Claude write access to GitHub

In claude.ai, open **Settings → Connectors** and add a GitHub connector that can create
branches, write files and open pull requests. GitHub's own MCP server
(`https://api.githubcopilot.com/mcp/`) works as a custom connector. Allow it on `wadidaww/mcp`.

## 2. Paste this into your preferences

Open **Settings → Profile** and add this to *What personal preferences should Claude consider
in responses?* (or to a Project's instructions, to limit it to one Project):

```text
[INTO-SKILL] rule: when a message of mine contains the tag [INTO-SKILL], also turn the lesson from
this conversation into an improvement for Claude agents and open a pull request on GitHub repo
wadidaww/mcp (base branch main) with the GitHub connector. Never merge it.
1. Name the lesson in one sentence (my text after the tag says what it is; if it is missing or
   vague, infer it from the conversation, and ask me one question if there is nothing concrete).
2. Choose the smallest change: a skill at claude/skills/<kebab-name>/SKILL.md (frontmatter with
   name and a one-sentence description of when to use it, then short imperative steps) for a
   repeatable procedure; a rule at claude/rules/<topic>.md for a short standing preference; or a
   hook folder under claude/hooks/<name>/ for something that must always happen. Read
   claude/README.md and the existing skills and rules first, and edit one rather than adding a
   near-duplicate.
3. Check for an open PR whose title starts with [INTO-SKILL] on the same lesson and update it
   instead of opening a second one.
4. Create a branch into-skill/<short-slug>-<yyyy-mm-dd> from main, write the files there, and
   open a PR titled "[INTO-SKILL] <summary>" whose body has Lesson, Why, Change and How to use.
5. No secrets, tokens or personal data in the change.
6. Reply with what you captured, which kind of change, and the PR link. If you have no GitHub
   tool that can write, give me the full file contents and path instead.
```

## 3. Use it

```text
[INTO-SKILL] when I ask for a summary, lead with the decision, then the reasons
```

After you merge the PR, pull your local clone so Claude Code picks it up too (see the
[hook README](../hooks/into-skill/README.md#install)). For chat, skills from this repo can also
be uploaded in **Settings → Capabilities → Skills** as a zip of the skill's folder.

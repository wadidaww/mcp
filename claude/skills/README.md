# Skills

One folder per skill. Each folder holds a `SKILL.md` and any helper files it refers to.

```text
skills/
  my-skill/
    SKILL.md
    helper.py        # optional
```

`SKILL.md` starts with frontmatter, then concise, imperative instructions:

```markdown
---
name: my-skill
description: One sentence saying when Claude should use this skill.
---

# My skill

1. Do this first.
2. Then this.
```

The `description` decides when the skill is used, so name the situation, not just the topic.

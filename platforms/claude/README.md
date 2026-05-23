# Claude Adapter

Claude Code uses the same `SKILL.md` folder format as this package.

## Personal Install

```bash
python install.py --claude --yes
```

This copies the skill to:

```text
~/.claude/skills/enterprise-drawio-diagrammer
```

Claude Code discovers personal skills from `~/.claude/skills/` and project skills from `.claude/skills/`. Restart Claude Code after installation if the skill is not visible immediately.

## Project Install

Copy the full `enterprise-drawio-diagrammer` folder to:

```text
.claude/skills/enterprise-drawio-diagrammer
```

Use this for team-shared repository behavior. Keep the helper scripts and validation files with the `SKILL.md` so Claude can run the draw.io generator and validator.

## Claude.ai

Claude.ai skills are uploaded as skill folders or archives. Zip the `enterprise-drawio-diagrammer` folder after reviewing the source and excluding generated `output/` files if you do not want the sample output included.

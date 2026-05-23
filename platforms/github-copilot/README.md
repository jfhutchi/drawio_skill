# GitHub Copilot Adapter

GitHub Copilot can consume this capability in three ways:

1. Personal agent skill: install the full skill to `~/.copilot/skills/enterprise-drawio-diagrammer`.
2. Project agent skill: copy the full skill to `.github/skills/enterprise-drawio-diagrammer`.
3. Repository guidance and reusable prompts: copy the adapter files in this folder into a repository.

## Personal Install

```bash
python install.py --copilot --yes
```

## Project Install

Copy the full skill folder into your repository:

```text
.github/skills/enterprise-drawio-diagrammer/
  SKILL.md
  src/
  validation/
  ...
```

## Repository Instructions

This adapter includes:

- `.github/copilot-instructions.md`: always-on repository instructions.
- `.github/prompts/enterprise-drawio-diagrammer.prompt.md`: reusable prompt file for Copilot Chat.
- `AGENTS.md`: agent-oriented fallback instructions for tools that read AGENTS.md.

These files do not replace the full skill folder when helper scripts are needed. They make Copilot more likely to follow the same workflow when operating inside a repository.

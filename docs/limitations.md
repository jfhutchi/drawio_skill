# Limitations

This implementation is intentionally portable and dependency-light. It provides a strong base skill plus deterministic helper code, but it is not a full enterprise diagramming platform.

## Current Limits

- The CLI does not perform live web research. The skill instructs the agent to research official sources when search or local documentation tools are available.
- File extraction is heuristic. It recognizes common infrastructure and architecture patterns, but it is not a complete Terraform, Kubernetes, OpenAPI, Mermaid, PlantUML, or source-code parser.
- Multi-page draw.io generation is documented but not fully implemented in the helper CLI.
- PNG/SVG export requires external diagrams.net or draw.io desktop tooling and is not bundled.
- Official vendor icon packs are not embedded. The default registry uses safe built-in shapes and aliases.
- Layout is deterministic and readable for moderate diagrams, but very large systems should be split into pages or separate diagrams.
- The adversarial review is rule-based. A human or AI reviewer should still inspect architecture accuracy for high-stakes use.
- The installer copies the skill into local Codex, Claude Code, GitHub Copilot, and agent skill folders. It does not modify runtime settings or force a live reload.
- Microsoft 365 Copilot support is a declarative-agent package template. Local Python generation and validation require a hosted API plugin, custom engine agent, or separate manual validation workflow.

## Recommended Next Improvements

- Add real Mermaid and PlantUML import.
- Add OpenAPI endpoint relationship extraction.
- Add Kubernetes service-to-deployment linking.
- Add Terraform dependency graph extraction.
- Add multi-page XML generation.
- Add diagrams.net CLI rendering integration for SVG/PNG verification.
- Add official cloud icon mapping where licensing permits it.
- Add complexity scoring and page-splitting recommendations.

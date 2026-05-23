---
mode: agent
description: Generate a validated enterprise draw.io diagram from architecture requests, repository files, or infrastructure configs.
---

Create an enterprise-quality draw.io / diagrams.net diagram for the request or selected files.

Follow this workflow:

1. Inspect the request and relevant files.
2. Identify the diagram type and target audience.
3. Extract components, relationships, boundaries, security controls, observability, and unknowns.
4. Build an intermediate model before XML.
5. Run adversarial review and improve the model.
6. Generate uncompressed `.drawio` XML.
7. Validate with `validation/validate_drawio.py` when available.
8. Return output paths, assumptions, unknowns, validation evidence, and suggested follow-up diagrams.

Do not preserve raw secrets or credentials in XML, Markdown, logs, or temporary files.

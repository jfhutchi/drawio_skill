# Enterprise Draw.io Diagram Instructions

When asked to create architecture, infrastructure, Kubernetes, network, security, CI/CD, code workflow, data flow, deployment, observability, runbook, or troubleshooting diagrams, use the `enterprise-drawio-diagrammer` workflow if available.

Required behavior:

- Build an intermediate model before writing draw.io XML.
- Produce valid `.drawio` / diagrams.net XML with `<mxfile>`, `<diagram>`, `<mxGraphModel>`, and root cells `0` and `1`.
- Validate edge source and target references.
- Include a legend, boundaries, directional arrows, assumptions, unknowns, and a quality checklist.
- Redact secrets, tokens, credentials, private keys, connection strings, and sensitive customer data.
- Run `validation/validate_drawio.py` when the skill helper is present.

Prefer official vendor documentation and repository files over general web sources. Separate confirmed facts from assumptions.

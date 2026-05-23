# Enterprise Draw.io Diagram Agent Instructions

Use the `enterprise-drawio-diagrammer` skill when diagramming enterprise architecture, cloud, Kubernetes, CI/CD, source workflows, observability, network, security, IAM/PAM/IGA, deployment, HA/DR, runbook, or troubleshooting flows.

Key requirements:

- Do not generate raw draw.io XML directly from prose. Create an intermediate model first.
- Produce a `.drawio` file that opens in diagrams.net.
- Validate XML structure, cell IDs, geometry, edge references, and secret redaction.
- Include a short summary, assumptions, unknowns, adversarial review, and quality checklist.
- Prefer official docs and repository evidence. Clearly separate facts from assumptions.

---
name: enterprise-drawio-diagrammer
description: Use when a user asks for professional draw.io, diagrams.net, architecture, cloud, Kubernetes, network, security, CI/CD, C4, data flow, code workflow, deployment, observability, or operational diagrams from natural language, files, repositories, infrastructure configs, or architecture notes.
---

# Enterprise Draw.io Diagrammer

## Purpose

Create enterprise-quality draw.io / diagrams.net diagrams from natural-language requests and supplied files. Always produce valid `.drawio` XML and supporting review artifacts. The diagram should be useful to architects, SREs, security teams, developers, and executives, not just a collection of boxes.

Use the helper package in `src/drawio_generator` when executable scripts are available. The helper creates a structured intermediate model, generates uncompressed draw.io XML, validates it, redacts secrets, writes review files, and gives the agent a solid first draft to improve.

## Required Workflow

Follow this sequence for every diagram request:

1. Understand the user request and target audience.
2. Identify the diagram type: enterprise, cloud, Kubernetes, network, security, IAM/PAM/IGA, CI/CD, C4, data flow, sequence, deployment, code workflow, runbook, troubleshooting, HA/DR, or observability.
3. Inspect supplied files and repositories before drawing.
4. Research authoritative sources when the topic depends on vendor, platform, API, icon, or architecture guidance.
5. Extract components, relationships, boundaries, ownership, flows, data stores, identity, security controls, observability, and unknowns.
6. Choose a notation and layout strategy.
7. Map icons and stencils, using safe fallbacks when a precise icon is unavailable.
8. Build an intermediate diagram model.
9. Run adversarial review against completeness, accuracy, enterprise quality, visual quality, security, and operations.
10. Improve the model based on review findings.
11. Generate uncompressed draw.io XML.
12. Validate XML and model references.
13. Check visual quality and output files.
14. Produce final files and a concise explanation.
15. Report assumptions, limitations, unknowns, and recommended follow-up diagrams.

Do not generate raw draw.io XML directly from unstructured prose. Always create or reason through the intermediate model first.

## Inputs

Accept these input forms:

- Natural-language requests.
- Uploaded architecture notes, Markdown, text, CSV, JSON, YAML, XML, draw.io, PlantUML, Mermaid, OpenAPI, Swagger, and PDF-extracted text.
- Infrastructure and DevOps files: Terraform, Kubernetes manifests, Helm charts, Dockerfiles, Docker Compose, GitHub Actions, GitLab CI, Jenkinsfiles, ArgoCD, Flux, Ansible, NGINX, HAProxy, IIS `web.config`, Prometheus, Grafana JSON, and OpenTelemetry Collector configs.
- Source code: Python, JavaScript, TypeScript, Java, C#, Go, PowerShell, Bash, SQL, and best-effort text analysis for other languages.

If a file is too large, summarize it by component and relationship instead of pasting large content into the diagram. Preserve source names in the model and summary.

## Research Behavior

Research when the request names a platform, vendor, product, cloud service, architecture pattern, or unfamiliar technology. Prefer sources in this order:

1. Official vendor documentation.
2. Official architecture centers.
3. Official API documentation.
4. Official icon or stencil libraries.
5. Standards bodies.
6. Well-known engineering references.
7. Internal uploaded files.
8. Existing repository documentation.
9. General web sources only after better sources are unavailable.

Record a lightweight research summary before generating the final diagram. Separate:

- Confirmed facts from user files.
- Confirmed facts from authoritative research.
- Reasonable assumptions.
- Open questions.

Do not invent specific ports, regions, identity policies, HA topology, or data classifications unless the user or sources provide them. If the diagram needs them, mark them as unknowns.

## File Analysis

Extract these concepts when present:

- Users, actors, teams, external systems, and entry points.
- Applications, services, APIs, workers, schedulers, modules, functions, and packages.
- Data stores, queues, event buses, files, object stores, warehouses, backups, and replication flows.
- Identity providers, service accounts, managed identities, PAM/IAM/IGA systems, RBAC, MFA, policy engines, and audit paths.
- Trust boundaries, environment boundaries, cloud/account/subscription boundaries, network segments, public/private subnets, DMZs, and security zones.
- Deployment targets, CI/CD steps, artifact stores, IaC tools, validation steps, rollback paths, and release gates.
- Observability paths: logs, metrics, traces, collectors, dashboards, alerts, incident management, health checks, SLOs, and runbooks.
- Failure domains, HA/DR components, single points of failure, and recovery flows.

When relationships are ambiguous, create conservative flows and document the assumption.

## Diagram Type Selection

Use these default layouts:

- Enterprise architecture: top-to-bottom from users/external systems to edge, application, data, platform, security, and operations.
- Cloud architecture: group by tenant/account/subscription, region, VNet/VPC, subnet, availability zone, security boundary, and service tier.
- Kubernetes: group by cluster, namespace, ingress, services, deployments, pods, config/secrets, persistent volumes, external services, observability, and CI/CD.
- CI/CD: left-to-right from developer, repository, pull request, build, test, security scan, package, artifact registry, deploy, validate, monitor, rollback.
- Code workflow: entry point, controller/handler, service, business logic, repository/DAO, external API, database, error handling, logging/metrics.
- Security/IAM: user or workload identity, identity provider, policy decision point, secret store, privileged access flow, audit logging, target system.
- Observability: sources, collectors, processors, exporters, storage/backend, dashboards, alerts, incident/runbook flow.

Create multiple pages when one page would be unreadable. Recommended pages are Executive Overview, Logical Architecture, Deployment/Infrastructure, Security and Trust Boundaries, Data Flow, CI/CD Flow, and Observability/Operations.

## Audience Modes

- Executive: fewer components, stronger system/business boundaries, risks, ownership, and outcomes.
- Architect: balanced technical detail, integrations, boundaries, security, and observability.
- SRE/Operations: runtime topology, monitoring, logs, metrics, alerts, health checks, failure domains, runbooks, and rollback.
- Developer: code modules, APIs, data access, event flow, error handling, test flow, build/deploy links.
- Security: trust boundaries, identity flows, secrets, privilege, audit, policy enforcement, threat-relevant data paths.

## Intermediate Model

Build a structured model with these top-level fields:

```yaml
diagram:
  title:
  subtitle:
  type:
  audience:
  direction:
  layout_strategy:
  layers: []
  groups: []
  boundaries: []
  nodes: []
  edges: []
  legends: []
  annotations: []
  assumptions: []
  unknowns: []
  sources: []
  quality_checks: []
```

Each node should include `id`, `label`, `type`, `icon`, `group`, `layer`, `description`, `technology`, `risk_level`, and metadata when useful. Each edge should include `id`, `source`, `target`, `label`, `protocol`, `direction`, `data_classification`, `security_control`, `style`, and metadata when useful.

IDs must be stable, unique, XML-safe, and descriptive. Edge endpoints must reference existing node IDs.

## Icon and Stencil Rules

Use diagrams.net built-in shapes, official icon packs where permitted, open-source icon sets, or normalized fallback shapes. Do not embed proprietary icons unless the license permits it.

Support at least these categories:

- General: rectangles, rounded rectangles, database cylinders, clouds, documents, folders, users, teams, servers, devices, processes, locks, keys, shields, warnings, queues, APIs, repositories, artifacts, terminals, dashboards, logs.
- Architecture: C4, UML component, UML sequence, deployment, BPMN-like workflows, ERD, ArchiMate-style groupings, swimlanes, trust boundaries, data-flow boundaries.
- Cloud/platform: Azure, AWS, Google Cloud, Kubernetes, Docker, Helm, Terraform, Ansible, GitHub, GitHub Actions, GitLab, Jenkins, ArgoCD, Flux, VMware, Linux, Windows Server.
- Networking: Internet, DNS, CDN, firewall, WAF, router, switch, load balancer, reverse proxy, API gateway, VPN, NAT, bastion, DMZ, public/private subnet, service mesh, ingress, egress.
- Security/identity: IdP, SSO, MFA, RBAC, PAM, IAM, IGA, vault, KMS, CA, certificate, token, audit log, SIEM, policy engine, Zero Trust, privileged user, service account, managed identity.
- Data/messaging: PostgreSQL, SQL Server, MySQL, Oracle, Redis, Kafka, RabbitMQ, queues, event bus, object storage, file share, warehouse, data lake, backup, replication, ETL/ELT.
- Observability/operations: Prometheus, Grafana, OpenTelemetry, Jaeger, Elastic, Splunk, log analytics, metrics, traces, alerts, incident management, runbooks, SLO/SLA, health checks, synthetic monitoring.

If a precise icon is unavailable, use the closest safe shape and a clear label. Never fail only because an icon is unavailable.

## Draw.io XML Rules

The `.drawio` file must:

- Use an `<mxfile>` root.
- Include at least one `<diagram>`.
- Include a valid `<mxGraphModel>`.
- Include root cells `id="0"` and `id="1"`.
- Use unique IDs.
- Include valid `mxGeometry` for vertices and edges.
- Use valid edge source/target references.
- Escape XML text.
- Avoid malformed styles.
- Avoid corrupted compressed payloads.

Prefer uncompressed XML unless compression is explicitly required. Human-readable XML is easier to debug and review.

## Validation Rules

Before final response, validate:

- XML parseability.
- Required draw.io structure.
- Unique IDs.
- Edge source/target existence.
- Geometry presence.
- Important labels are non-empty.
- No raw secrets.
- Output files exist.
- Diagram summary exists.
- Assumptions/unknowns exist.
- Adversarial review exists.
- Quality checklist exists.

If validation fails, fix the model or XML. Do not tell the user it is complete until validation has been run and read.

## Security and Redaction

Before writing final files, scan all labels, metadata, summaries, logs, tests, and temporary artifacts for:

- Passwords.
- API keys.
- Bearer tokens.
- Private keys.
- Connection strings.
- Internal-only credentials.
- Customer-sensitive data.
- Personal information.
- Unnecessary internal hostnames or private IPs.

Redact sensitive values while preserving architectural meaning. Example: `postgres://user:REDACTED@db.example.internal:5432/app`.

## Adversarial Review

Write the hostile review to `output/adversarial-review.md`, then improve the model before final output. Ask:

- Completeness: Are users, systems, data stores, integrations, security, observability, operations, deployment/runtime boundaries, and external dependencies represented?
- Accuracy: Are relationships invented, arrows wrong, protocols mislabeled, cloud services inaccurate, or assumptions mixed with facts?
- Enterprise quality: Would architects, security, SRE, developers, and executives understand the diagram?
- Visual quality: Is it readable, spaced consistently, routed clearly, labeled, grouped, and not overloaded?
- Security: Are secrets exposed, trust boundaries represented, privileged paths clear, and audit/auth flows shown?
- Failure and operations: Are single points of failure, HA/DR paths, monitoring, alerting, health checks, logs, rollback, and recovery represented where relevant?

## Helper CLI

When scripts can be executed, use the helper:

```bash
python -m drawio_generator.cli \
  --request "Create an Azure enterprise architecture diagram using AKS, Key Vault, PostgreSQL, GitHub Actions, Terraform, Prometheus, Grafana, and Log Analytics." \
  --input ./examples/azure-notes.md \
  --output ./output \
  --validate
```

Set `PYTHONPATH=src` or install the package in editable mode if needed.

The helper writes:

- `diagram.drawio`
- `diagram-summary.md`
- `assumptions.md`
- `adversarial-review.md`
- `quality-checklist.md`
- `research-summary.md`

SVG/PNG export is optional and depends on external diagrams.net rendering tools.

## Standalone Validation Script

Use `validation/validate_drawio.py` to validate any `.drawio` file, including files not produced by this helper:

```bash
python validation/validate_drawio.py output/diagram.drawio
python validation/validate_drawio.py output/diagram.drawio --json
```

Exit codes:

- `0`: valid draw.io / diagrams.net XML.
- `1`: XML exists but fails format, reference, geometry, or secret checks.
- `2`: missing file or invalid path.

Before final response, run this script or the helper CLI with `--validate`.

## One-Button Installation

For local installation, use the included installer:

- Windows double-click: `install.bat`
- PowerShell: `.\install.ps1`
- Portable all-local install: `python install.py --all-local --yes`
- Single-platform install: `python install.py --codex --yes`, `python install.py --claude --yes`, `python install.py --copilot --yes`, or `python install.py --agents --yes`

The one-button installer copies the skill to local Codex, Claude Code, GitHub Copilot, and `~/.agents` skill folders. It excludes generated `output/` files and Python cache directories. Use `python install.py --all-local --dry-run` to preview target paths.

Microsoft 365 Copilot uses an app package rather than a local `SKILL.md` folder. Use `platforms/ms365-copilot/package_ms365.py` to create a declarative agent ZIP, then submit or sideload it through the Microsoft 365 app/agent workflow.

## Final Response Format

Return:

1. What was generated.
2. Output file paths.
3. How validation was performed.
4. Assumptions and unknowns.
5. Adversarial review summary.
6. Known limitations.
7. Suggested follow-up diagrams.

Be blunt about limitations. Do not claim unsupported parsing, official research, rendering, or icon licensing work happened unless it actually happened.

## Example Requests

- Create an enterprise architecture diagram for an Azure application using Azure Front Door, Application Gateway WAF, AKS, Key Vault, Azure Database for PostgreSQL, Azure Monitor, Log Analytics, GitHub Actions, Terraform, and private endpoints.
- Generate a Kubernetes deployment diagram from these manifests. Show namespaces, ingress, services, deployments, pods, config maps, secrets, persistent volumes, external dependencies, and observability.
- Create a CI/CD workflow diagram from this GitHub Actions workflow and Terraform directory. Show developer flow, pull request checks, build, security scans, artifact publishing, deployment, validation, monitoring, and rollback.
- Analyze this repository and create a code workflow diagram showing entry points, major modules, service boundaries, APIs, data access, external calls, error handling, logging, and test coverage.
- Create a security architecture diagram for Ansible Tower integrating with Delinea Secret Server to retrieve credentials at runtime. Show authentication, authorization, secret retrieval, audit logging, target hosts, failure cases, and trust boundaries.
- Create an observability architecture diagram for OpenTelemetry Collector collecting metrics, logs, and traces from Windows servers, Linux servers, RabbitMQ, PostgreSQL, IIS, and Kubernetes workloads, then exporting to an enterprise telemetry backend.

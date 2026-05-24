---
name: enterprise-drawio-diagrammer
description: Use when a user asks for professional draw.io, diagrams.net, architecture, cloud, Kubernetes, network, security, CI/CD, C4, data flow, code workflow, deployment, observability, or operational diagrams from natural language, files, repositories, infrastructure configs, or architecture notes.
---

# Enterprise Draw.io Diagrammer

## Purpose

Create enterprise-quality draw.io / diagrams.net diagrams from natural-language requests and supplied files. Always produce valid `.drawio` XML and supporting review artifacts. The diagram should be useful to architects, SREs, security teams, developers, and executives, not just a collection of boxes.

Use the helper package in `src/drawio_generator` when executable scripts are available. The helper creates a structured intermediate model, plans executive/detail pages, selects a reference visual pattern, generates uncompressed draw.io XML, validates it, redacts secrets, writes review files, and gives the agent a solid first draft to improve.

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
9. Build a page plan that separates the executive overview from implementation detail, security, data/evidence flow, and operations follow-up.
10. Generate real draw.io pages from the page plan: Page 1 executive view, later pages for detail/security/data/operations.
11. Select a visual pattern and write `visual-guide.md`.
12. Run adversarial review against completeness, accuracy, enterprise quality, visual quality, security, and operations.
13. Improve the model based on review findings.
14. Generate uncompressed draw.io XML.
15. Validate XML and model references.
16. Run static visual QA and renderer availability detection; write `render-qa.md`.
17. Check visual quality and output files.
18. Produce final files and a concise explanation.
19. Report assumptions, limitations, unknowns, and recommended follow-up diagrams.

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

- Enterprise architecture: left-to-right executive flow from source/control systems, orchestration, targets, workspace/data objects, reports/evidence, optional storage, then consumers. Use wider swimlanes and avoid crossing zone boundaries unless the flow requires it.
- Cloud architecture: group by tenant/account/subscription, region, VNet/VPC, subnet, availability zone, security boundary, and service tier.
- Kubernetes: group by cluster, namespace, ingress, services, deployments, pods, config/secrets, persistent volumes, external services, observability, and CI/CD.
- CI/CD: left-to-right from developer, repository, pull request, build, test, security scan, package, artifact registry, deploy, validate, monitor, rollback.
- Code workflow: entry point, controller/handler, service, business logic, repository/DAO, external API, database, error handling, logging/metrics.
- Security/IAM: user or workload identity, identity provider, policy decision point, secret store, privileged access flow, audit logging, target system.
- Observability: sources, collectors, processors, exporters, storage/backend, dashboards, alerts, incident/runbook flow.

Create multiple pages when one page would be unreadable. Recommended pages are Executive Overview, Logical Architecture, Deployment/Infrastructure, Security and Trust Boundaries, Data Flow, CI/CD Flow, and Observability/Operations.

## Page Planning

Before generating the final draw.io XML, create a page plan and write it to `page-plan.md`. The helper uses this plan to create real pages inside `diagram.drawio`:

- Executive Overview: the primary flow, ownership zones, trust boundaries, critical outputs, and optional handoffs.
- Implementation Detail: role stacks, job templates, inventories, variables, controller workspace details, and implementation mechanics.
- Security and Trust Boundaries: trust zones, secret retrieval, privileged access, sensitive paths, audit, and policy controls.
- Data and Evidence Flow: collected data, staged evidence, reports, workbooks, queues, databases, SFS, and optional storage.
- Operations and Follow-Up: monitoring, logs, health checks, runbooks, assumptions, unknowns, limits, and follow-up diagrams.

Use `page-plan.md` as a quality gate: if Page 1 includes content that belongs on a detail page, simplify Page 1 before final delivery.

## Visual Pattern Selection

Before final output, select a reference visual pattern and write it to `visual-guide.md`. Use it to steer layout, palette, callouts, icon choices, and routing:

- Azure Reference Architecture: primary/secondary regions, tier columns, dashed network boundaries, Azure-blue service tiles, and blue numbered callouts.
- AWS Reference Architecture: account/VPC/domain containers, service-category colors, data lake/governance/processing/analytics bands, and blue numbered review callouts.
- Data Platform Pipeline: Sources -> Process -> Store -> Serve, lower governance/platform bands, green numbered callouts, and data-tier state labels such as bronze/silver/gold when present.
- Presentation Architecture: dark or branded canvas, large central subject, sparse text, high-contrast accent color, and fewer callouts.
- Enterprise Reference Architecture: source/control -> control plane -> targets -> evidence/reports -> consumers, semantic edge colors, trust boundaries, and numbered flow legend.

Do not blindly apply one style to all diagrams. Match the visual pattern to the audience, vendor, and diagram purpose.

## Executive Readability Rules

For Page 1 or any executive architecture review, readability wins over completeness:

- Keep Page 1 understandable in about 30 seconds. Show the main architecture path, ownership zones, trust boundaries, and critical outputs; move variable lists, role internals, host inventories, and long role-level detail to later pages or Markdown artifacts.
- Use short numbered edge labels on busy diagrams. Put the full flow descriptions in a legend or callout instead of writing long labels over arrows.
- Prefer a single clean flow direction. For automation/reporting diagrams, use: Source Control -> Tower/AWX or controller -> Customer Targets -> Controller Workspace/Data Objects -> Reports/SFS -> Consumers.
- Size nodes for reading first. Use fewer words per shape, larger nodes, more whitespace, and one clear concept per shape. Turn dense role lists into compact stacks, matrices, or follow-up pages.
- Render data objects as data objects. Examples: collected health data, staged results, Excel workbooks, reports, queues, databases, vaults, and object storage should not look like generic process boxes.
- Put consumers downstream and outside the report-generation path. Optional destinations such as SFS or object storage should sit below or far right with dashed optional routing.
- Show trust boundaries on Page 1 when security ownership matters. Use dashed red boundaries for customer, external, privileged, or sensitive zones.
- Use light fills with dark text even when diagrams.net is in dark mode. Avoid heavy dark boxes and tiny white text in production diagrams.
- Include a compact security callout when applicable: no secrets in source control or reports; generated reports may contain sensitive configuration evidence.

Use these default line semantics on Page 1:

- Blue or purple solid: control flow, orchestration, sync, and job launch.
- Green solid: target collection, health checks, and inventory/evidence retrieval.
- Yellow or amber solid: evidence, report, workbook, and consumer flow.
- Gray dashed: optional external storage or optional handoff.
- Red dashed: secrets, credentials, privileged access, or sensitive security paths.

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

If a precise icon is unavailable, use the closest safe shape and a clear label. Never fail only because an icon is unavailable. The helper records vendor-aware fallback metadata for common Azure and AWS service names, but those are diagrams.net built-in fallback shapes by default. Do not call them official Microsoft/Azure/AWS icons unless a licensed local official icon pack was actually used and documented.

Use icon-like visual cues for common enterprise review nodes: repository/folder for source control, controller/process for Tower/AWX, server for Linux/Windows targets, cylinder for databases, queue for RabbitMQ/Kafka, note/document for Excel workbooks and reports, vault/lock for secret stores, cloud/object for SFS or object storage, and actor/user shapes for consumers.

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
- Busy edge labels are shortened or numbered with full descriptions moved to a legend.
- Page 1 has enough spacing for nodes, labels, and routed arrows to avoid overlaps.
- `page-plan.md` exists and separates executive content from detail, security, data/evidence, and operations content.
- `visual-guide.md` exists and selects the reference visual pattern, layout rules, callout rules, and quality gates.
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
- `page-plan.md`
- `visual-guide.md`
- `render-qa.md`
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
3. Page-plan summary.
4. Visual-guide summary.
5. How validation and visual QA were performed.
6. Assumptions and unknowns.
7. Adversarial review summary.
8. Known limitations.
9. Suggested follow-up diagrams.

Be blunt about limitations. Do not claim unsupported parsing, official research, rendering, or icon licensing work happened unless it actually happened.

## Example Requests

- Create an enterprise architecture diagram for an Azure application using Azure Front Door, Application Gateway WAF, AKS, Key Vault, Azure Database for PostgreSQL, Azure Monitor, Log Analytics, GitHub Actions, Terraform, and private endpoints.
- Generate a Kubernetes deployment diagram from these manifests. Show namespaces, ingress, services, deployments, pods, config maps, secrets, persistent volumes, external dependencies, and observability.
- Create a CI/CD workflow diagram from this GitHub Actions workflow and Terraform directory. Show developer flow, pull request checks, build, security scans, artifact publishing, deployment, validation, monitoring, and rollback.
- Analyze this repository and create a code workflow diagram showing entry points, major modules, service boundaries, APIs, data access, external calls, error handling, logging, and test coverage.
- Create a security architecture diagram for Ansible Tower integrating with Delinea Secret Server to retrieve credentials at runtime. Show authentication, authorization, secret retrieval, audit logging, target hosts, failure cases, and trust boundaries.
- Create an observability architecture diagram for OpenTelemetry Collector collecting metrics, logs, and traces from Windows servers, Linux servers, RabbitMQ, PostgreSQL, IIS, and Kubernetes workloads, then exporting to an enterprise telemetry backend.

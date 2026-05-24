# Enterprise Draw.io Diagrammer

`enterprise-drawio-diagrammer` is an agent skill and Python helper package for producing professional diagrams.net / draw.io diagrams from architecture requests, notes, and common infrastructure files.

The skill is designed around a structured intermediate model. The agent extracts components and flows, plans what belongs on executive and detail pages, selects a reference visual pattern, reviews the model adversarially, improves it, generates uncompressed `.drawio` XML, validates the result, and writes supporting review artifacts.

## Quick Start

### One-Button Install

On Windows, double-click:

```text
install.bat
```

That installs the skill to local Codex, Claude Code, GitHub Copilot, and `~/.agents` skill folders:

```text
%USERPROFILE%\.codex\skills\enterprise-drawio-diagrammer
%USERPROFILE%\.claude\skills\enterprise-drawio-diagrammer
%USERPROFILE%\.copilot\skills\enterprise-drawio-diagrammer
%USERPROFILE%\.agents\skills\enterprise-drawio-diagrammer
```

Restart the relevant agent if the skill is not visible immediately.

For PowerShell:

```powershell
.\install.ps1
```

For an explicit target or dry run:

```powershell
python .\install.py --all-local --dry-run
python .\install.py --all-local --yes
```

Target one platform explicitly:

```powershell
python .\install.py --codex --yes
python .\install.py --claude --yes
python .\install.py --copilot --yes
python .\install.py --agents --yes
```

From this directory:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m drawio_generator.cli `
  --request "Create an enterprise architecture diagram for an Azure-hosted web application using AKS, Key Vault, PostgreSQL, GitHub Actions, Terraform, Prometheus, Grafana, and centralized logging." `
  --input .\examples\azure-notes.md `
  --output .\output `
  --validate
```

On POSIX shells:

```bash
PYTHONPATH=src python -m drawio_generator.cli \
  --request "Create an enterprise architecture diagram for an Azure-hosted web application using AKS, Key Vault, PostgreSQL, GitHub Actions, Terraform, Prometheus, Grafana, and centralized logging." \
  --input ./examples/azure-notes.md \
  --output ./output \
  --validate
```

## Outputs

The helper writes:

- `output/diagram.drawio`
- `output/diagram-summary.md`
- `output/page-plan.md`
- `output/visual-guide.md`
- `output/render-qa.md`
- `output/assumptions.md`
- `output/adversarial-review.md`
- `output/quality-checklist.md`
- `output/research-summary.md`

The helper writes real multi-page uncompressed `.drawio` files from `page-plan.md`: Page 1 is the executive architecture view, while later pages carry implementation detail, security/trust, data/evidence, and operations content. Open `diagram.drawio` in diagrams.net. The XML is intentionally uncompressed so it can be inspected and repaired if needed.

## Validate Existing Draw.io Files

Run the standalone validation script against any `.drawio` file:

```powershell
python .\validation\validate_drawio.py .\output\diagram.drawio
python .\validation\validate_drawio.py .\output\diagram.drawio --json
```

The validator checks XML parseability, `<mxfile>`, `<diagram>`, `<mxGraphModel>`, root cells `0` and `1`, unique cell IDs, geometry, edge source/target references, and unredacted secrets. It exits `0` for valid files, `1` for format/validation errors, and `2` for missing or invalid input paths.

## Platform Adapters

- Claude Code: install with `python install.py --claude --yes`, or copy the folder to `.claude/skills/enterprise-drawio-diagrammer`.
- GitHub Copilot: install personal agent skills with `python install.py --copilot --yes`, copy the folder to `.github/skills/enterprise-drawio-diagrammer` for a repository skill, or copy `platforms/github-copilot/.github/*` into a repository for instructions and prompt files.
- Microsoft 365 Copilot: build a declarative agent package with `python platforms/ms365-copilot/package_ms365.py --output enterprise-drawio-diagrammer-ms365.zip`. This package guides Copilot to create draw.io XML but cannot run local Python validation unless you add a hosted API plugin/action.

## Tests

```bash
python -m unittest discover -s tests
```

The tests cover model validation, draw.io XML generation, file ingestion heuristics, redaction, adversarial review, CLI output, and required skill artifacts.

## GitHub Actions

This repo includes two workflows under `.github/workflows/`:

- `ci.yml`: runs on pushes and pull requests to `main`/`master`; installs the package, runs tests on Python 3.11, 3.12, and 3.13, generates and validates a sample `.drawio`, checks installer dry-run, validates JSON manifests, and builds the Microsoft 365 package.
- `package.yml`: runs manually or on `v*` tags; runs tests, generates a validated sample, builds `enterprise-drawio-diagrammer.skill.zip`, builds `enterprise-drawio-diagrammer-ms365.zip`, and uploads both as workflow artifacts.

These workflows assume the contents of this folder are the root of the GitHub repository.

## Supported Inputs

The helper performs best-effort text analysis for Markdown, text, JSON, YAML, XML, draw.io, PlantUML, Mermaid, Terraform, Kubernetes manifests, GitHub Actions, OpenTelemetry Collector configs, Docker/Jenkins style files, common source files, and SQL.

The skill instructions are broader than the helper. When an AI agent has web search, repository access, PDF extraction, or vendor documentation access, it should use those sources and update the intermediate model before generating final XML.

## Architecture

- `diagram_model.py`: dataclasses for diagrams, boundaries, nodes, edges, legends, annotations, assumptions, unknowns, and sources.
- `file_ingestion.py`: best-effort extraction from requests and files.
- `adversarial_review.py`: hostile review and safe model improvements.
- `layout_engine.py`: deterministic enterprise layout heuristics.
- `page_planner.py`: recommends Page 1 versus detail, security, data/evidence, and operations follow-up content.
- `visual_patterns.py`: recommends Azure, AWS, data-platform, presentation, or enterprise reference visual patterns.
- `visual_qa.py`: detects local renderer availability and runs static overlap/off-canvas/label/badge checks.
- `icon_registry.py`: vendor-aware built-in draw.io style mappings with safe fallbacks that do not claim official vendor icons.
- `drawio_xml.py`: single-page and multi-page XML generation from the intermediate model.
- `validators.py`: model/XML validation and secret redaction.
- `cli.py`: command-line workflow that writes the required output artifacts.

## Known Limits

This is a portable, dependency-light implementation. It records whether a local draw.io/diagrams.net renderer is available and always runs static visual QA, but it does not export PNG/SVG/screenshots unless external renderer integration is added. It does not perform live web research by itself, and uses heuristics rather than full parsers for complex IaC/codebases. The skill instructs the agent to fill those gaps when richer tools are available.

"""Hostile review pass for enterprise diagram quality."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .diagram_model import Boundary, Diagram, LegendItem
from .validators import validate_model


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    category: str
    severity: str
    message: str
    recommendation: str


BOUNDARY_REQUIRED_TYPES = {"enterprise", "cloud", "kubernetes", "security", "network", "data-flow"}


def review_diagram(diagram: Diagram) -> list[ReviewFinding]:
    """Review a diagram as an architect, SRE, and security reviewer."""

    findings: list[ReviewFinding] = []
    for issue in validate_model(diagram):
        findings.append(ReviewFinding("correctness", issue.severity, issue.message, "Fix the model invariant before generating XML."))

    if not diagram.title.strip():
        findings.append(ReviewFinding("enterprise quality", "error", "Diagram is missing a title.", "Add a clear title."))
    if not diagram.legends:
        findings.append(ReviewFinding("visual quality", "warning", "Diagram is missing a legend.", "Add a concise legend for colors, boundaries, and flow semantics."))
    if diagram.diagram_type.lower() in BOUNDARY_REQUIRED_TYPES and not diagram.boundaries:
        findings.append(ReviewFinding("security", "warning", "Diagram has no trust boundary or environment boundary.", "Add at least one meaningful boundary."))
    if not diagram.edges and len(diagram.nodes) > 1:
        findings.append(ReviewFinding("completeness", "warning", "Diagram has components but no relationships.", "Add directional, labeled flows."))
    for edge in diagram.edges:
        if not edge.label.strip():
            findings.append(ReviewFinding("accuracy", "warning", f"Edge {edge.id} has no meaningful label.", "Label important flows with protocol or purpose."))

    labels = " ".join(node.label.lower() for node in diagram.nodes)
    if diagram.diagram_type.lower() in {"enterprise", "cloud", "kubernetes"} and not any(term in labels for term in ["monitor", "prometheus", "grafana", "log", "telemetry", "alert"]):
        findings.append(ReviewFinding("operations", "info", "Observability path is not represented.", "Add observability components if supported by evidence, otherwise record as an unknown."))
    if diagram.diagram_type.lower() in {"enterprise", "cloud", "security", "kubernetes"} and not any(term in labels for term in ["vault", "iam", "identity", "waf", "firewall", "secret", "rbac", "mfa"]):
        findings.append(ReviewFinding("security", "info", "Security controls are not represented.", "Add known controls or record the missing controls as unknowns."))
    if len(diagram.nodes) > 35:
        findings.append(ReviewFinding("visual quality", "warning", "Diagram may be overloaded with too many nodes.", "Split into multiple pages or summarize by layer."))

    return findings


def improve_diagram(diagram: Diagram, findings: list[ReviewFinding]) -> Diagram:
    """Apply safe, non-inventive improvements based on review findings."""

    improved = deepcopy(diagram)
    messages = " ".join(finding.message.lower() for finding in findings)

    if "legend" in messages and not improved.legends:
        improved.legends.extend(
            [
                LegendItem("Blue", "Application, platform, and network services"),
                LegendItem("Purple", "Identity, secrets, and security controls"),
                LegendItem("Green", "Operations, telemetry, and healthy workflow steps"),
                LegendItem("Dashed boundary", "Trust, environment, cloud, or ownership boundary"),
            ]
        )

    if "trust boundary" in messages or "environment boundary" in messages:
        if not improved.boundaries:
            boundary = Boundary(id="boundary-architecture", label="Architecture / Trust Boundary", boundary_type="trust")
            improved.boundaries.append(boundary)
            for node in improved.nodes:
                if not node.group:
                    node.group = boundary.id
            improved.assumptions.append("A single high-level architecture boundary was added because no explicit boundary was provided.")

    if "observability path is not represented" in messages:
        improved.unknowns.append("Monitoring, logging, metrics, traces, and alert destinations were not confirmed.")
    if "security controls are not represented" in messages:
        improved.unknowns.append("Authentication, authorization, secrets, audit logging, and trust boundaries need confirmation.")
    if not improved.assumptions:
        improved.assumptions.append("The diagram uses best-effort extraction from the request and provided files.")
    if not improved.unknowns:
        improved.unknowns.append("Exact regions, ownership, network CIDRs, ports, and HA/DR details were not fully specified.")

    for check in [
        "XML must parse as diagrams.net mxfile.",
        "Every edge must reference existing nodes.",
        "Critical flows should be directional and labeled.",
        "Secrets and credentials must be redacted before final output.",
        "Assumptions and unknowns must be documented.",
    ]:
        improved.add_quality_check(check)

    return improved


def render_adversarial_review(before: list[ReviewFinding], after: list[ReviewFinding]) -> str:
    """Render review findings for output/adversarial-review.md."""

    lines = ["# Adversarial Review", "", "## Initial Findings"]
    if before:
        lines.extend(_render_findings(before))
    else:
        lines.append("- No findings.")
    lines.extend(["", "## Post-Improvement Findings"])
    if after:
        lines.extend(_render_findings(after))
    else:
        lines.append("- No remaining findings from automated review.")
    return "\n".join(lines) + "\n"


def _render_findings(findings: list[ReviewFinding]) -> list[str]:
    return [
        f"- **{finding.severity.upper()} / {finding.category}:** {finding.message} Recommendation: {finding.recommendation}"
        for finding in findings
    ]

"""Command-line interface for the enterprise draw.io diagrammer helper."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .adversarial_review import improve_diagram, render_adversarial_review, review_diagram
from .diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from .drawio_xml import generate_drawio_xml
from .file_ingestion import ExtractionResult, extract_components_from_text, load_inputs
from .page_planner import build_page_plan, render_page_plan
from .research_planner import render_research_summary
from .validators import redact_sensitive_text, validate_drawio_xml, validate_model


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    request = redact_sensitive_text(args.request)
    extraction = extract_components_from_text("request", request)
    extraction.extend(load_inputs(args.input, args.input_dir))

    diagram_type = args.diagram_type or detect_diagram_type(request)
    diagram = build_diagram(request, extraction, diagram_type, args.audience, args.layout)
    initial_findings = review_diagram(diagram)
    improved = improve_diagram(diagram, initial_findings)
    final_findings = review_diagram(improved)
    page_plan = build_page_plan(improved)

    model_issues = [issue for issue in validate_model(improved) if issue.severity == "error"]
    if model_issues:
        for issue in model_issues:
            print(f"model validation error: {issue.message}", file=sys.stderr)
        return 2

    drawio_xml = generate_drawio_xml(improved)
    xml_issues = [issue for issue in validate_drawio_xml(drawio_xml) if issue.severity == "error"]
    if args.validate and xml_issues:
        for issue in xml_issues:
            print(f"draw.io validation error: {issue.message}", file=sys.stderr)
        return 3

    (output_dir / "diagram.drawio").write_text(drawio_xml, encoding="utf-8")
    (output_dir / "diagram-summary.md").write_text(render_summary(improved), encoding="utf-8")
    (output_dir / "page-plan.md").write_text(render_page_plan(page_plan), encoding="utf-8")
    (output_dir / "assumptions.md").write_text(render_assumptions(improved), encoding="utf-8")
    (output_dir / "adversarial-review.md").write_text(render_adversarial_review(initial_findings, final_findings), encoding="utf-8")
    (output_dir / "quality-checklist.md").write_text(render_quality_checklist(improved, xml_issues, has_page_plan=True), encoding="utf-8")
    (output_dir / "research-summary.md").write_text(render_research_summary(request, diagram_type), encoding="utf-8")

    print(f"Wrote draw.io diagram and review artifacts to {output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate enterprise diagrams.net XML from requests and files.")
    parser.add_argument("--request", required=True, help="Natural-language diagram request.")
    parser.add_argument("--input", action="append", help="Input file to inspect. May be repeated.")
    parser.add_argument("--input-dir", help="Directory of input files to inspect.")
    parser.add_argument("--diagram-type", help="Diagram type override, such as enterprise, cloud, kubernetes, cicd, code, security.")
    parser.add_argument("--audience", default="architect", choices=["executive", "architect", "sre", "developer", "security"], help="Audience mode.")
    parser.add_argument("--output", default="./output", help="Output directory.")
    parser.add_argument("--validate", action="store_true", help="Fail if generated draw.io XML has validation errors.")
    parser.add_argument("--redact", action="store_true", help="Accepted for compatibility; redaction is always enabled.")
    parser.add_argument("--format", default="drawio", choices=["drawio"], help="Output format.")
    parser.add_argument("--theme", default="enterprise", help="Theme name. Currently only enterprise is implemented.")
    parser.add_argument("--layout", choices=["top-to-bottom", "left-to-right"], help="Layout direction override.")
    parser.add_argument("--max-nodes", type=int, default=35, help="Soft maximum node count before quality warning.")
    return parser


def detect_diagram_type(request: str) -> str:
    lowered = request.lower()
    if "security architecture" in lowered or any(term in lowered for term in ["iam", "pam", "iga", "zero trust"]):
        return "security"
    if "enterprise architecture" in lowered:
        return "enterprise"
    if "cloud architecture" in lowered:
        return "cloud"
    if "kubernetes deployment" in lowered or "kubernetes architecture" in lowered:
        return "kubernetes"
    if "ci/cd workflow" in lowered or "pipeline diagram" in lowered:
        return "cicd"
    if any(term in lowered for term in ["github actions", "pipeline", "ci/cd", "build", "deploy"]):
        return "cicd"
    if any(term in lowered for term in ["kubernetes", "aks", "namespace", "pods", "ingress"]):
        return "kubernetes"
    if any(term in lowered for term in ["security", "secret", "vault"]):
        return "security"
    if any(term in lowered for term in ["code workflow", "repository", "module", "class", "function"]):
        return "code"
    if any(term in lowered for term in ["aws", "azure", "google cloud", "vpc", "vnet", "region"]):
        return "cloud"
    return "enterprise"


def build_diagram(request: str, extraction: ExtractionResult, diagram_type: str, audience: str, layout: str | None) -> Diagram:
    nodes = _dedupe_nodes(extraction.components)
    if not nodes:
        nodes = [
            Node(id="user", label="User / External System", node_type="user"),
            Node(id="application", label="Application", node_type="backend"),
            Node(id="data-store", label="Data Store", node_type="database"),
        ]
    nodes = _apply_audience_filter(nodes, audience)
    boundaries = _build_boundaries(diagram_type, nodes, request)
    edges = _build_edges(nodes, extraction.relationships)
    title = _title_from_request(request, diagram_type)
    direction = layout or ("left-to-right" if diagram_type in {"enterprise", "cloud", "cicd", "workflow", "code"} else "top-to-bottom")
    _assign_node_groups(nodes, boundaries, diagram_type)
    diagram = Diagram(
        title=title,
        subtitle=f"{audience.title()} view generated from request and supplied files",
        diagram_type=diagram_type,
        audience=audience,
        direction=direction,
        layout_strategy="executive-flow" if direction == "left-to-right" and diagram_type in {"enterprise", "cloud"} else "layered",
        boundaries=boundaries,
        nodes=nodes,
        edges=edges,
        legends=[
            LegendItem("Blue/Purple", "Control flow and orchestration"),
            LegendItem("Green", "Target collection and health checks"),
            LegendItem("Yellow", "Evidence, report, and workbook flow"),
            LegendItem("Gray dashed", "Optional external storage path"),
            LegendItem("Red dashed", "Sensitive security or secret path"),
        ],
        assumptions=[
            "Relationships are generated from explicit text when available, then completed with conservative enterprise flow heuristics.",
            "Official research should be added by the agent when web or internal documentation access is available.",
        ],
        unknowns=[
            "Exact regions, network CIDRs, identity policies, ports, owners, and HA/DR topology require confirmation unless provided in inputs.",
        ],
        sources=extraction.sources or ["request"],
    )
    return diagram


def _dedupe_nodes(nodes: list[Node]) -> list[Node]:
    seen: set[str] = set()
    deduped: list[Node] = []
    for node in nodes:
        base = node.id
        candidate = base
        counter = 2
        while candidate in seen:
            candidate = f"{base}-{counter}"
            counter += 1
        node.id = candidate
        seen.add(candidate)
        deduped.append(node)
    return deduped


def _apply_audience_filter(nodes: list[Node], audience: str) -> list[Node]:
    if audience != "executive" or len(nodes) <= 12:
        return nodes
    priority = {"cdn", "gateway", "waf", "kubernetes", "database", "secret", "identity", "monitoring", "process"}
    filtered = [node for node in nodes if node.node_type in priority]
    return filtered[:12] or nodes[:12]


def _build_boundaries(diagram_type: str, nodes: list[Node], request: str) -> list[Boundary]:
    if diagram_type == "cicd":
        return [Boundary(id="boundary-delivery", label="Software Delivery Pipeline", boundary_type="workflow")]
    if diagram_type == "kubernetes":
        return [Boundary(id="boundary-cluster", label="Kubernetes Cluster / Namespace Boundary", boundary_type="platform")]
    if diagram_type == "security":
        return [Boundary(id="boundary-trust", label="Trust Boundary", boundary_type="trust")]
    if diagram_type in {"enterprise", "cloud"}:
        semantic_boundaries = _build_enterprise_boundaries(nodes)
        if semantic_boundaries:
            return semantic_boundaries
    if "azure" in request.lower() or any("Azure" in node.label or node.label == "AKS" for node in nodes):
        return [Boundary(id="boundary-azure", label="Azure Subscription / Region", boundary_type="cloud")]
    if diagram_type in {"enterprise", "cloud", "network"}:
        return [Boundary(id="boundary-enterprise", label="Enterprise Architecture Boundary", boundary_type="logical")]
    return []


def _build_enterprise_boundaries(nodes: list[Node]) -> list[Boundary]:
    specs = [
        ("boundary-source-control", "Source Control Zone", "logical"),
        ("boundary-automation-control", "Automation Control Zone", "logical"),
        ("boundary-customer-infrastructure", "Customer Infrastructure Trust Boundary", "trust"),
        ("boundary-controller-workspace", "Controller Workspace Zone", "logical"),
        ("boundary-reporting-evidence", "Reporting / Evidence Zone", "logical"),
        ("boundary-optional-external-storage", "Optional External Storage Trust Boundary", "trust"),
        ("boundary-report-consumers", "Report Consumers", "logical"),
    ]
    matched_groups = {_enterprise_group_for_node(node) for node in nodes}
    return [
        Boundary(id=group_id, label=label, boundary_type=boundary_type)
        for group_id, label, boundary_type in specs
        if group_id in matched_groups
    ]


def _assign_node_groups(nodes: list[Node], boundaries: list[Boundary], diagram_type: str) -> None:
    if not boundaries:
        return
    boundary_ids = {boundary.id for boundary in boundaries}
    if diagram_type in {"enterprise", "cloud"}:
        for node in nodes:
            group_id = _enterprise_group_for_node(node)
            if group_id in boundary_ids:
                node.group = group_id
            elif not node.group:
                node.group = boundaries[0].id
        return
    for node in nodes:
        if not node.group:
            node.group = boundaries[0].id


def _enterprise_group_for_node(node: Node) -> str:
    text = f"{node.node_type} {node.label} {node.icon or ''}".lower()
    if any(term in text for term in ["consumer", "reviewer", "engineer", "auditor", "stakeholder"]):
        return "boundary-report-consumers"
    if any(term in text for term in ["sfs", "object storage", "file share", "external storage"]):
        return "boundary-optional-external-storage"
    if any(term in text for term in ["secret", "vault", "credential"]):
        return "boundary-automation-control"
    if any(term in text for term in ["report", "workbook", "excel", "evidence", "artifact", "dashboard"]):
        return "boundary-reporting-evidence"
    if any(term in text for term in ["controller workspace", "runtime workspace", "collected health data", "staged results"]):
        return "boundary-controller-workspace"
    if any(term in text for term in ["target", "linux", "windows", "server", "postgres", "rabbitmq", "iis", "pgbouncer", "zabbix", "database", "queue", "kubernetes"]):
        return "boundary-customer-infrastructure"
    if any(term in text for term in ["tower", "awx", "ansible", "terraform", "job template", "workflow", "orchestration", "pipeline", "process"]):
        return "boundary-automation-control"
    if any(term in text for term in ["github repository", "repository", "source control", "gitlab"]):
        return "boundary-source-control"
    return "boundary-automation-control"


def _build_edges(nodes: list[Node], extracted: list[Edge]) -> list[Edge]:
    node_ids = {node.id for node in nodes}
    edges: list[Edge] = [edge for edge in extracted if edge.source in node_ids and edge.target in node_ids]
    labels = {node.label.lower(): node for node in nodes}

    def add_if_present(
        source_names: list[str],
        target_names: list[str],
        label: str,
        protocol: str | None = None,
        flow_type: str = "control",
    ) -> None:
        source = _find_node(labels, source_names)
        target = _find_node(labels, target_names)
        if source and target and source.id != target.id:
            edge_id = f"edge-{source.id}-{target.id}"
            if not any(edge.id == edge_id for edge in edges):
                edges.append(Edge(id=edge_id, source=source.id, target=target.id, label=label, protocol=protocol, metadata={"flow_type": flow_type}))

    add_if_present(["azure front door"], ["application gateway waf", "application gateway", "aks"], "HTTPS ingress", "HTTPS")
    add_if_present(["application gateway waf", "application gateway"], ["aks", "azure kubernetes service"], "WAF-routed HTTPS", "HTTPS")
    add_if_present(["aks", "azure kubernetes service"], ["key vault", "delinea secret server"], "retrieves secrets", "TLS", "security_sensitive")
    add_if_present(["aks", "azure kubernetes service"], ["azure database for postgresql", "postgresql"], "SQL over TLS", "TLS", "target_collection")
    add_if_present(["github actions"], ["terraform"], "runs plan/apply")
    add_if_present(["terraform"], ["aks", "azure kubernetes service", "key vault", "azure database for postgresql"], "provisions")
    add_if_present(["prometheus"], ["grafana"], "dashboard data", flow_type="report_evidence")
    add_if_present(["aks", "azure kubernetes service"], ["prometheus"], "metrics scrape", flow_type="target_collection")
    add_if_present(["aks", "azure kubernetes service"], ["log analytics"], "logs and diagnostics", flow_type="report_evidence")
    add_if_present(["opentelemetry collector"], ["prometheus", "grafana", "log analytics"], "exports telemetry", flow_type="report_evidence")
    add_if_present(["github repository"], ["ansible tower", "awx"], "Project sync pulls latest SHC repository", flow_type="control")
    add_if_present(["ansible tower", "awx"], ["linux server", "windows server", "target platforms", "postgresql", "rabbitmq", "iis", "pgbouncer"], "Collect health and security evidence", flow_type="target_collection")
    add_if_present(["ansible tower", "awx"], ["delinea secret server", "key vault"], "Retrieve runtime secrets", "TLS", "security_sensitive")
    add_if_present(["target platforms", "linux server", "windows server", "postgresql", "rabbitmq"], ["report generation", "excel workbook", "customer excel workbooks"], "Stage evidence for workbook generation", flow_type="report_evidence")
    add_if_present(["report generation", "excel workbook", "customer excel workbooks"], ["report consumers"], "Completed report for review", flow_type="report_evidence")
    add_if_present(["report generation", "excel workbook", "customer excel workbooks"], ["sfs", "object storage"], "Optional secure SFS upload path", flow_type="optional_storage")

    if not edges and len(nodes) > 1:
        ordered = sorted(nodes, key=lambda node: _flow_rank(node.node_type, node.label))
        for index, (source, target) in enumerate(zip(ordered, ordered[1:]), start=1):
            edges.append(Edge(id=f"edge-flow-{index}", source=source.id, target=target.id, label="architecture flow"))
    _number_edges(edges)
    return edges


def _number_edges(edges: list[Edge]) -> None:
    for index, edge in enumerate(edges, start=1):
        edge.metadata.setdefault("sequence", index)
        edge.metadata.setdefault("flow_type", _infer_flow_type(edge))


def _infer_flow_type(edge: Edge) -> str:
    text = " ".join(
        item
        for item in [edge.label, edge.protocol or "", edge.security_control or "", edge.data_classification or ""]
        if item
    ).lower()
    if any(term in text for term in ["secret", "credential", "vault", "token"]):
        return "security_sensitive"
    if any(term in text for term in ["optional", "sfs", "object storage", "external storage"]):
        return "optional_storage"
    if any(term in text for term in ["report", "evidence", "workbook", "excel", "telemetry", "dashboard", "logs"]):
        return "report_evidence"
    if any(term in text for term in ["collect", "target", "metrics", "health", "scrape", "sql"]):
        return "target_collection"
    return "control"


def _find_node(labels: dict[str, Node], names: list[str]) -> Node | None:
    for name in names:
        for label, node in labels.items():
            if name in label:
                return node
    return None


def _flow_rank(node_type: str, label: str) -> int:
    lowered = f"{node_type} {label}".lower()
    for index, terms in enumerate(
        [
            ["user", "front door", "cdn", "edge"],
            ["gateway", "waf", "firewall"],
            ["api", "frontend", "backend", "kubernetes", "aks"],
            ["queue", "database", "postgres", "sql", "redis"],
            ["vault", "secret", "identity", "iam"],
            ["monitor", "prometheus", "grafana", "log", "telemetry"],
            ["github", "terraform", "deploy", "pipeline"],
        ]
    ):
        if any(term in lowered for term in terms):
            return index
    return 3


def _title_from_request(request: str, diagram_type: str) -> str:
    lowered = request.lower()
    if diagram_type == "enterprise":
        if "azure" in lowered:
            return "Azure Enterprise Architecture"
        if "aws" in lowered:
            return "AWS Enterprise Architecture"
        if "google cloud" in lowered or "gcp" in lowered:
            return "Google Cloud Enterprise Architecture"
        return "Enterprise Architecture"
    if diagram_type == "cloud":
        if "azure" in lowered:
            return "Azure Cloud Architecture"
        if "aws" in lowered:
            return "AWS Cloud Architecture"
        if "google cloud" in lowered or "gcp" in lowered:
            return "Google Cloud Architecture"
        return "Cloud Architecture"
    if diagram_type == "kubernetes":
        return "Kubernetes Architecture"
    if diagram_type == "cicd":
        return "CI/CD Workflow"
    if diagram_type == "security":
        return "Security Architecture"
    if diagram_type == "code":
        return "Code Workflow"
    clean = re.sub(r"\s+", " ", request).strip()
    clean = re.sub(r"^(create|generate|analyze)\s+", "", clean, flags=re.IGNORECASE)
    clean = clean[:90].rsplit(" ", 1)[0].rstrip(" .,")
    return clean[:1].upper() + clean[1:] if clean else f"{diagram_type.title()} Diagram"


def render_summary(diagram: Diagram) -> str:
    lines = [
        f"# {diagram.title}",
        "",
        f"- Diagram type: {diagram.diagram_type}",
        f"- Audience: {diagram.audience}",
        f"- Components: {len(diagram.nodes)}",
        f"- Flows: {len(diagram.edges)}",
        "",
        "## Components",
        *[f"- {node.label} ({node.node_type})" for node in diagram.nodes],
        "",
        "## Flows",
        *[f"- {edge.source} -> {edge.target}: {edge.label}" for edge in diagram.edges],
        "",
        "## Suggested Follow-Up Diagrams",
        "- Security and trust boundaries",
        "- Deployment and infrastructure topology",
        "- Observability and incident response flow",
        "- CI/CD and rollback flow",
    ]
    return "\n".join(lines) + "\n"


def render_assumptions(diagram: Diagram) -> str:
    lines = [
        "# Assumptions and Unknowns",
        "",
        "## Assumptions",
        *[f"- {item}" for item in diagram.assumptions],
        "",
        "## Unknowns",
        *[f"- {item}" for item in diagram.unknowns],
        "",
        "## Recommended Follow-Up Questions",
        "- Which environments, regions, subscriptions/accounts, and availability zones are in scope?",
        "- Which identity provider, RBAC model, and privileged access controls are authoritative?",
        "- What data classifications, ports, protocols, and compliance boundaries must be shown?",
        "- What SLOs, alert routes, runbooks, and rollback procedures should be represented?",
    ]
    return "\n".join(lines) + "\n"


def render_quality_checklist(diagram: Diagram, xml_issues: list[object], has_page_plan: bool = False) -> str:
    checks = [
        "Clear title and context statement",
        "Page plan separates executive and detail content",
        "Legend present",
        "Directional arrows with labels",
        "Boundary included when relevant",
        "Intermediate model generated before XML",
        "Draw.io XML generated with mxfile/mxGraphModel/root cells",
        "Secrets redacted",
        "Assumptions and unknowns documented",
        "Adversarial review performed",
    ]
    lines = ["# Quality Checklist", ""]
    for check in checks:
        lines.append(f"- [{'x' if _check_passes(check, diagram, xml_issues, has_page_plan) else ' '}] {check}")
    lines.extend(["", "## Model Quality Checks", *[f"- {item}" for item in diagram.quality_checks]])
    if xml_issues:
        lines.extend(["", "## XML Validation Issues", *[f"- {issue}" for issue in xml_issues]])
    return "\n".join(lines) + "\n"


def _check_passes(check: str, diagram: Diagram, xml_issues: list[object], has_page_plan: bool = False) -> bool:
    if check == "Page plan separates executive and detail content":
        return has_page_plan
    if check == "Legend present":
        return bool(diagram.legends)
    if check == "Boundary included when relevant":
        return bool(diagram.boundaries)
    if check == "Directional arrows with labels":
        return all(edge.label for edge in diagram.edges)
    if check == "Draw.io XML generated with mxfile/mxGraphModel/root cells":
        return not xml_issues
    return True


if __name__ == "__main__":
    raise SystemExit(main())

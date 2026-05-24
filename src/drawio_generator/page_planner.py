"""Page planning helpers for separating executive and detail diagram content."""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagram_model import Diagram, Edge, Node


@dataclass(frozen=True, slots=True)
class PagePlanPage:
    title: str
    purpose: str
    node_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PagePlan:
    diagram_title: str
    pages: list[PagePlanPage]
    quality_gates: list[str]


EXECUTIVE_NODE_LIMIT = 8


def build_page_plan(diagram: Diagram) -> PagePlan:
    """Build deterministic page recommendations from a single-page model."""

    nodes_by_id = {node.id: node for node in diagram.nodes}
    executive_nodes = _executive_nodes(diagram.nodes)
    detail_nodes = [node.id for node in diagram.nodes if _is_detail_node(node)]
    security_nodes = [node.id for node in diagram.nodes if _is_security_node(node)]
    data_nodes = [node.id for node in diagram.nodes if _is_data_node(node)]
    operations_nodes = [node.id for node in diagram.nodes if _is_operations_node(node)]

    executive_node_set = set(executive_nodes)
    detail_node_set = set(detail_nodes)
    security_node_set = set(security_nodes)
    data_node_set = set(data_nodes)
    operations_node_set = set(operations_nodes)

    pages = [
        PagePlanPage(
            title="Executive Overview",
            purpose="Show the main architecture path, ownership zones, trust boundaries, critical outputs, and optional handoffs.",
            node_ids=executive_nodes,
            edge_ids=[
                edge.id
                for edge in diagram.edges
                if edge.source in executive_node_set
                and edge.target in executive_node_set
                and _flow_type(edge) != "security_sensitive"
            ],
            notes=[
                "Use short numbered flow labels and keep full descriptions in the legend.",
                "Move runtime variables, role internals, inventories, and templates to detail pages.",
            ],
        ),
        PagePlanPage(
            title="Implementation Detail",
            purpose="Carry role stacks, templates, inventories, variables, controller workspace detail, and implementation mechanics.",
            node_ids=detail_nodes,
            edge_ids=[edge.id for edge in diagram.edges if edge.source in detail_node_set or edge.target in detail_node_set],
            notes=["Use compact stacks, matrices, or tables instead of dense text blocks."],
        ),
        PagePlanPage(
            title="Security and Trust Boundaries",
            purpose="Show trust boundaries, secret retrieval, privileged access, sensitive data, audit paths, and security ownership.",
            node_ids=security_nodes,
            edge_ids=[
                edge.id
                for edge in diagram.edges
                if _flow_type(edge) == "security_sensitive"
                or edge.source in security_node_set
                or edge.target in security_node_set
            ],
            notes=["No secrets in source control or reports; reports may contain sensitive configuration evidence."],
        ),
        PagePlanPage(
            title="Data and Evidence Flow",
            purpose="Show collected data, staged evidence, reports, workbooks, queues, databases, SFS, and optional storage handoffs.",
            node_ids=data_nodes,
            edge_ids=[
                edge.id
                for edge in diagram.edges
                if _flow_type(edge) in {"report_evidence", "optional_storage"}
                or edge.source in data_node_set
                or edge.target in data_node_set
            ],
            notes=["Represent data objects with database, queue, document, workbook, or object-storage shapes."],
        ),
        PagePlanPage(
            title="Operations and Follow-Up",
            purpose="Track observability, validation, unknowns, assumptions, follow-up diagrams, and operational review questions.",
            node_ids=operations_nodes,
            edge_ids=[
                edge.id
                for edge in diagram.edges
                if edge.source in operations_node_set or edge.target in operations_node_set
            ],
            notes=[
                "Use this page for monitoring, logs, health checks, runbooks, open questions, and known limits.",
                f"Assumptions: {len(diagram.assumptions)}; Unknowns: {len(diagram.unknowns)}.",
            ],
        ),
    ]

    return PagePlan(
        diagram_title=diagram.title,
        pages=pages,
        quality_gates=[
            "Page 1 should be understandable in about 30 seconds.",
            "Page 1 uses numbered edge labels with full descriptions in a legend.",
            "Detail pages carry variable lists, role internals, host inventories, and implementation mechanics.",
            "Trust boundaries and sensitive flows have an explicit security page.",
            "No secrets in source control or reports; reports may contain sensitive configuration evidence.",
        ],
    )


def render_page_plan(plan: PagePlan) -> str:
    lines = [
        "# Page Plan",
        "",
        f"- Diagram: {plan.diagram_title}",
        "",
        "## Quality Gates",
        *[f"- {gate}" for gate in plan.quality_gates],
        "",
    ]
    for page in plan.pages:
        lines.extend(
            [
                f"## {page.title}",
                "",
                f"- Purpose: {page.purpose}",
                f"- Nodes: {_format_ids(page.node_ids)}",
                f"- Edges: {_format_ids(page.edge_ids)}",
                *[f"- Note: {note}" for note in page.notes],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _executive_nodes(nodes: list[Node]) -> list[str]:
    candidates = [node for node in nodes if not _is_detail_node(node) and not _is_security_node(node)]
    return [node.id for node in sorted(candidates, key=_executive_rank)[:EXECUTIVE_NODE_LIMIT]]


def _executive_rank(node: Node) -> tuple[int, str]:
    text = _node_text(node)
    if any(term in text for term in ["github", "repository", "source control"]):
        return (0, node.id)
    if any(term in text for term in ["tower", "awx", "ansible", "controller", "orchestration"]):
        return (1, node.id)
    if any(term in text for term in ["target", "linux", "windows", "server", "postgres", "rabbitmq", "iis", "database", "queue"]):
        return (2, node.id)
    if any(term in text for term in ["collected", "staged", "workspace", "data"]):
        return (3, node.id)
    if any(term in text for term in ["report", "workbook", "excel", "evidence"]):
        return (4, node.id)
    if any(term in text for term in ["sfs", "object storage", "external storage"]):
        return (5, node.id)
    if any(term in text for term in ["consumer", "reviewer", "engineer", "auditor"]):
        return (6, node.id)
    return (7, node.id)


def _is_detail_node(node: Node) -> bool:
    detail_level = str(node.metadata.get("detail_level", "")).lower()
    text = _node_text(node)
    return detail_level in {"detail", "deep"} or any(
        term in text
        for term in [
            "role execution",
            "runtime input",
            "variable",
            "inventory",
            "template",
            "group_vars",
            "playbook",
            "repository contents",
            "job template",
        ]
    )


def _is_security_node(node: Node) -> bool:
    text = _node_text(node)
    return node.node_type.lower() in {"secret", "security", "identity", "waf", "firewall"} or any(
        term in text for term in ["vault", "secret", "credential", "rbac", "identity", "security boundary"]
    )


def _is_data_node(node: Node) -> bool:
    text = _node_text(node)
    return node.node_type.lower() in {"database", "queue", "cache", "data", "report", "workbook", "object_storage"} or any(
        term in text for term in ["data", "report", "workbook", "excel", "evidence", "sfs", "object storage"]
    )


def _is_operations_node(node: Node) -> bool:
    text = _node_text(node)
    return node.node_type.lower() in {"monitoring", "logging", "dashboard"} or any(
        term in text for term in ["monitor", "log", "metric", "grafana", "prometheus", "zabbix", "health check", "runbook"]
    )


def _flow_type(edge: Edge) -> str:
    flow_type = edge.metadata.get("flow_type")
    if isinstance(flow_type, str):
        return flow_type
    text = " ".join([edge.label, edge.protocol or "", edge.security_control or "", edge.data_classification or ""]).lower()
    if any(term in text for term in ["secret", "credential", "vault", "token"]):
        return "security_sensitive"
    if any(term in text for term in ["optional", "sfs", "object storage", "external storage"]):
        return "optional_storage"
    if any(term in text for term in ["report", "evidence", "workbook", "excel", "data"]):
        return "report_evidence"
    if any(term in text for term in ["collect", "target", "health", "check"]):
        return "target_collection"
    return "control"


def _node_text(node: Node) -> str:
    return f"{node.node_type} {node.label} {node.icon or ''}".lower()


def _format_ids(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "none"

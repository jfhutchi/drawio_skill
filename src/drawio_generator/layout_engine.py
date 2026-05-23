"""Deterministic layout heuristics for enterprise diagrams."""

from __future__ import annotations

from copy import deepcopy

from .diagram_model import Boundary, Diagram, Node


VERTICAL_LAYERS = [
    "users",
    "edge",
    "application",
    "data",
    "platform",
    "security",
    "observability",
    "operations",
]

HORIZONTAL_TYPES = {"cicd", "workflow", "sequence", "code"}


def infer_layer(node: Node) -> str:
    node_type = (node.node_type or "").lower()
    label = node.label.lower()
    if node_type in {"actor", "user"} or "user" in label:
        return "users"
    if node_type in {"cdn", "gateway", "waf", "firewall", "network"}:
        return "edge"
    if node_type in {"database", "cache", "queue", "data"} or any(term in label for term in ["postgres", "sql", "redis", "queue", "kafka", "rabbitmq"]):
        return "data"
    if node_type in {"kubernetes", "container", "server", "terraform", "ansible"}:
        return "platform"
    if node_type in {"identity", "secret", "security"} or any(term in label for term in ["vault", "iam", "sso", "mfa", "rbac", "pam", "siem"]):
        return "security"
    if node_type in {"monitoring", "logging", "dashboard"} or any(term in label for term in ["prometheus", "grafana", "logs", "metrics", "traces", "monitor"]):
        return "observability"
    if node_type in {"process", "deployment", "repository", "artifact"}:
        return "operations"
    return "application"


def apply_layout(diagram: Diagram) -> Diagram:
    """Return a laid-out copy of the model without mutating the input."""

    laid_out = deepcopy(diagram)
    horizontal = laid_out.diagram_type.lower() in HORIZONTAL_TYPES or laid_out.direction.lower() == "left-to-right"

    for node in laid_out.nodes:
        if not node.layer:
            node.layer = infer_layer(node)

    if horizontal:
        _layout_horizontal(laid_out)
    else:
        _layout_vertical(laid_out)

    _layout_boundaries(laid_out)
    return laid_out


def _layout_vertical(diagram: Diagram) -> None:
    layers = diagram.layers or VERTICAL_LAYERS
    grouped = {layer: [node for node in diagram.nodes if node.layer == layer] for layer in layers}
    unknown_layer_nodes = [node for node in diagram.nodes if node.layer not in grouped]
    if unknown_layer_nodes:
        grouped["application"] = [*grouped.get("application", []), *unknown_layer_nodes]

    y = 150
    for layer in layers:
        nodes = grouped.get(layer, [])
        if not nodes:
            continue
        total_width = sum(node.width for node in nodes) + max(0, len(nodes) - 1) * 40
        x = max(80, 480 - total_width // 2)
        for node in nodes:
            node.x = x
            node.y = y
            x += node.width + 40
        y += 130


def _layout_horizontal(diagram: Diagram) -> None:
    x = 90
    y_base = 230
    for index, node in enumerate(diagram.nodes):
        node.x = x
        node.y = y_base + (index % 2) * 105
        x += node.width + 55


def _layout_boundaries(diagram: Diagram) -> None:
    if not diagram.boundaries:
        return

    for boundary in diagram.boundaries:
        member_nodes = [node for node in diagram.nodes if node.group == boundary.id]
        if member_nodes:
            min_x = min((node.x or 0) for node in member_nodes) - 40
            min_y = min((node.y or 0) for node in member_nodes) - 55
            max_x = max((node.x or 0) + node.width for node in member_nodes) + 40
            max_y = max((node.y or 0) + node.height for node in member_nodes) + 40
            boundary.x = min_x
            boundary.y = min_y
            boundary.width = max(260, max_x - min_x)
            boundary.height = max(170, max_y - min_y)
        else:
            boundary.x = boundary.x if boundary.x is not None else 40
            boundary.y = boundary.y if boundary.y is not None else 105

"""Validation and redaction helpers for draw.io outputs."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .diagram_model import Diagram
from .icon_registry import get_icon_style


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: str
    message: str
    item_id: str | None = None


SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", re.MULTILINE),
        "-----BEGIN PRIVATE KEY-----\nREDACTED\n-----END PRIVATE KEY-----",
    ),
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}"), r"\1REDACTED"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[A-Za-z0-9._~+/=-]{8,}"), r"\1REDACTED"),
    (re.compile(r"(?i)(token\s*[:=]\s*)[A-Za-z0-9._~+/=-]{8,}"), r"\1REDACTED"),
    (re.compile(r"(?i)(password\s*[:=]\s*)[^\s;,\"]+"), r"\1REDACTED"),
    (re.compile(r"(gh[pousr]_[A-Za-z0-9_]{20,})"), "REDACTED"),
    (re.compile(r"([a-z][a-z0-9+.-]*://[^:\s/@]+:)(?!REDACTED@)([^@\s]+)(@)", re.IGNORECASE), r"\1REDACTED\3"),
]


def redact_sensitive_text(text: str) -> str:
    """Redact common secrets while preserving architecture-relevant context."""

    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def contains_secret(text: str) -> bool:
    """Return True if the text appears to contain an unredacted secret."""

    return redact_sensitive_text(text) != text


def validate_model(diagram: Diagram) -> list[ValidationIssue]:
    """Validate hard model invariants before XML generation."""

    issues: list[ValidationIssue] = []
    ids = diagram.all_ids()
    seen: set[str] = set()
    for item_id in ids:
        if not item_id:
            issues.append(ValidationIssue("error", "Empty id found"))
            continue
        if item_id in seen:
            issues.append(ValidationIssue("error", f"Duplicate id: {item_id}", item_id))
        seen.add(item_id)

    boundary_ids = diagram.boundary_ids()
    node_ids = diagram.node_ids()
    for boundary in diagram.boundaries:
        if not boundary.label.strip():
            issues.append(ValidationIssue("error", "Boundary has empty label", boundary.id))
        if contains_secret(boundary.label):
            issues.append(ValidationIssue("error", "Boundary label contains an unredacted secret", boundary.id))

    for node in diagram.nodes:
        if not node.label.strip():
            issues.append(ValidationIssue("error", "Node has empty label", node.id))
        if node.group and node.group not in boundary_ids:
            issues.append(ValidationIssue("error", f"Node references missing boundary: {node.group}", node.id))
        if contains_secret(" ".join(filter(None, [node.label, node.description or "", str(node.metadata)]))):
            issues.append(ValidationIssue("error", "Node contains an unredacted secret", node.id))

    for edge in diagram.edges:
        if edge.source not in node_ids:
            issues.append(ValidationIssue("error", f"Edge references missing source: {edge.source}", edge.id))
        if edge.target not in node_ids:
            issues.append(ValidationIssue("error", f"Edge references missing target: {edge.target}", edge.id))
        if not edge.label.strip():
            issues.append(ValidationIssue("warning", "Edge has empty label", edge.id))
        if contains_secret(" ".join(filter(None, [edge.label, edge.protocol or "", edge.security_control or "", str(edge.metadata)]))):
            issues.append(ValidationIssue("error", "Edge contains an unredacted secret", edge.id))

    issues.extend(validate_vendor_shape_accuracy(diagram))
    return issues


_VENDOR_HINT_TERMS: tuple[tuple[str, str], ...] = (
    ("azure", "azure"),
    ("aws", "aws"),
    ("amazon", "aws"),
    ("google cloud", "gcp"),
    ("gcp", "gcp"),
    ("kubernetes", "kubernetes"),
)


def validate_vendor_shape_accuracy(diagram: Diagram) -> list[ValidationIssue]:
    """Warn when a node's label clearly names a vendor service but resolves to
    a generic fallback shape.

    This surfaces coverage gaps in the built-in vendor stencil registry to
    reviewers before delivery, so they can either rename the node, add a new
    alias, or accept the gap consciously. Only nodes whose label or icon
    contains an unambiguous vendor hint are checked; generic shapes for
    non-vendor nodes are left alone.
    """

    issues: list[ValidationIssue] = []
    for node in diagram.nodes:
        text = " ".join(filter(None, [node.label, node.icon or "", node.technology or ""])).lower()
        vendor = next((vendor for hint, vendor in _VENDOR_HINT_TERMS if hint in text), None)
        if vendor is None:
            continue
        style = get_icon_style(node.node_type, node.icon, node.label)
        if style.category == "fallback":
            issues.append(
                ValidationIssue(
                    "warning",
                    (
                        f"Node looks like a {vendor.upper()} service but resolved to a generic fallback shape. "
                        "Add an alias in builtin_vendor_shapes.py or rename the label to a recognized service."
                    ),
                    node.id,
                )
            )
    return issues


def validate_drawio_xml(xml_text: str) -> list[ValidationIssue]:
    """Validate diagrams.net XML structure and references."""

    issues: list[ValidationIssue] = []
    if contains_secret(xml_text):
        issues.append(ValidationIssue("error", "XML contains an unredacted secret"))

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return [ValidationIssue("error", f"XML is not parseable: {exc}")]

    if root.tag != "mxfile":
        issues.append(ValidationIssue("error", "Root element must be mxfile"))

    diagrams = root.findall("diagram")
    if not diagrams:
        issues.append(ValidationIssue("error", "Missing diagram element"))
        return issues

    for diagram_index, diagram in enumerate(diagrams, start=1):
        graph_model = diagram.find("mxGraphModel")
        if graph_model is None:
            issues.append(ValidationIssue("error", "Missing mxGraphModel", diagram.attrib.get("name")))
            continue

        cells = graph_model.findall(".//mxCell")
        cell_ids = [cell.attrib.get("id", "") for cell in cells]
        if "0" not in cell_ids:
            issues.append(ValidationIssue("error", f'Diagram {diagram_index} missing root cell id="0"'))
        if "1" not in cell_ids:
            issues.append(ValidationIssue("error", f'Diagram {diagram_index} missing root cell id="1"'))

        seen: set[str] = set()
        for cell_id in cell_ids:
            if not cell_id:
                issues.append(ValidationIssue("error", f"Diagram {diagram_index} cell has empty id"))
                continue
            if cell_id in seen:
                issues.append(ValidationIssue("error", f"Duplicate mxCell id on diagram {diagram_index}: {cell_id}", cell_id))
            seen.add(cell_id)

        vertex_or_edge = [cell for cell in cells if cell.attrib.get("vertex") == "1" or cell.attrib.get("edge") == "1"]
        for cell in vertex_or_edge:
            if cell.find("mxGeometry") is None:
                issues.append(ValidationIssue("error", f"Diagram {diagram_index} mxCell is missing mxGeometry", cell.attrib.get("id")))

        id_set = set(cell_ids)
        for cell in graph_model.findall(".//mxCell[@edge='1']"):
            source = cell.attrib.get("source")
            target = cell.attrib.get("target")
            if source not in id_set:
                issues.append(ValidationIssue("error", f"Diagram {diagram_index} edge references missing source: {source}", cell.attrib.get("id")))
            if target not in id_set:
                issues.append(ValidationIssue("error", f"Diagram {diagram_index} edge references missing target: {target}", cell.attrib.get("id")))

    return issues

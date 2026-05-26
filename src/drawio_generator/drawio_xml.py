"""Generate human-readable diagrams.net XML from the intermediate model."""

from __future__ import annotations

from copy import deepcopy
import xml.etree.ElementTree as ET
from typing import Any

from .diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from .icon_registry import get_icon_style
from .layout_engine import apply_layout


def generate_drawio_xml(diagram: Diagram) -> str:
    """Generate uncompressed draw.io XML for a single-page diagram."""

    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "enterprise-drawio-diagrammer"})
    _add_diagram_page(mxfile, diagram, _page_name(diagram.title))
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", short_empty_elements=True)


def generate_multipage_drawio_xml(diagram: Diagram, page_plan: Any) -> str:
    """Generate uncompressed multi-page draw.io XML from a page plan.

    Page 1 is the executive architecture view. Later pages are filtered by
    the page-plan node and edge lists so details, security, and evidence flows
    do not overload the executive page. Cell IDs are page-prefixed to keep
    cross-page XML validation deterministic while each page remains readable.
    """

    pages = list(getattr(page_plan, "pages", []))
    if not pages:
        return generate_drawio_xml(diagram)

    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "enterprise-drawio-diagrammer"})
    emitted = 0
    for index, plan_page in enumerate(pages, start=1):
        page_diagram = _diagram_for_plan_page(diagram, plan_page)
        if emitted > 0 and not page_diagram.nodes and not page_diagram.edges:
            continue
        emitted += 1
        laid_out = apply_layout(page_diagram)
        laid_out.metadata = {**laid_out.metadata, "_laid_out": True}
        _renumber_edges_per_page(laid_out)
        prefix = f"p{emitted}_"
        prefixed = _prefix_diagram_ids(laid_out, prefix)
        _add_diagram_page(mxfile, prefixed, _page_name(str(getattr(plan_page, "title", f"Page {emitted}"))))
    if emitted == 0:
        return generate_drawio_xml(diagram)
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", short_empty_elements=True)


def _renumber_edges_per_page(diagram: Diagram) -> None:
    """Reassign edge sequence numbers so each page reads 1, 2, 3, ..."""

    for index, edge in enumerate(diagram.edges, start=1):
        edge.metadata = {**edge.metadata, "sequence": index}


def _add_diagram_page(mxfile: ET.Element, diagram: Diagram, page_name: str) -> None:
    laid_out = diagram if diagram.metadata.get("_laid_out") else apply_layout(diagram)
    page_width, page_height = _page_size(laid_out)
    page = ET.SubElement(mxfile, "diagram", {"name": page_name})
    model = ET.SubElement(
        page,
        "mxGraphModel",
        {
            "dx": "1200",
            "dy": "900",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(page_width),
            "pageHeight": str(page_height),
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    _add_title(root, laid_out)
    for boundary in laid_out.boundaries:
        _add_boundary(root, boundary)
    for node in laid_out.nodes:
        _add_node(root, node)
    if laid_out.legends or _flow_legend_rows(laid_out.edges):
        _add_legend(root, laid_out.legends, laid_out.edges, laid_out)
    for edge in laid_out.edges:
        _add_edge(root, edge)
    _add_flow_badges(root, laid_out)
    _add_page_notes(root, laid_out, page_height)


def _diagram_for_plan_page(diagram: Diagram, plan_page: Any) -> Diagram:
    node_lookup = {node.id: node for node in diagram.nodes}
    edge_lookup = {edge.id: edge for edge in diagram.edges}
    selected_edge_ids = [edge_id for edge_id in getattr(plan_page, "edge_ids", []) if edge_id in edge_lookup]
    selected_node_ids = {node_id for node_id in getattr(plan_page, "node_ids", []) if node_id in node_lookup}

    for edge_id in selected_edge_ids:
        edge = edge_lookup[edge_id]
        selected_node_ids.add(edge.source)
        selected_node_ids.add(edge.target)

    nodes = [deepcopy(node) for node in diagram.nodes if node.id in selected_node_ids]
    edges = [deepcopy(edge_lookup[edge_id]) for edge_id in selected_edge_ids]
    included_groups = {node.group for node in nodes if node.group}
    boundaries = [deepcopy(boundary) for boundary in diagram.boundaries if boundary.id in included_groups]
    title = str(getattr(plan_page, "title", diagram.title))
    purpose = str(getattr(plan_page, "purpose", ""))
    notes = list(getattr(plan_page, "notes", []))
    page_diagram = Diagram(
        title=title,
        subtitle=f"{diagram.title} — {purpose}" if purpose else diagram.title,
        diagram_type=diagram.diagram_type,
        audience=diagram.audience,
        direction=diagram.direction,
        layout_strategy=diagram.layout_strategy,
        layers=list(diagram.layers),
        groups=list(diagram.groups),
        boundaries=boundaries,
        nodes=nodes,
        edges=edges,
        legends=deepcopy(diagram.legends),
        annotations=deepcopy(diagram.annotations),
        assumptions=list(diagram.assumptions),
        unknowns=list(diagram.unknowns),
        sources=list(diagram.sources),
        quality_checks=list(diagram.quality_checks),
        metadata={**diagram.metadata, "page_notes": notes},
    )
    return page_diagram


def _prefix_diagram_ids(diagram: Diagram, prefix: str) -> Diagram:
    prefixed = deepcopy(diagram)
    for boundary in prefixed.boundaries:
        boundary.id = f"{prefix}{boundary.id}"
    for node in prefixed.nodes:
        node.id = f"{prefix}{node.id}"
        if node.group:
            node.group = f"{prefix}{node.group}"
    for edge in prefixed.edges:
        edge.id = f"{prefix}{edge.id}"
        edge.source = f"{prefix}{edge.source}"
        edge.target = f"{prefix}{edge.target}"
    prefixed.metadata = {**prefixed.metadata, "cell_prefix": prefix}
    return prefixed


def _page_size(diagram: Diagram) -> tuple[int, int]:
    max_x = 1169
    max_y = 827
    for boundary in diagram.boundaries:
        max_x = max(max_x, (boundary.x or 0) + boundary.width + 80)
        max_y = max(max_y, (boundary.y or 0) + boundary.height + 80)
    for node in diagram.nodes:
        max_x = max(max_x, (node.x or 0) + node.width + 80)
        max_y = max(max_y, (node.y or 0) + node.height + 80)
    legend_rows = ["Legend", *diagram.legends, *_flow_legend_rows(diagram.edges)]
    if len(legend_rows) > 1:
        max_x = max(max_x, 1300)
        max_y = max(max_y, 105 + len(legend_rows) * 24)
    page_notes = diagram.metadata.get("page_notes")
    if isinstance(page_notes, list) and page_notes:
        max_y = max(max_y, 185 + len(page_notes) * 24)
    return max_x, max_y


def _page_name(title: str) -> str:
    clean = "".join(char for char in title if char.isalnum() or char in {" ", "-", "_"}).strip()
    return (clean or "Page-1")[:60]


def _add_title(root: ET.Element, diagram: Diagram) -> None:
    title_value = diagram.title if not diagram.subtitle else f"{diagram.title}\n{diagram.subtitle}"
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{diagram.metadata.get('cell_prefix', '')}__title",
            "value": title_value,
            "style": "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=20;fontStyle=1;fontColor=#1f2933;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": "40", "y": "30", "width": "850", "height": "60", "as": "geometry"})


def _add_boundary(root: ET.Element, boundary: Boundary) -> None:
    style = _boundary_style(boundary)
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": boundary.id,
            "value": boundary.label,
            "style": style,
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(
        cell,
        "mxGeometry",
        {
            "x": str(boundary.x if boundary.x is not None else 40),
            "y": str(boundary.y if boundary.y is not None else 110),
            "width": str(boundary.width),
            "height": str(boundary.height),
            "as": "geometry",
        },
    )


def _add_node(root: ET.Element, node: Node) -> None:
    style = get_icon_style(node.node_type, node.icon, node.label).drawio_style
    if node.risk_level and node.risk_level.lower() in {"high", "critical"}:
        style += "strokeColor=#b85450;strokeWidth=2;"
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": node.id,
            "value": node.label,
            "style": style,
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(
        cell,
        "mxGeometry",
        {
            "x": str(node.x if node.x is not None else 80),
            "y": str(node.y if node.y is not None else 160),
            "width": str(node.width),
            "height": str(node.height),
            "as": "geometry",
        },
    )


def _add_edge(root: ET.Element, edge: Edge) -> None:
    style = edge.style or _edge_style(edge)
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": edge.id,
            "value": _edge_value(edge),
            "style": style,
            "edge": "1",
            "parent": "1",
            "source": edge.source,
            "target": edge.target,
        },
    )
    ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})


def _add_flow_badges(root: ET.Element, diagram: Diagram) -> None:
    nodes = {node.id: node for node in diagram.nodes}
    cell_prefix = str(diagram.metadata.get("cell_prefix", ""))
    for edge in diagram.edges:
        sequence = edge.metadata.get("sequence")
        source = nodes.get(edge.source)
        target = nodes.get(edge.target)
        if sequence is None or source is None or target is None:
            continue
        _add_flow_badge(root, edge, source, target, str(sequence), cell_prefix)


def _add_flow_badge(root: ET.Element, edge: Edge, source: Node, target: Node, value: str, cell_prefix: str = "") -> None:
    size = 28
    source_x = (source.x or 0) + source.width
    source_y = (source.y or 0) + source.height // 2
    target_x = target.x or 0
    target_y = (target.y or 0) + target.height // 2
    x = max(30, (source_x + target_x) // 2 - size // 2)
    y = max(30, (source_y + target_y) // 2 - size // 2)
    fill = _flow_color(edge)
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{cell_prefix}__badge_{edge.id}",
            "value": value,
            "style": (
                "ellipse;whiteSpace=wrap;html=1;aspect=fixed;"
                f"fillColor={fill};strokeColor=#ffffff;fontColor=#ffffff;fontStyle=1;fontSize=13;"
                "align=center;verticalAlign=middle;spacing=0;"
            ),
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(size), "height": str(size), "as": "geometry"})


def _add_legend(root: ET.Element, legends: list[LegendItem], edges: list[Edge], diagram: Diagram | None = None) -> None:
    rows = ["Legend", *[f"{item.label}: {item.meaning}" for item in legends], *_flow_legend_rows(edges)]
    value = "\n".join(rows)
    cell_prefix = "" if diagram is None else str(diagram.metadata.get("cell_prefix", ""))
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{cell_prefix}__legend",
            "value": value,
            "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#adb5bd;fontColor=#343a40;align=left;spacingLeft=8;verticalAlign=top;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": "900", "y": "30", "width": "320", "height": str(45 + len(rows) * 24), "as": "geometry"})


def _add_page_notes(root: ET.Element, diagram: Diagram, page_height: int) -> None:
    notes = diagram.metadata.get("page_notes")
    if not isinstance(notes, list) or not notes:
        return
    value = "Page notes\n" + "\n".join(str(note) for note in notes)
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{diagram.metadata.get('cell_prefix', '')}__page_notes",
            "value": value,
            "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8f9fa;strokeColor=#adb5bd;fontColor=#343a40;align=left;spacingLeft=8;verticalAlign=top;fontSize=12;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": "40", "y": str(max(120, page_height - 105)), "width": "760", "height": str(45 + len(notes) * 22), "as": "geometry"})



def _boundary_style(boundary: Boundary) -> str:
    boundary_type = boundary.boundary_type.lower()
    stroke = "#dc2626" if boundary_type in {"trust", "security"} else "#6c757d"
    fill = "#fffafa" if boundary_type in {"trust", "security"} else "#f8fbff"
    return (
        "rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=8 4;"
        f"fillColor={fill};strokeColor={stroke};verticalAlign=top;align=left;"
        "spacingTop=10;spacingLeft=12;fontStyle=1;fontColor=#343a40;"
    )


def _edge_style(edge: Edge) -> str:
    flow_type = _flow_type(edge)
    stroke = _flow_color(edge)
    dashed = "dashed=1;dashPattern=8 4;" if flow_type in {"optional_storage", "security_sensitive"} else ""
    return (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
        f"html=1;endArrow=block;endFill=1;strokeColor={stroke};fontColor=#343a40;strokeWidth=2;"
        f"{dashed}"
    )


def _flow_color(edge: Edge) -> str:
    flow_type = _flow_type(edge)
    return {
        "control": "#4f46e5",
        "target_collection": "#2f9e44",
        "report_evidence": "#d97706",
        "optional_storage": "#6c757d",
        "security_sensitive": "#dc2626",
    }.get(flow_type, "#495057")


def _edge_value(edge: Edge) -> str:
    display_label = edge.metadata.get("display_label")
    if display_label is not None:
        return str(display_label)
    sequence = edge.metadata.get("sequence")
    if sequence is not None:
        return str(sequence)
    return edge.label


def _flow_legend_rows(edges: list[Edge]) -> list[str]:
    rows: list[str] = []
    for edge in edges:
        sequence = edge.metadata.get("sequence")
        if sequence is not None:
            rows.append(f"{sequence}: {edge.label}")
    return rows


def _flow_type(edge: Edge) -> str:
    flow_type = edge.metadata.get("flow_type")
    if isinstance(flow_type, str) and flow_type:
        return flow_type

    text = " ".join(
        item
        for item in [edge.label, edge.protocol or "", edge.security_control or "", edge.data_classification or ""]
        if item
    ).lower()
    if any(term in text for term in ["secret", "credential", "vault", "token"]):
        return "security_sensitive"
    if any(term in text for term in ["optional", "sfs", "object storage", "external storage"]):
        return "optional_storage"
    if any(term in text for term in ["report", "evidence", "workbook", "csv", "excel"]):
        return "report_evidence"
    if any(term in text for term in ["collect", "target", "health", "check"]):
        return "target_collection"
    if any(term in text for term in ["sync", "launch", "orchestrat", "control", "plan/apply"]):
        return "control"
    return "default"

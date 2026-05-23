"""Generate human-readable diagrams.net XML from the intermediate model."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from .icon_registry import get_icon_style
from .layout_engine import apply_layout


def generate_drawio_xml(diagram: Diagram) -> str:
    """Generate uncompressed draw.io XML for a single-page diagram."""

    laid_out = apply_layout(diagram)
    page_width, page_height = _page_size(laid_out)
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "enterprise-drawio-diagrammer"})
    page = ET.SubElement(mxfile, "diagram", {"name": _page_name(laid_out.title)})
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
    if laid_out.legends:
        _add_legend(root, laid_out.legends)
    for edge in laid_out.edges:
        _add_edge(root, edge)

    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", short_empty_elements=True)


def _page_size(diagram: Diagram) -> tuple[int, int]:
    max_x = 1169
    max_y = 827
    for boundary in diagram.boundaries:
        max_x = max(max_x, (boundary.x or 0) + boundary.width + 80)
        max_y = max(max_y, (boundary.y or 0) + boundary.height + 80)
    for node in diagram.nodes:
        max_x = max(max_x, (node.x or 0) + node.width + 80)
        max_y = max(max_y, (node.y or 0) + node.height + 80)
    if diagram.legends:
        max_x = max(max_x, 1180)
        max_y = max(max_y, 160 + len(diagram.legends) * 30)
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
            "id": "__title",
            "value": title_value,
            "style": "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=20;fontStyle=1;fontColor=#1f2933;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": "40", "y": "30", "width": "850", "height": "60", "as": "geometry"})


def _add_boundary(root: ET.Element, boundary: Boundary) -> None:
    style = (
        "rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=8 4;"
        "fillColor=#ffffff;strokeColor=#6c757d;verticalAlign=top;align=left;"
        "spacingTop=10;spacingLeft=12;fontStyle=1;fontColor=#495057;"
    )
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
    style = get_icon_style(node.node_type, node.icon).drawio_style
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
    style = edge.style or (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
        "html=1;endArrow=block;endFill=1;strokeColor=#495057;fontColor=#343a40;"
    )
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": edge.id,
            "value": edge.label,
            "style": style,
            "edge": "1",
            "parent": "1",
            "source": edge.source,
            "target": edge.target,
        },
    )
    ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})


def _add_legend(root: ET.Element, legends: list[LegendItem]) -> None:
    rows = ["Legend", *[f"{item.label}: {item.meaning}" for item in legends]]
    value = "\n".join(rows)
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": "__legend",
            "value": value,
            "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#adb5bd;fontColor=#343a40;align=left;spacingLeft=8;verticalAlign=top;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": "900", "y": "30", "width": "230", "height": str(45 + len(legends) * 30), "as": "geometry"})

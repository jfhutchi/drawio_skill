"""Generate human-readable diagrams.net XML from the intermediate model."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from typing import Any

from .diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from .icon_registry import get_icon_style
from .layout_engine import apply_layout, _snap_down, _snap_up


LEGEND_WIDTH = 320
LEGEND_FONT_SIZE = 12
NOTES_WIDTH = 760
FURNITURE_GAP = 40
SIDE_LEGEND_BUDGET = 1654  # A3 landscape width; beyond this the legend drops to the bottom band


@dataclass(frozen=True, slots=True)
class FurnitureBox:
    """Geometry and text for one page-furniture element (title, legend, notes)."""

    x: int
    y: int
    width: int
    height: int
    text: str


@dataclass(frozen=True, slots=True)
class PageFurniture:
    title: FurnitureBox
    legend: FurnitureBox | None
    notes: FurnitureBox | None


def _content_bbox(diagram: Diagram) -> tuple[int, int, int, int]:
    """Bounding box of laid-out content: boundaries, nodes, and planned routes."""

    xs: list[float] = []
    ys: list[float] = []
    for boundary in diagram.boundaries:
        if boundary.x is None or boundary.y is None:
            continue
        xs.extend((boundary.x, boundary.x + boundary.width))
        ys.extend((boundary.y, boundary.y + boundary.height))
    for node in diagram.nodes:
        xs.extend((node.x or 0, (node.x or 0) + node.width))
        ys.extend((node.y or 0, (node.y or 0) + node.height))
    for edge in diagram.edges:
        route = edge.metadata.get("route")
        if isinstance(route, list):
            for point in route:
                xs.append(float(point[0]))
                ys.append(float(point[1]))
    if not xs:
        return (40, 120, 1080, 700)
    return (_snap_down(min(xs)), _snap_down(min(ys)), _snap_up(max(xs)), _snap_up(max(ys)))


def _estimate_wrapped_lines(text: str, box_width: int, font_size: int) -> int:
    """Line-count estimate using the shared 0.6 * fontSize glyph width metric."""

    max_chars = max(4, int(box_width / (0.6 * font_size)))
    lines = 0
    for raw_line in text.split("\n"):
        lines += max(1, -(-len(raw_line) // max_chars))
    return lines


def compute_furniture(diagram: Diagram) -> PageFurniture:
    """Place title, legend, and page notes from the laid-out content extents.

    No fixed coordinates: the title band spans the content width at the top,
    the legend sits right of the content when it fits the page budget and
    drops into the bottom band beside the notes otherwise. Single source of
    truth shared by the XML emitter and the preview renderer.
    """

    min_x, min_y, max_x, max_y = _content_bbox(diagram)
    title_value = diagram.title if not diagram.subtitle else f"{diagram.title}\n{diagram.subtitle}"
    title = FurnitureBox(min_x, 30, max(400, max_x - min_x), 60, title_value)

    legend_rows = [
        "Legend",
        *[f"{item.label}: {item.meaning}" for item in diagram.legends],
        *_flow_legend_rows(diagram.edges),
    ]
    legend_text = "\n".join(legend_rows)
    legend_height = 20 + sum(
        _estimate_wrapped_lines(row, LEGEND_WIDTH - 16, LEGEND_FONT_SIZE) for row in legend_rows
    ) * 22
    legend_height = _snap_up(legend_height)

    notes_lines = [str(note) for note in diagram.metadata.get("page_notes") or [] if str(note).strip()]
    bottom_y = _snap_up(max_y + FURNITURE_GAP)

    legend: FurnitureBox | None = None
    legend_at_side = False
    if len(legend_rows) > 1:
        side_x = _snap_up(max_x + FURNITURE_GAP)
        legend_at_side = side_x + LEGEND_WIDTH + FURNITURE_GAP <= SIDE_LEGEND_BUDGET
        if legend_at_side:
            legend = FurnitureBox(side_x, max(30, min_y), LEGEND_WIDTH, legend_height, legend_text)

    notes: FurnitureBox | None = None
    if notes_lines:
        notes_text = "Page notes\n" + "\n".join(notes_lines)
        notes_height = _snap_up(
            20 + sum(_estimate_wrapped_lines(line, NOTES_WIDTH - 16, LEGEND_FONT_SIZE) for line in ["Page notes", *notes_lines]) * 22
        )
        notes = FurnitureBox(min_x, bottom_y, NOTES_WIDTH, notes_height, notes_text)

    if len(legend_rows) > 1 and not legend_at_side:
        legend_x = min_x + NOTES_WIDTH + FURNITURE_GAP if notes is not None else min_x
        legend = FurnitureBox(legend_x, bottom_y, LEGEND_WIDTH, legend_height, legend_text)

    return PageFurniture(title, legend, notes)


def build_page_diagrams(diagram: Diagram, page_plan: Any) -> list[tuple[str, Diagram]]:
    """Return (page_name, laid-out id-prefixed Diagram) pairs for each emitted page.

    This is the same page sequence ``generate_multipage_drawio_xml`` emits, so
    the preview renderer and any model-level QA see exactly what the XML will
    contain. Falls back to a single laid-out page when the plan is empty.
    """

    pages = list(getattr(page_plan, "pages", []))
    built: list[tuple[str, Diagram]] = []
    emitted = 0
    for plan_page in pages:
        page_diagram = _diagram_for_plan_page(diagram, plan_page)
        if emitted > 0 and not page_diagram.nodes and not page_diagram.edges:
            continue
        emitted += 1
        laid_out = apply_layout(page_diagram)
        laid_out.metadata = {**laid_out.metadata, "_laid_out": True}
        _renumber_edges_per_page(laid_out)
        prefix = f"p{emitted}_"
        prefixed = _prefix_diagram_ids(laid_out, prefix)
        built.append((_page_name(str(getattr(plan_page, "title", f"Page {emitted}"))), prefixed))
    if not built:
        laid_out = apply_layout(diagram)
        laid_out.metadata = {**laid_out.metadata, "_laid_out": True}
        built.append((_page_name(diagram.title), laid_out))
    return built


def generate_drawio_xml(diagram: Diagram) -> str:
    """Generate uncompressed draw.io XML for a single-page diagram."""

    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "enterprise-drawio-diagrammer"})
    _add_diagram_page(mxfile, diagram, _page_name(diagram.title))
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", short_empty_elements=True)


def generate_multipage_drawio_xml(
    diagram: Diagram,
    page_plan: Any,
    pages: list[tuple[str, Diagram]] | None = None,
) -> str:
    """Generate uncompressed multi-page draw.io XML from a page plan.

    Page 1 is the executive architecture view. Later pages are filtered by
    the page-plan node and edge lists so details, security, and evidence flows
    do not overload the executive page. Cell IDs are page-prefixed to keep
    cross-page XML validation deterministic while each page remains readable.

    ``pages`` may carry pre-built output from :func:`build_page_diagrams` to
    avoid laying the model out twice when the caller also renders previews.
    """

    if pages is None:
        pages = build_page_diagrams(diagram, page_plan)
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "enterprise-drawio-diagrammer"})
    for page_name, page_diagram in pages:
        _add_diagram_page(mxfile, page_diagram, page_name)
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", short_empty_elements=True)


def _renumber_edges_per_page(diagram: Diagram) -> None:
    """Reassign edge sequence numbers so each page reads 1, 2, 3, ..."""

    for index, edge in enumerate(diagram.edges, start=1):
        edge.metadata = {**edge.metadata, "sequence": index}


def _add_diagram_page(mxfile: ET.Element, diagram: Diagram, page_name: str) -> None:
    laid_out = diagram if diagram.metadata.get("_laid_out") else apply_layout(diagram)
    furniture = compute_furniture(laid_out)
    page_width, page_height = _page_size(laid_out, furniture)
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

    boundary_by_id = {boundary.id: boundary for boundary in laid_out.boundaries}
    _add_title(root, laid_out, furniture.title)
    for boundary in laid_out.boundaries:
        _add_boundary(root, boundary)
    for node in laid_out.nodes:
        _add_node(root, node, boundary_by_id.get(node.group or ""))
    if furniture.legend is not None:
        _add_legend(root, laid_out, furniture.legend)
    for edge in laid_out.edges:
        _add_edge(root, edge)
    _add_page_notes(root, laid_out, furniture.notes)


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


def _page_size(diagram: Diagram, furniture: PageFurniture | None = None) -> tuple[int, int]:
    if furniture is None:
        furniture = compute_furniture(diagram)
    _, _, content_max_x, content_max_y = _content_bbox(diagram)
    max_x = content_max_x + 80
    max_y = content_max_y + 80
    for box in (furniture.title, furniture.legend, furniture.notes):
        if box is None:
            continue
        max_x = max(max_x, box.x + box.width + 40)
        max_y = max(max_y, box.y + box.height + 40)
    return max(1169, _snap_up(max_x)), max(827, _snap_up(max_y))


def _page_name(title: str) -> str:
    clean = "".join(char for char in title if char.isalnum() or char in {" ", "-", "_"}).strip()
    return (clean or "Page-1")[:60]


def _drawio_value(value: object) -> str:
    """Normalize cell label text for diagrams.net HTML labels.

    mxCell labels in this generator use ``html=1``. For multi-line text,
    diagrams.net expects an HTML break in the label value, not raw newline
    characters or a literal backslash-n token. ElementTree will XML-escape the
    ``<br>`` marker to ``&lt;br&gt;`` on serialization, which draw.io reads back as
    an HTML line break when opening the uncompressed XML.
    """

    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    return "<br>".join(text.split("\n"))


def _add_title(root: ET.Element, diagram: Diagram, box: FurnitureBox) -> None:
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{diagram.metadata.get('cell_prefix', '')}__title",
            "value": _drawio_value(box.text),
            "style": "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=20;fontStyle=1;fontColor=#1f2933;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": str(box.x), "y": str(box.y), "width": str(box.width), "height": str(box.height), "as": "geometry"})


def _add_boundary(root: ET.Element, boundary: Boundary) -> None:
    """Emit a boundary as a genuine draw.io container with a title strip.

    Dragging the boundary in draw.io moves its member nodes because members
    carry parent=<boundary_id> with container-relative geometry.
    """

    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": boundary.id,
            "value": _drawio_value(boundary.label),
            "style": _boundary_style(boundary),
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


def _add_node(root: ET.Element, node: Node, boundary: Boundary | None = None) -> None:
    style = get_icon_style(node.node_type, node.icon, node.label).drawio_style
    if node.risk_level and node.risk_level.lower() in {"high", "critical"}:
        style += "strokeColor=#b85450;strokeWidth=2;"
    x = node.x if node.x is not None else 80
    y = node.y if node.y is not None else 160
    parent = "1"
    if boundary is not None and boundary.x is not None and boundary.y is not None:
        parent = boundary.id
        x -= boundary.x
        y -= boundary.y
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": node.id,
            "value": _drawio_value(node.label),
            "style": style,
            "vertex": "1",
            "parent": parent,
        },
    )
    ET.SubElement(
        cell,
        "mxGeometry",
        {
            "x": str(x),
            "y": str(y),
            "width": str(node.width),
            "height": str(node.height),
            "as": "geometry",
        },
    )


def _add_edge(root: ET.Element, edge: Edge) -> None:
    style = edge.style or _edge_style(edge)
    if not style.endswith(";"):
        style += ";"
    sequence = edge.metadata.get("sequence")
    display_label = edge.metadata.get("display_label")
    numbered = sequence is not None and display_label is None
    value = "" if numbered else _drawio_value(_edge_value(edge))
    if value:
        style += "labelBackgroundColor=#ffffff;"
    exit_port = edge.metadata.get("exit_port")
    entry_port = edge.metadata.get("entry_port")
    if isinstance(exit_port, (tuple, list)) and len(exit_port) == 2:
        style += f"exitX={_style_number(exit_port[0])};exitY={_style_number(exit_port[1])};exitDx=0;exitDy=0;"
    if isinstance(entry_port, (tuple, list)) and len(entry_port) == 2:
        style += f"entryX={_style_number(entry_port[0])};entryY={_style_number(entry_port[1])};entryDx=0;entryDy=0;"
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": edge.id,
            "value": value,
            "style": style,
            "edge": "1",
            "parent": "1",
            "source": edge.source,
            "target": edge.target,
        },
    )
    geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    waypoints = edge.metadata.get("waypoints")
    if isinstance(waypoints, list) and waypoints:
        array = ET.SubElement(geometry, "Array", {"as": "points"})
        for point in waypoints:
            ET.SubElement(array, "mxPoint", {"x": _style_number(point[0]), "y": _style_number(point[1])})
    if numbered:
        _add_edge_number_label(root, edge, str(sequence))


def _add_edge_number_label(root: ET.Element, edge: Edge, value: str) -> None:
    """One numbered pill that rides the edge route forever (single numbering mechanism)."""

    label = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{edge.id}__n",
            "value": _drawio_value(value),
            "style": (
                "edgeLabel;html=1;rounded=1;"
                f"fillColor={_flow_color(edge)};strokeColor=none;fontColor=#ffffff;"
                "fontStyle=1;fontSize=12;align=center;verticalAlign=middle;spacing=4;"
            ),
            "vertex": "1",
            "connectable": "0",
            "parent": edge.id,
        },
    )
    ET.SubElement(label, "mxGeometry", {"relative": "1", "as": "geometry"})


def _style_number(value: float) -> str:
    number = float(value)
    return str(int(number)) if number == int(number) else f"{number:g}"


def _add_legend(root: ET.Element, diagram: Diagram, box: FurnitureBox) -> None:
    cell_prefix = str(diagram.metadata.get("cell_prefix", ""))
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{cell_prefix}__legend",
            "value": _drawio_value(box.text),
            "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#adb5bd;fontColor=#343a40;align=left;spacingLeft=8;verticalAlign=top;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": str(box.x), "y": str(box.y), "width": str(box.width), "height": str(box.height), "as": "geometry"})


def _add_page_notes(root: ET.Element, diagram: Diagram, box: FurnitureBox | None) -> None:
    if box is None:
        return
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"{diagram.metadata.get('cell_prefix', '')}__page_notes",
            "value": _drawio_value(box.text),
            "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8f9fa;strokeColor=#adb5bd;fontColor=#343a40;align=left;spacingLeft=8;verticalAlign=top;fontSize=12;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(cell, "mxGeometry", {"x": str(box.x), "y": str(box.y), "width": str(box.width), "height": str(box.height), "as": "geometry"})



def _boundary_style(boundary: Boundary) -> str:
    boundary_type = boundary.boundary_type.lower()
    stroke = "#dc2626" if boundary_type in {"trust", "security"} else "#6c757d"
    fill = "#fffafa" if boundary_type in {"trust", "security"} else "#f8fbff"
    return (
        "swimlane;html=1;rounded=1;startSize=32;container=1;collapsible=0;"
        "dashed=1;dashPattern=8 4;whiteSpace=wrap;"
        f"fillColor={fill};swimlaneFillColor={fill};strokeColor={stroke};"
        "align=left;spacingLeft=12;fontStyle=1;fontColor=#343a40;fontSize=13;"
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

"""Static visual QA and local renderer detection for draw.io outputs."""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .diagram_model import Diagram
from .layout_engine import ENTERPRISE_HORIZONTAL_TYPES, HORIZONTAL_TYPES


@dataclass(frozen=True, slots=True)
class RendererStatus:
    available: bool
    command: str | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class RenderExport:
    """Outcome of one real draw.io page export attempt."""

    page_number: int
    path: str
    ok: bool
    message: str


@dataclass(frozen=True, slots=True)
class VisualQaIssue:
    severity: str
    message: str
    page: str | None = None
    item_id: str | None = None


@dataclass(frozen=True, slots=True)
class _Box:
    item_id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    style: str

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


RENDERER_COMMANDS = ("drawio", "draw.io", "diagrams.net", "diagramsnet", "drawio-desktop")
MAX_EDGE_LABEL_CHARS = 24
MIN_TEXT_HEIGHT = 38


def detect_renderer() -> RendererStatus:
    """Detect a local draw.io/diagrams.net renderer without pretending to render."""

    for command in RENDERER_COMMANDS:
        path = shutil.which(command)
        if path:
            return RendererStatus(True, path, "Renderer available; screenshot export can be added by the caller.")
    return RendererStatus(False, None, "Renderer unavailable; performed static XML geometry QA only.")


def export_pages_with_renderer(
    renderer: RendererStatus,
    xml_path: Path,
    output_dir: Path,
    page_count: int,
) -> list[RenderExport]:
    """Export each page to PNG with a detected draw.io binary.

    Tries ``xvfb-run -a`` first when available (headless Linux), then a plain
    invocation. Reports failures honestly instead of pretending an export
    happened.
    """

    if not renderer.available or not renderer.command:
        return []
    xvfb = shutil.which("xvfb-run")
    exports: list[RenderExport] = []
    for page_index in range(page_count):
        out_path = Path(output_dir) / f"render-page-{page_index + 1}.png"
        base = [
            renderer.command,
            "-x",
            "-f",
            "png",
            "--page-index",
            str(page_index),
            "-o",
            str(out_path),
            str(xml_path),
        ]
        attempts = ([[xvfb, "-a", *base]] if xvfb else []) + [base]
        ok = False
        message = "no export attempt ran"
        for command in attempts:
            try:
                completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
            except (OSError, subprocess.SubprocessError) as exc:
                message = f"{command[0]} failed to run: {exc}"
                continue
            if completed.returncode == 0 and out_path.exists():
                ok = True
                message = "exported"
                break
            message = (completed.stderr or completed.stdout or "").strip()[:200] or f"exit code {completed.returncode}"
        exports.append(RenderExport(page_index + 1, str(out_path), ok, message))
    return exports


def analyze_drawio_xml(xml_text: str) -> list[VisualQaIssue]:
    """Run deterministic static checks that catch common review-quality defects."""

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return [VisualQaIssue("error", f"XML is not parseable for visual QA: {exc}")]

    issues: list[VisualQaIssue] = []
    for diagram in root.findall("diagram"):
        page_name = diagram.attrib.get("name", "unnamed page")
        model = diagram.find("mxGraphModel")
        if model is None:
            issues.append(VisualQaIssue("error", "Missing mxGraphModel", page_name))
            continue
        page_width = _float_attr(model, "pageWidth", 1169)
        page_height = _float_attr(model, "pageHeight", 827)
        boxes = _absolute_boxes(model)
        content_boxes = [box for box in boxes if _box_kind(box) == "content"]
        furniture_boxes = [box for box in boxes if _box_kind(box) == "furniture"]
        boundary_boxes = [box for box in boxes if _box_kind(box) == "boundary"]

        for box in content_boxes:
            if box.x < 0 or box.y < 0 or box.right > page_width or box.bottom > page_height:
                issues.append(VisualQaIssue("warning", f"Off-canvas node: {box.label or box.item_id}", page_name, box.item_id))
            if box.height < MIN_TEXT_HEIGHT and len(box.label) > 18:
                issues.append(VisualQaIssue("warning", f"Potentially unreadable text: {box.label}", page_name, box.item_id))

        for first_index, first in enumerate(content_boxes):
            for second in content_boxes[first_index + 1:]:
                if _boxes_overlap(first, second):
                    issues.append(
                        VisualQaIssue(
                            "warning",
                            f"Node overlap: {first.label or first.item_id} overlaps {second.label or second.item_id}",
                            page_name,
                            first.item_id,
                        )
                    )

        # Furniture (title, legend, notes, badges) must never sit on content.
        for furniture in furniture_boxes:
            for box in content_boxes:
                if _boxes_overlap(furniture, box, slack=0):
                    issues.append(
                        VisualQaIssue(
                            "warning",
                            f"Furniture overlap: {furniture.item_id} covers {box.label or box.item_id}",
                            page_name,
                            furniture.item_id,
                        )
                    )
            if "__badge_" in furniture.item_id:
                continue  # badges ride edge routes, which legitimately run inside boundaries
            for boundary in boundary_boxes:
                if _boxes_overlap(furniture, boundary, slack=0):
                    issues.append(
                        VisualQaIssue(
                            "warning",
                            f"Furniture overlap: {furniture.item_id} covers boundary {boundary.label or boundary.item_id}",
                            page_name,
                            furniture.item_id,
                        )
                    )
        for first_index, first in enumerate(furniture_boxes):
            for second in furniture_boxes[first_index + 1:]:
                if _boxes_overlap(first, second):
                    issues.append(
                        VisualQaIssue(
                            "warning",
                            f"Furniture overlap: {first.item_id} overlaps {second.item_id}",
                            page_name,
                            first.item_id,
                        )
                    )

        for first_index, first in enumerate(boundary_boxes):
            for second in boundary_boxes[first_index + 1:]:
                if _boxes_overlap(first, second, slack=0):
                    issues.append(
                        VisualQaIssue(
                            "error",
                            f"Boundary overlap: {first.label or first.item_id} overlaps {second.label or second.item_id}",
                            page_name,
                            first.item_id,
                        )
                    )

        # Exactly one numbering mechanism: numbered pills are edgeLabel child
        # cells parented to their edge. Floating ellipse badges and digit
        # edge values are the legacy double-numbering mechanisms.
        edge_ids = {cell.attrib.get("id", "") for cell in model.findall(".//mxCell[@edge='1']")}
        numbered_children: set[str] = set()
        for cell in model.findall(".//mxCell[@vertex='1']"):
            style = cell.attrib.get("style", "")
            value = cell.attrib.get("value", "")
            parent = cell.attrib.get("parent", "")
            if "edgeLabel" in style and parent in edge_ids:
                numbered_children.add(parent)
                continue
            if "ellipse" in style and value.isdigit():
                issues.append(
                    VisualQaIssue(
                        "error",
                        f"Orphan numbered badge ellipse {cell.attrib.get('id')}: numbering must be an edge label riding the route",
                        page_name,
                        cell.attrib.get("id"),
                    )
                )

        connected_ids: set[str] = set()
        for edge in model.findall(".//mxCell[@edge='1']"):
            value = edge.attrib.get("value", "")
            source = edge.attrib.get("source")
            target = edge.attrib.get("target")
            if source:
                connected_ids.add(source)
            if target:
                connected_ids.add(target)
            if len(value) > MAX_EDGE_LABEL_CHARS and not value.isdigit():
                issues.append(VisualQaIssue("warning", f"Long edge label should move to legend: {value}", page_name, edge.attrib.get("id")))
            if value.isdigit() and edge.attrib.get("id") in numbered_children:
                issues.append(
                    VisualQaIssue(
                        "error",
                        f"Double numbering on edge {edge.attrib.get('id')}: digit value plus numbered child label",
                        page_name,
                        edge.attrib.get("id"),
                    )
                )

        for box in boxes:
            if box.item_id in {"0", "1"}:
                continue
            style = box.style
            if (
                "shape=mxgraph." in style
                and "aspect=fixed" not in style
                and (box.width > 64 or box.height > 64)
            ):
                issues.append(
                    VisualQaIssue(
                        "warning",
                        f"Stencil stretched to {box.width:g}x{box.height:g} without aspect=fixed: {box.item_id}",
                        page_name,
                        box.item_id,
                    )
                )
            # Glyph contract: fixed-aspect shapes are emitted square. A ratio
            # deviating >10% means someone resized a stencil out of shape.
            if "aspect=fixed" in style and box.width > 0 and box.height > 0 and abs(box.width / box.height - 1) > 0.10:
                issues.append(
                    VisualQaIssue(
                        "warning",
                        f"Fixed-aspect shape {box.item_id} has geometry ratio {box.width / box.height:.2f}, deviating >10% from square",
                        page_name,
                        box.item_id,
                    )
                )
            if box.item_id.endswith("__icon") or not box.label:
                continue
            contrast = _style_contrast_ratio(style)
            if contrast is None:
                continue
            # Bold one/two-character values (numbered pills) read like large
            # text; WCAG large-text threshold 3.0 applies. Everything else 4.5.
            threshold = 3.0 if ("fontStyle=1" in style and len(box.label) <= 2) else 4.5
            if contrast < threshold:
                issues.append(
                    VisualQaIssue(
                        "warning",
                        f"Low text contrast ({contrast:.1f}:1) on {box.label!r}",
                        page_name,
                        box.item_id,
                    )
                )

        is_executive_page = page_name.strip().lower().startswith("executive")
        for box in content_boxes:
            if box.item_id not in connected_ids:
                severity = "error" if is_executive_page else "warning"
                issues.append(
                    VisualQaIssue(
                        severity,
                        f"Disconnected node on {page_name}: {box.label or box.item_id}",
                        page_name,
                        box.item_id,
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Model-level QA over the laid-out pages (runs pre-emit; phase 3 owns routes)

NODE_FONT_SIZE = 13
LINE_HEIGHT = 1.35


def analyze_page_models(pages: list[tuple[str, Diagram]]) -> list[VisualQaIssue]:
    """Deep checks on the planned model: routes, flow direction, text fit."""

    issues: list[VisualQaIssue] = []
    for page_index, (page_name, diagram) in enumerate(pages, start=1):
        severity = "error" if page_index == 1 else "warning"
        issues.extend(_check_route_collisions(page_name, diagram, severity))
        issues.extend(_check_monotonic_flow(page_name, diagram))
        issues.extend(_check_text_overflow(page_name, diagram))
    return issues


def _check_route_collisions(page_name: str, diagram: Diagram, severity: str) -> list[VisualQaIssue]:
    from .drawio_xml import compute_furniture  # local import; drawio_xml does not import visual_qa

    issues: list[VisualQaIssue] = []
    rects: dict[str, tuple[float, float, float, float]] = {
        node.id: (float(node.x or 0), float(node.y or 0), float((node.x or 0) + node.width), float((node.y or 0) + node.height))
        for node in diagram.nodes
    }
    furniture = compute_furniture(diagram)
    furniture_rects = {
        name: (float(box.x), float(box.y), float(box.x + box.width), float(box.y + box.height))
        for name, box in (("legend", furniture.legend), ("page notes", furniture.notes))
        if box is not None
    }
    for edge in diagram.edges:
        route = edge.metadata.get("route")
        if not isinstance(route, list) or len(route) < 2:
            continue
        for p1, p2 in zip(route, route[1:]):
            for node_id, rect in rects.items():
                if node_id in {edge.source, edge.target}:
                    continue
                if _segment_hits_rect(p1, p2, rect):
                    issues.append(
                        VisualQaIssue(
                            severity,
                            f"Planned route of {edge.id} crosses node {node_id}",
                            page_name,
                            edge.id,
                        )
                    )
            for name, rect in furniture_rects.items():
                if _segment_hits_rect(p1, p2, rect):
                    issues.append(
                        VisualQaIssue(
                            severity,
                            f"Planned route of {edge.id} crosses the {name}",
                            page_name,
                            edge.id,
                        )
                    )
    return issues


def _check_monotonic_flow(page_name: str, diagram: Diagram) -> list[VisualQaIssue]:
    diagram_type = diagram.diagram_type.lower()
    horizontal = (
        diagram_type in HORIZONTAL_TYPES
        or diagram_type in ENTERPRISE_HORIZONTAL_TYPES
        or diagram.direction.lower() == "left-to-right"
    )
    nodes = {node.id: node for node in diagram.nodes}
    issues: list[VisualQaIssue] = []
    for edge in diagram.edges:
        if edge.metadata.get("sequence") is None:
            continue
        if edge.direction.lower() in {"backward", "reverse", "return"}:
            continue  # explicitly declared backward flows are allowed
        source, target = nodes.get(edge.source), nodes.get(edge.target)
        if source is None or target is None:
            continue
        flow = (lambda n: n.x or 0) if horizontal else (lambda n: n.y or 0)
        cross = (lambda n: n.y or 0) if horizontal else (lambda n: n.x or 0)
        if flow(source) < flow(target):
            continue
        if flow(source) == flow(target) and cross(source) < cross(target):
            continue
        issues.append(
            VisualQaIssue(
                "error",
                f"Numbered flow {edge.metadata.get('sequence')} ({edge.id}) points backward/upward against the reading direction",
                page_name,
                edge.id,
            )
        )
    return issues


def _check_text_overflow(page_name: str, diagram: Diagram) -> list[VisualQaIssue]:
    from .icon_registry import get_node_visual

    issues: list[VisualQaIssue] = []
    for node in diagram.nodes:
        has_glyph = get_node_visual(node.node_type, node.icon, node.label).glyph_style is not None
        inner_width = node.width - 12 - (56 if has_glyph else 12)
        char_width = 0.6 * NODE_FONT_SIZE
        longest_word = max((len(word) for word in node.label.split()), default=0)
        if longest_word * char_width > inner_width:
            issues.append(
                VisualQaIssue(
                    "warning",
                    f"Label wider than card: {node.label!r} needs {int(longest_word * char_width)}px, card offers {int(inner_width)}px",
                    page_name,
                    node.id,
                )
            )
            continue
        max_chars = max(4, int(inner_width / char_width))
        line_count = 0
        for raw_line in node.label.split("\n"):
            words = raw_line.split()
            if not words:
                line_count += 1
                continue
            current = words[0]
            for word in words[1:]:
                if len(current) + 1 + len(word) <= max_chars:
                    current = f"{current} {word}"
                else:
                    line_count += 1
                    current = word
            line_count += 1
        if line_count * NODE_FONT_SIZE * LINE_HEIGHT > node.height - 16:
            issues.append(
                VisualQaIssue(
                    "warning",
                    f"Label taller than card: {node.label!r} needs about {line_count} lines",
                    page_name,
                    node.id,
                )
            )
    return issues


def _segment_hits_rect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    rect: tuple[float, float, float, float],
    slack: float = 1.0,
) -> bool:
    """Axis-aligned segment vs rect interior (planned routes are orthogonal)."""

    (x1, y1), (x2, y2) = (p1[0], p1[1]), (p2[0], p2[1])
    rx1, ry1, rx2, ry2 = rect
    lo_x, hi_x = sorted((x1, x2))
    lo_y, hi_y = sorted((y1, y2))
    return lo_x < rx2 - slack and hi_x > rx1 + slack and lo_y < ry2 - slack and hi_y > ry1 + slack


def qa_error_count(issues: list[VisualQaIssue], xml_error_count: int = 0) -> int:
    """Total error-severity findings that must fail a --validate run."""

    return xml_error_count + sum(1 for issue in issues if issue.severity == "error")


def result_line(error_count: int) -> str:
    return f"RESULT: FAIL ({error_count} errors)" if error_count else "RESULT: PASS"


def render_visual_qa(
    issues: list[VisualQaIssue],
    renderer: RendererStatus | None = None,
    *,
    xml_error_count: int = 0,
    exports: list[RenderExport] | None = None,
    preview_paths: list[Path] | None = None,
) -> str:
    renderer = renderer or detect_renderer()
    lines = [result_line(qa_error_count(issues, xml_error_count)), "", "# Render and Visual QA", ""]
    if renderer.available:
        lines.append(f"- Renderer available: {renderer.command}")
        if exports:
            for export in exports:
                if export.ok:
                    lines.append(f"- Page {export.page_number} exported: {export.path}")
                else:
                    lines.append(f"- Page {export.page_number} export FAILED: {export.message}")
        else:
            lines.append("- Screenshot captured: no; renderer export was not attempted on this run.")
    else:
        lines.append(f"- Renderer unavailable: {renderer.note}")
    if preview_paths:
        lines.extend(["", "## Model Previews"])
        lines.extend(f"- {path}" for path in preview_paths)
    lines.extend(["", "## Static Checks"])
    if xml_error_count:
        lines.append(f"- [error] draw.io XML validation reported {xml_error_count} error(s); see stderr/quality-checklist.")
    if not issues and not xml_error_count:
        lines.append("- [x] No static overlap, off-canvas, unreadable text, long edge label, or numbering-mechanism findings.")
    else:
        for issue in issues:
            page = f" ({issue.page})" if issue.page else ""
            item = f" [{issue.item_id}]" if issue.item_id else ""
            lines.append(f"- [{issue.severity}]{page}{item} {issue.message}")
    return "\n".join(lines).rstrip() + "\n"


def _absolute_boxes(model: ET.Element) -> list[_Box]:
    """Vertex boxes with container-relative geometry resolved to page coordinates."""

    cells = model.findall(".//mxCell")
    parents = {cell.attrib.get("id", ""): cell.attrib.get("parent", "") for cell in cells}
    origins: dict[str, tuple[float, float]] = {}
    raw: dict[str, tuple[float, float]] = {}
    for cell in cells:
        geometry = cell.find("mxGeometry")
        if geometry is not None:
            raw[cell.attrib.get("id", "")] = (_float_attr(geometry, "x", 0), _float_attr(geometry, "y", 0))

    def origin(cell_id: str, depth: int = 0) -> tuple[float, float]:
        if cell_id in {"", "0", "1"} or depth > 10:
            return (0.0, 0.0)
        if cell_id in origins:
            return origins[cell_id]
        parent_x, parent_y = origin(parents.get(cell_id, ""), depth + 1)
        own_x, own_y = raw.get(cell_id, (0.0, 0.0))
        origins[cell_id] = (parent_x + own_x, parent_y + own_y)
        return origins[cell_id]

    boxes: list[_Box] = []
    for cell in cells:
        if cell.attrib.get("vertex") != "1":
            continue
        geometry = cell.find("mxGeometry")
        if geometry is None:
            continue
        cell_id = cell.attrib.get("id", "")
        parent_x, parent_y = origin(parents.get(cell_id, ""))
        boxes.append(
            _Box(
                item_id=cell_id,
                label=cell.attrib.get("value", ""),
                x=parent_x + _float_attr(geometry, "x", 0),
                y=parent_y + _float_attr(geometry, "y", 0),
                width=_float_attr(geometry, "width", 0),
                height=_float_attr(geometry, "height", 0),
                style=cell.attrib.get("style", ""),
            )
        )
    return boxes


def _box_kind(box: _Box) -> str:
    """Classify a vertex: boundary container, page furniture, or content node."""

    if box.item_id in {"0", "1"} or box.width <= 0 or box.height <= 0:
        return "ignore"
    if box.item_id.endswith("__icon"):
        return "ignore"  # glyph child riding its parent card by design
    if (
        box.item_id.endswith("__title")
        or box.item_id.endswith("__legend")
        or box.item_id.endswith("__page_notes")
        or "__badge_" in box.item_id
    ):
        return "furniture"
    if "swimlane" in box.style or ("dashed=1" in box.style and "verticalAlign=top" in box.style):
        return "boundary"
    return "content"


def _boxes_overlap(first: _Box, second: _Box, slack: float = 12) -> bool:
    x_overlap = min(first.right, second.right) - max(first.x, second.x)
    y_overlap = min(first.bottom, second.bottom) - max(first.y, second.y)
    return x_overlap > slack and y_overlap > slack


def _float_attr(element: ET.Element, name: str, default: float) -> float:
    try:
        return float(element.attrib.get(name, default))
    except (TypeError, ValueError):
        return default


_FONT_COLOR_RE = re.compile(r"fontColor=(#[0-9a-fA-F]{6})")
_FILL_COLOR_RE = re.compile(r"fillColor=(#[0-9a-fA-F]{6})")


def _style_contrast_ratio(style: str) -> float | None:
    """WCAG contrast ratio of fontColor vs fillColor when both are set."""

    font_match = _FONT_COLOR_RE.search(style)
    fill_match = _FILL_COLOR_RE.search(style)
    if font_match is None or fill_match is None:
        return None
    first = _relative_luminance(font_match.group(1))
    second = _relative_luminance(fill_match.group(1))
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255.0 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

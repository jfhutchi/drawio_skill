"""Static visual QA and local renderer detection for draw.io outputs."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RendererStatus:
    available: bool
    command: str | None = None
    note: str = ""


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
        boxes = [_box_from_cell(cell) for cell in model.findall(".//mxCell[@vertex='1']")]
        boxes = [box for box in boxes if box is not None]
        content_boxes = [box for box in boxes if _is_content_box(box)]

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

        badge_values = {cell.attrib.get("value") for cell in model.findall(".//mxCell[@vertex='1']") if "ellipse" in cell.attrib.get("style", "")}
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
            if value.isdigit() and value not in badge_values:
                issues.append(VisualQaIssue("warning", f"Missing numbered badge for edge label {value}", page_name, edge.attrib.get("id")))

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


def render_visual_qa(issues: list[VisualQaIssue], renderer: RendererStatus | None = None) -> str:
    renderer = renderer or detect_renderer()
    lines = ["# Render and Visual QA", ""]
    if renderer.available:
        lines.append(f"- Renderer available: {renderer.command}")
        lines.append("- Screenshot captured: no; CLI currently records availability and static checks only.")
    else:
        lines.append(f"- Renderer unavailable: {renderer.note}")
    lines.extend(["", "## Static Checks"])
    if not issues:
        lines.append("- [x] No static overlap, off-canvas, unreadable text, long edge label, or missing badge warnings found.")
    else:
        for issue in issues:
            page = f" ({issue.page})" if issue.page else ""
            item = f" [{issue.item_id}]" if issue.item_id else ""
            lines.append(f"- [{issue.severity}]{page}{item} {issue.message}")
    return "\n".join(lines).rstrip() + "\n"


def _box_from_cell(cell: ET.Element) -> _Box | None:
    geometry = cell.find("mxGeometry")
    if geometry is None:
        return None
    return _Box(
        item_id=cell.attrib.get("id", ""),
        label=cell.attrib.get("value", ""),
        x=_float_attr(geometry, "x", 0),
        y=_float_attr(geometry, "y", 0),
        width=_float_attr(geometry, "width", 0),
        height=_float_attr(geometry, "height", 0),
        style=cell.attrib.get("style", ""),
    )


def _is_content_box(box: _Box) -> bool:
    if box.item_id in {"0", "1"} or box.item_id.endswith("__title") or box.item_id.endswith("__legend"):
        return False
    if "__badge_" in box.item_id or box.item_id.endswith("__page_notes"):
        return False
    if "dashed=1" in box.style and "verticalAlign=top" in box.style:
        return False
    if box.width <= 0 or box.height <= 0:
        return False
    return True


def _boxes_overlap(first: _Box, second: _Box) -> bool:
    x_overlap = min(first.right, second.right) - max(first.x, second.x)
    y_overlap = min(first.bottom, second.bottom) - max(first.y, second.y)
    return x_overlap > 12 and y_overlap > 12


def _float_attr(element: ET.Element, name: str, default: float) -> float:
    try:
        return float(element.attrib.get(name, default))
    except (TypeError, ValueError):
        return default

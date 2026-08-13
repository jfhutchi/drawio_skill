"""Model-faithful SVG/PNG preview of laid-out diagram pages.

Renders the intermediate model (not the emitted draw.io XML) so the picture
shows exactly what the layout engine planned: boundaries, node cards with
wrapped labels, edge polylines, edge labels, legend, title, and notes.

The SVG path is pure stdlib. PNG rasterization is optional: it draws the same
scene through Pillow when importable (preferred) or matplotlib as a fallback,
and is skipped silently when neither is installed.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import base64
import re
from functools import lru_cache

from .diagram_model import Diagram, Edge, Node
from .drawio_xml import compute_furniture, _edge_value, _flow_color, _page_size
from .icon_registry import GLYPH_SIZE, get_node_visual
from .layout_engine import route_midpoint
from .visual_qa import _relative_luminance

CHAR_WIDTH_FACTOR = 0.6  # estimated glyph width = 0.6 * fontSize
LINE_HEIGHT_FACTOR = 1.35
NODE_FONT_SIZE = 13
BOUNDARY_FONT_SIZE = 13
FURNITURE_FONT_SIZE = 12
EDGE_FONT_SIZE = 11
ARROW_SIZE = 9.0


@dataclass(frozen=True, slots=True)
class Shape:
    """One drawable primitive shared by the SVG and PNG emitters.

    ``kind`` is one of ``rect``, ``line``, ``polygon``, ``text``. For rects,
    ``points`` is ((x, y), (width, height)); for lines/polygons it is the
    vertex sequence; for text it is the single anchor point.
    """

    kind: str
    cls: str
    points: tuple[tuple[float, float], ...]
    text: str = ""
    fill: str | None = None
    stroke: str | None = None
    dashed: bool = False
    font_size: int = FURNITURE_FONT_SIZE
    bold: bool = False
    anchor: str = "start"
    href: str | None = None  # kind "icon": embedded data URI; fill/text are the raster fallback


@dataclass(slots=True)
class PageScene:
    name: str
    width: int
    height: int
    shapes: list[Shape] = field(default_factory=list)
    node_count: int = 0
    boundary_count: int = 0
    edge_count: int = 0


def estimate_text_width(text: str, font_size: int) -> float:
    return CHAR_WIDTH_FACTOR * font_size * len(text)


def wrap_label(text: str, box_width: float, font_size: int) -> list[str]:
    """Greedy word wrap using the estimated glyph width."""

    max_chars = max(4, int(box_width / (CHAR_WIDTH_FACTOR * font_size)))
    lines: list[str] = []
    for raw_line in str(text).split("\n"):
        words = raw_line.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            if len(current) + 1 + len(word) <= max_chars:
                current = f"{current} {word}"
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def build_scene(page_name: str, diagram: Diagram) -> PageScene:
    width, height = _page_size(diagram)
    scene = PageScene(name=page_name, width=int(width), height=int(height))
    shapes = scene.shapes

    shapes.append(Shape("rect", "page", ((0.0, 0.0), (float(width), float(height))), fill="#ffffff", stroke="#d0d4d9"))

    for boundary in diagram.boundaries:
        x, y = float(boundary.x or 0), float(boundary.y or 0)
        trust = boundary.boundary_type.lower() in {"trust", "security"}
        shapes.append(
            Shape(
                "rect",
                "boundary",
                ((x, y), (float(boundary.width), float(boundary.height))),
                fill="#fffafa" if trust else "#f8fbff",
                stroke="#dc2626" if trust else "#6c757d",
                dashed=True,
            )
        )
        shapes.append(
            Shape(
                "text",
                "boundary-label",
                ((x + 12.0, y + 8.0 + BOUNDARY_FONT_SIZE),),
                text=boundary.label,
                font_size=BOUNDARY_FONT_SIZE,
                bold=True,
                fill="#343a40",
            )
        )

    for node in diagram.nodes:
        _add_node_shapes(shapes, node)
        scene.node_count += 1
    scene.boundary_count = len(diagram.boundaries)

    nodes_by_id = {node.id: node for node in diagram.nodes}
    for edge in diagram.edges:
        if _add_edge_shapes(shapes, edge, nodes_by_id):
            scene.edge_count += 1

    _add_furniture_shapes(shapes, diagram)
    return scene


_GLYPH_FILL_RE = re.compile(r"fillColor=(#[0-9a-fA-F]{6})")
_GLYPH_SHAPE_RE = re.compile(r"shape=([A-Za-z0-9_.]+)")
_GLYPH_IMAGE_RE = re.compile(r"image=[^;]*/([A-Za-z0-9_]+)\.svg")

_VENDOR_MONOGRAMS = {"azure": "Az", "aws": "AWS", "gcp": "GCP", "kubernetes": "K8s"}
_SHAPE_MONOGRAMS = {
    "cylinder3d": "DB",
    "umlActor": "USR",
    "folder": "SRC",
    "package": "PKG",
    "note": "DOC",
    "document": "DOC",
    "cloud": "OBJ",
    "mxgraph.basic.queue": "MQ",
    "mxgraph.cisco19.rect": "SRV",
    "mxgraph.weblogos.github": "GH",
}


_VENDOR_BRAND_FILLS = {"azure": "#0078D4", "aws": "#FF9900", "gcp": "#4285F4", "kubernetes": "#326CE5"}

_ASSET_ROOT = Path(__file__).resolve().parent / "assets"
_GLYPH_IMAGE_PATH_RE = re.compile(r"image=img/lib/([^;]+);")


@lru_cache(maxsize=None)
def _asset_data_uri(relative_path: str) -> str | None:
    """Vendored copy of a bundled diagrams.net icon, as an embeddable data URI."""

    path = _ASSET_ROOT / relative_path
    if not path.is_file():
        return None
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"


def _glyph_data_uri(glyph_style: str) -> str | None:
    match = _GLYPH_IMAGE_PATH_RE.search(glyph_style)
    return _asset_data_uri(match.group(1)) if match else None


def _glyph_marker(glyph_style: str, vendor: str | None) -> tuple[str, str]:
    """(fill, monogram) standing in for a stencil the stdlib cannot rasterize.

    The real vendor artwork lives in the emitted .drawio (and in the optional
    real-renderer export); the preview shows the glyph's exact slot, color,
    and identity so its presence and geometry are reviewable.
    """

    fill_match = _GLYPH_FILL_RE.search(glyph_style)
    if fill_match is not None:
        fill = fill_match.group(1)
    else:
        fill = _VENDOR_BRAND_FILLS.get(vendor or "", "#6c757d")
    shape_match = _GLYPH_SHAPE_RE.search(glyph_style)
    token = shape_match.group(1) if shape_match else ""
    if token in _SHAPE_MONOGRAMS:
        return fill, _SHAPE_MONOGRAMS[token]
    if vendor in _VENDOR_MONOGRAMS:
        return fill, _VENDOR_MONOGRAMS[vendor]
    if not token:
        image_match = _GLYPH_IMAGE_RE.search(glyph_style)
        if image_match:
            return fill, image_match.group(1)[:2].upper()
    short = token.rsplit(".", 1)[-1]
    return fill, (short[:2].upper() or "??")


def _add_node_shapes(shapes: list[Shape], node: Node) -> None:
    x, y = float(node.x or 0), float(node.y or 0)
    w, h = float(node.width), float(node.height)
    shapes.append(Shape("rect", "node", ((x, y), (w, h)), fill="#fdfdfd", stroke="#495057"))
    visual = get_node_visual(node.node_type, node.icon, node.label)
    # Mirror the emitted card grammar and the layout fitter: spacingLeft=12
    # plus reserved right-hand space (glyph or plain padding).
    label_width = w - 12.0 - (GLYPH_SIZE + 16.0 if visual.glyph_style else 12.0)
    lines = wrap_label(node.label, label_width, NODE_FONT_SIZE)
    line_height = NODE_FONT_SIZE * LINE_HEIGHT_FACTOR
    start_y = y + h / 2.0 - line_height * (len(lines) - 1) / 2.0 + NODE_FONT_SIZE / 3.0
    for index, line in enumerate(lines):
        shapes.append(
            Shape(
                "text",
                "node-label",
                ((x + 12.0, start_y + index * line_height),),
                text=line,
                font_size=NODE_FONT_SIZE,
                fill="#212529",
            )
        )
    if visual.glyph_style:
        fill, monogram = _glyph_marker(visual.glyph_style, visual.vendor)
        gx = x + w - GLYPH_SIZE - 8.0
        gy = y + 8.0
        href = _glyph_data_uri(visual.glyph_style)
        if href is not None:
            # Real vendored artwork, embedded so the SVG stays self-contained.
            shapes.append(
                Shape(
                    "icon",
                    "node-glyph-image",
                    ((gx, gy), (float(GLYPH_SIZE), float(GLYPH_SIZE))),
                    text=monogram,
                    fill=fill,
                    href=href,
                )
            )
            return
        shapes.append(Shape("rect", "node-glyph", ((gx, gy), (float(GLYPH_SIZE), float(GLYPH_SIZE))), fill=fill))
        text_fill = "#ffffff" if _relative_luminance(fill) < 0.45 else "#212529"
        shapes.append(
            Shape(
                "text",
                "node-glyph-label",
                ((gx + GLYPH_SIZE / 2.0, gy + GLYPH_SIZE / 2.0 + 4.0),),
                text=monogram,
                font_size=11,
                bold=True,
                fill=text_fill,
                anchor="middle",
            )
        )


def _edge_route(edge: Edge, nodes_by_id: dict[str, Node]) -> list[tuple[float, float]] | None:
    route = edge.metadata.get("route")
    if isinstance(route, list) and len(route) >= 2:
        try:
            return [(float(px), float(py)) for px, py in route]
        except (TypeError, ValueError):
            pass
    source = nodes_by_id.get(edge.source)
    target = nodes_by_id.get(edge.target)
    if source is None or target is None:
        return None
    return [
        ((source.x or 0) + source.width / 2.0, (source.y or 0) + source.height / 2.0),
        ((target.x or 0) + target.width / 2.0, (target.y or 0) + target.height / 2.0),
    ]


def _add_edge_shapes(shapes: list[Shape], edge: Edge, nodes_by_id: dict[str, Node]) -> bool:
    points = _edge_route(edge, nodes_by_id)
    if points is None:
        return False
    color = _flow_color(edge)
    dashed = edge.metadata.get("flow_type") in {"optional_storage", "security_sensitive"}
    shapes.append(Shape("line", "edge", tuple(points), stroke=color, dashed=bool(dashed)))
    shapes.append(Shape("polygon", "edge-arrow", _arrow_head(points[-2], points[-1]), fill=color))
    label = str(_edge_value(edge))
    if label:
        mid, normal = _midpoint_normal(points)
        cx = mid[0] + normal[0] * 14.0
        cy = mid[1] + normal[1] * 14.0
        if label.isdigit():
            # Mirror the emitted pill: flow-colored capsule, white number,
            # floated off the line so it stays readable.
            pill_width = max(18.0, 6.0 + len(label) * 7.0)
            shapes.append(Shape("rect", "edge-label-pill", ((cx - pill_width / 2.0, cy - 9.0), (pill_width, 18.0)), fill=color))
            shapes.append(
                Shape(
                    "text",
                    "edge-label",
                    ((cx, cy + 4.0),),
                    text=label,
                    font_size=EDGE_FONT_SIZE,
                    bold=True,
                    fill="#ffffff",
                    anchor="middle",
                )
            )
        else:
            shapes.append(
                Shape(
                    "text",
                    "edge-label",
                    ((cx, cy + 4.0),),
                    text=label,
                    font_size=EDGE_FONT_SIZE,
                    bold=True,
                    fill=color,
                    anchor="middle",
                )
            )
    return True


def _midpoint_normal(points: list[tuple[float, float]]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Route midpoint plus the unit normal of its segment (pointing up/right)."""

    mid = route_midpoint(points)
    segments = list(zip(points, points[1:]))
    remaining = sum(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 for (ax, ay), (bx, by) in segments) / 2.0
    direction = (1.0, 0.0)
    for (ax, ay), (bx, by) in segments:
        seg_len = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if seg_len >= remaining and seg_len > 0:
            direction = ((bx - ax) / seg_len, (by - ay) / seg_len)
            break
        remaining -= seg_len
    normal = (-direction[1], direction[0])
    if normal[1] > 0 or (normal[1] == 0 and normal[0] < 0):
        normal = (-normal[0], -normal[1])
    return mid, normal


def _arrow_head(before: tuple[float, float], tip: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    dx, dy = tip[0] - before[0], tip[1] - before[1]
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / length, dy / length
    left = (tip[0] - ARROW_SIZE * ux + ARROW_SIZE * 0.5 * uy, tip[1] - ARROW_SIZE * uy - ARROW_SIZE * 0.5 * ux)
    right = (tip[0] - ARROW_SIZE * ux - ARROW_SIZE * 0.5 * uy, tip[1] - ARROW_SIZE * uy + ARROW_SIZE * 0.5 * ux)
    return (tip, left, right)


def _add_furniture_shapes(shapes: list[Shape], diagram: Diagram) -> None:
    furniture = compute_furniture(diagram)
    title = furniture.title
    title_lines = title.text.split("\n")
    for index, line in enumerate(title_lines):
        size = 20 if index == 0 else FURNITURE_FONT_SIZE
        shapes.append(
            Shape(
                "text",
                "furniture-title",
                ((float(title.x), float(title.y) + 24.0 + index * 24.0),),
                text=line,
                font_size=size,
                bold=index == 0,
                fill="#1f2933",
            )
        )
    for box, cls in ((furniture.legend, "furniture-legend"), (furniture.notes, "furniture-notes")):
        if box is None:
            continue
        shapes.append(
            Shape("rect", cls, ((float(box.x), float(box.y)), (float(box.width), float(box.height))), fill="#ffffff", stroke="#adb5bd")
        )
        line_height = FURNITURE_FONT_SIZE * LINE_HEIGHT_FACTOR
        text_y = float(box.y) + 8.0 + FURNITURE_FONT_SIZE
        for raw_line in box.text.split("\n"):
            for line in wrap_label(raw_line, box.width - 16.0, FURNITURE_FONT_SIZE):
                shapes.append(
                    Shape(
                        "text",
                        f"{cls}-text",
                        ((float(box.x) + 8.0, text_y),),
                        text=line,
                        font_size=FURNITURE_FONT_SIZE,
                        fill="#343a40",
                    )
                )
                text_y += line_height


def render_page_svg(scene: PageScene) -> str:
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(scene.width),
            "height": str(scene.height),
            "viewBox": f"0 0 {scene.width} {scene.height}",
        },
    )
    for shape in scene.shapes:
        if shape.kind == "rect":
            (x, y), (w, h) = shape.points
            attrs = {
                "class": shape.cls,
                "x": f"{x:g}",
                "y": f"{y:g}",
                "width": f"{w:g}",
                "height": f"{h:g}",
                "fill": shape.fill or "none",
                "stroke": shape.stroke or "none",
                "rx": "4",
            }
            if shape.dashed:
                attrs["stroke-dasharray"] = "8 4"
            ET.SubElement(svg, "rect", attrs)
        elif shape.kind == "line":
            attrs = {
                "class": shape.cls,
                "points": " ".join(f"{px:g},{py:g}" for px, py in shape.points),
                "fill": "none",
                "stroke": shape.stroke or "#495057",
                "stroke-width": "1.5",
            }
            if shape.dashed:
                attrs["stroke-dasharray"] = "8 4"
            ET.SubElement(svg, "polyline", attrs)
        elif shape.kind == "polygon":
            ET.SubElement(
                svg,
                "polygon",
                {
                    "class": shape.cls,
                    "points": " ".join(f"{px:g},{py:g}" for px, py in shape.points),
                    "fill": shape.fill or "#495057",
                },
            )
        elif shape.kind == "icon" and shape.href:
            (x, y), (w, h) = shape.points
            ET.SubElement(
                svg,
                "image",
                {
                    "class": shape.cls,
                    "x": f"{x:g}",
                    "y": f"{y:g}",
                    "width": f"{w:g}",
                    "height": f"{h:g}",
                    "href": shape.href,
                },
            )
        elif shape.kind == "text":
            ((x, y),) = shape.points
            attrs = {
                "class": shape.cls,
                "x": f"{x:g}",
                "y": f"{y:g}",
                "font-family": "Helvetica, Arial, sans-serif",
                "font-size": str(shape.font_size),
                "fill": shape.fill or "#212529",
            }
            if shape.bold:
                attrs["font-weight"] = "bold"
            if shape.anchor != "start":
                attrs["text-anchor"] = shape.anchor
            element = ET.SubElement(svg, "text", attrs)
            element.text = shape.text
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode")


def write_previews(pages: list[tuple[str, Diagram]], output_dir: Path) -> list[Path]:
    """Write preview-page-<n>.svg for every page, plus .png when a backend exists."""

    output_dir = Path(output_dir)
    written: list[Path] = []
    backend = _png_backend()
    for index, (page_name, diagram) in enumerate(pages, start=1):
        scene = build_scene(page_name, diagram)
        svg_path = output_dir / f"preview-page-{index}.svg"
        svg_path.write_text(render_page_svg(scene), encoding="utf-8")
        written.append(svg_path)
        if backend is not None:
            png_path = output_dir / f"preview-page-{index}.png"
            if _write_png(backend, scene, png_path):
                written.append(png_path)
    return written


def _png_backend():
    """Return ("pil", modules) or ("matplotlib", pyplot), or None when unavailable."""

    try:
        from PIL import Image, ImageDraw  # type: ignore[import-not-found]

        return ("pil", (Image, ImageDraw))
    except ImportError:
        pass
    try:
        import matplotlib  # type: ignore[import-not-found]

        matplotlib.use("Agg")
        from matplotlib import pyplot  # type: ignore[import-not-found]

        return ("matplotlib", pyplot)
    except ImportError:
        return None


def _write_png(backend, scene: PageScene, path: Path) -> bool:
    try:
        if backend[0] == "pil":
            _write_png_pil(backend[1], scene, path)
        else:
            _write_png_matplotlib(backend[1], scene, path)
        return True
    except Exception:  # pragma: no cover - PNG output is best-effort
        return False


def _write_png_pil(modules, scene: PageScene, path: Path) -> None:
    Image, ImageDraw = modules
    image = Image.new("RGB", (scene.width, scene.height), "#ffffff")
    draw = ImageDraw.Draw(image)
    for shape in scene.shapes:
        if shape.kind == "icon":
            # Raster backends cannot rasterize the embedded SVG; draw the
            # brand-color marker fallback instead.
            (x, y), (w, h) = shape.points
            draw.rectangle([x, y, x + w, y + h], fill=shape.fill or "#6c757d")
            tx = x + w / 2.0 - estimate_text_width(shape.text, 11) / 2.0
            draw.text((tx, y + h / 2.0 - 6), shape.text, fill="#ffffff")
        elif shape.kind == "rect":
            (x, y), (w, h) = shape.points
            draw.rectangle([x, y, x + w, y + h], fill=shape.fill, outline=shape.stroke)
        elif shape.kind == "line":
            draw.line([(px, py) for px, py in shape.points], fill=shape.stroke or "#495057", width=2)
        elif shape.kind == "polygon":
            draw.polygon([(px, py) for px, py in shape.points], fill=shape.fill or "#495057")
        elif shape.kind == "text":
            ((x, y),) = shape.points
            if shape.anchor == "middle":
                x -= estimate_text_width(shape.text, shape.font_size) / 2.0
            draw.text((x, y - shape.font_size), shape.text, fill=shape.fill or "#212529")
    image.save(path, format="PNG")


def _write_png_matplotlib(pyplot, scene: PageScene, path: Path) -> None:
    dpi = 100.0
    figure = pyplot.figure(figsize=(scene.width / dpi, scene.height / dpi), dpi=dpi)
    axes = figure.add_axes([0, 0, 1, 1])
    axes.set_xlim(0, scene.width)
    axes.set_ylim(scene.height, 0)
    axes.axis("off")
    for shape in scene.shapes:
        if shape.kind == "icon":
            (x, y), (w, h) = shape.points
            axes.add_patch(pyplot.Rectangle((x, y), w, h, facecolor=shape.fill or "#6c757d"))
            axes.text(x + w / 2, y + h / 2, shape.text, fontsize=8, color="#ffffff", ha="center", va="center")
            continue
        if shape.kind == "rect":
            (x, y), (w, h) = shape.points
            axes.add_patch(
                pyplot.Rectangle(
                    (x, y),
                    w,
                    h,
                    facecolor=shape.fill or "none",
                    edgecolor=shape.stroke or "none",
                    linestyle="--" if shape.dashed else "-",
                )
            )
        elif shape.kind == "line":
            xs = [px for px, _ in shape.points]
            ys = [py for _, py in shape.points]
            axes.plot(xs, ys, color=shape.stroke or "#495057", linestyle="--" if shape.dashed else "-", linewidth=1.5)
        elif shape.kind == "polygon":
            axes.fill([px for px, _ in shape.points], [py for _, py in shape.points], color=shape.fill or "#495057")
        elif shape.kind == "text":
            ((x, y),) = shape.points
            axes.text(
                x,
                y,
                shape.text,
                fontsize=shape.font_size * 0.75,
                color=shape.fill or "#212529",
                ha="center" if shape.anchor == "middle" else "left",
                fontweight="bold" if shape.bold else "normal",
            )
    figure.savefig(path, format="png")
    pyplot.close(figure)

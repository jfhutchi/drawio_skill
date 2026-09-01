"""Load and dump the intermediate ``Diagram`` model as JSON.

This is the primary agent-facing entry point: the calling LLM authors the
model (semantic extraction, dedupe, grouping) and the helper does layout,
emission, and QA. JSON is always supported; YAML loads only when a ``yaml``
module happens to be importable (it is never a dependency).

Validation is a minimal hand-rolled structural check with JSON-path error
messages - no third-party schema library.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from .diagram_model import (
    Annotation,
    Boundary,
    Diagram,
    Edge,
    LegendItem,
    Node,
    Route,
    RouteAnimation,
)


class ModelValidationError(ValueError):
    """Raised when a model payload fails structural validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


_STR_FIELDS = {"title", "subtitle", "diagram_type", "audience", "direction", "layout_strategy"}
_STR_LIST_FIELDS = {"layers", "groups", "assumptions", "unknowns", "sources", "quality_checks"}

_NODE_FIELDS = {field.name for field in fields(Node)}
_EDGE_FIELDS = {field.name for field in fields(Edge)}
_ROUTE_FIELDS = {field.name for field in fields(Route)}
_ROUTE_ANIMATION_FIELDS = {field.name for field in fields(RouteAnimation)}
_BOUNDARY_FIELDS = {field.name for field in fields(Boundary)}
_LEGEND_FIELDS = {field.name for field in fields(LegendItem)}
_ANNOTATION_FIELDS = {field.name for field in fields(Annotation)}
_DIAGRAM_FIELDS = {field.name for field in fields(Diagram)}


def load_model(path: Path) -> Diagram:
    """Load and validate a Diagram from a JSON (or YAML) model file."""

    payload = _load_payload(Path(path))
    return diagram_from_dict(payload)


def dump_model(diagram: Diagram, path: Path) -> None:
    Path(path).write_text(
        json.dumps(diagram_to_dict(diagram), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def diagram_to_dict(diagram: Diagram) -> dict[str, Any]:
    return asdict(diagram)


def diagram_from_dict(payload: Any) -> Diagram:
    """Validate a payload and build a Diagram. Raises ModelValidationError."""

    if isinstance(payload, dict) and set(payload) == {"diagram"}:
        payload = payload["diagram"]
    errors = validate_model_payload(payload)
    if errors:
        raise ModelValidationError(errors)

    routes: list[Route] = []
    for item in payload.get("routes", []):
        animation = RouteAnimation(**item.get("animation", {}))
        route_values = {key: value for key, value in item.items() if key != "animation"}
        routes.append(Route(**route_values, animation=animation))

    return Diagram(
        title=payload["title"],
        subtitle=payload.get("subtitle", ""),
        diagram_type=payload.get("diagram_type", "enterprise"),
        audience=payload.get("audience", "architect"),
        direction=payload.get("direction", "top-to-bottom"),
        layout_strategy=payload.get("layout_strategy", "layered"),
        layers=list(payload.get("layers", [])),
        groups=list(payload.get("groups", [])),
        boundaries=[Boundary(**item) for item in payload.get("boundaries", [])],
        nodes=[Node(**item) for item in payload.get("nodes", [])],
        edges=[Edge(**item) for item in payload.get("edges", [])],
        routes=routes,
        legends=[LegendItem(**item) for item in payload.get("legends", [])],
        annotations=[Annotation(**item) for item in payload.get("annotations", [])],
        assumptions=list(payload.get("assumptions", [])),
        unknowns=list(payload.get("unknowns", [])),
        sources=list(payload.get("sources", [])),
        quality_checks=list(payload.get("quality_checks", [])),
        metadata=dict(payload.get("metadata", {})),
    )


def validate_model_payload(payload: Any) -> list[str]:
    """Structural validation with JSON-path error messages."""

    if not isinstance(payload, dict):
        return [f"$: model must be a JSON object, got {type(payload).__name__}"]

    errors: list[str] = []
    for key in payload:
        if key not in _DIAGRAM_FIELDS:
            errors.append(f"$.{key}: unknown field (valid fields: {', '.join(sorted(_DIAGRAM_FIELDS))})")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("$.title: required non-empty string")
    if not isinstance(payload.get("nodes"), list) or not payload.get("nodes"):
        errors.append("$.nodes: at least one node is required")
    if "edges" not in payload or not isinstance(payload.get("edges"), list):
        errors.append("$.edges: required list (may be empty)")
    for name in _STR_FIELDS - {"title"}:
        if name in payload and not isinstance(payload[name], str):
            errors.append(f"$.{name}: must be a string")
    for name in _STR_LIST_FIELDS:
        value = payload.get(name, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"$.{name}: must be a list of strings")
    if "metadata" in payload and not isinstance(payload["metadata"], dict):
        errors.append("$.metadata: must be an object")

    boundary_ids = _validate_items(payload, "boundaries", _BOUNDARY_FIELDS, {"id", "label"}, errors)
    node_ids = _validate_items(payload, "nodes", _NODE_FIELDS, {"id", "label"}, errors)
    edge_ids = _validate_items(payload, "edges", _EDGE_FIELDS, {"id", "source", "target", "label"}, errors)
    route_ids = _validate_routes(payload, errors)
    annotation_ids = _validate_items(payload, "annotations", _ANNOTATION_FIELDS, {"id", "text"}, errors)
    _validate_items(payload, "legends", _LEGEND_FIELDS, {"label", "meaning"}, errors, id_field=None)

    seen: dict[str, str] = {}
    for section, ids in (
        ("boundaries", boundary_ids),
        ("nodes", node_ids),
        ("edges", edge_ids),
        ("routes", route_ids),
        ("annotations", annotation_ids),
    ):
        for index, item_id in ids:
            path = f"$.{section}[{index}].id"
            if item_id in seen:
                errors.append(f"{path}: duplicate id {item_id!r} (already used at {seen[item_id]})")
            else:
                seen[item_id] = path

    node_id_set = {item_id for _, item_id in node_ids}
    edges = payload.get("edges", [])
    if isinstance(edges, list):
        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                continue
            for endpoint in ("source", "target"):
                value = edge.get(endpoint)
                if isinstance(value, str) and value and value not in node_id_set:
                    errors.append(f"$.edges[{index}].{endpoint}: references missing node id {value!r}")

    boundary_id_set = {item_id for _, item_id in boundary_ids}
    nodes = payload.get("nodes", [])
    if isinstance(nodes, list):
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            group = node.get("group")
            if isinstance(group, str) and group and group not in boundary_id_set:
                errors.append(f"$.nodes[{index}].group: references missing boundary id {group!r}")

    edge_lookup = {
        edge.get("id"): edge
        for edge in edges
        if isinstance(edge, dict) and isinstance(edge.get("id"), str) and edge.get("id")
    }
    routes = payload.get("routes", [])
    if isinstance(routes, list):
        for index, route in enumerate(routes):
            if not isinstance(route, dict):
                continue
            route_edge_ids = route.get("edge_ids")
            if not isinstance(route_edge_ids, list):
                continue
            valid_edge_ids = [
                edge_id for edge_id in route_edge_ids
                if isinstance(edge_id, str) and edge_id.strip()
            ]
            missing = [edge_id for edge_id in valid_edge_ids if edge_id not in edge_lookup]
            for edge_id in missing:
                errors.append(f"$.routes[{index}].edge_ids: references missing edge id {edge_id!r}")
            if len(valid_edge_ids) == len(route_edge_ids) and not missing:
                errors.extend(_validate_route_chain(valid_edge_ids, edge_lookup, f"$.routes[{index}].edge_ids"))

    return errors


def _validate_routes(payload: dict[str, Any], errors: list[str]) -> list[tuple[int, str]]:
    value = payload.get("routes", [])
    if not isinstance(value, list):
        errors.append("$.routes: must be a list")
        return []

    ids: list[tuple[int, str]] = []
    for index, item in enumerate(value):
        path = f"$.routes[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: must be an object")
            continue
        for key in item:
            if key not in _ROUTE_FIELDS:
                errors.append(f"{path}.{key}: unknown field (valid fields: {', '.join(sorted(_ROUTE_FIELDS))})")
        for name in ("id", "label"):
            field_value = item.get(name)
            if not isinstance(field_value, str) or not field_value.strip():
                errors.append(f"{path}.{name}: required non-empty string")
        edge_ids = item.get("edge_ids")
        if not isinstance(edge_ids, list) or not edge_ids:
            errors.append(f"{path}.edge_ids: required non-empty list of edge ids")
        elif any(not isinstance(edge_id, str) or not edge_id.strip() for edge_id in edge_ids):
            errors.append(f"{path}.edge_ids: all edge ids must be non-empty strings")
        description = item.get("description")
        if description is not None and not isinstance(description, str):
            errors.append(f"{path}.description: must be a string or null")
        if "metadata" in item and not isinstance(item["metadata"], dict):
            errors.append(f"{path}.metadata: must be an object")
        _validate_route_animation(item.get("animation", {}), f"{path}.animation", errors)
        if isinstance(item.get("id"), str) and item["id"].strip():
            ids.append((index, item["id"]))
    return ids


def _validate_route_animation(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: must be an object")
        return
    for key in value:
        if key not in _ROUTE_ANIMATION_FIELDS:
            errors.append(
                f"{path}.{key}: unknown field (valid fields: {', '.join(sorted(_ROUTE_ANIMATION_FIELDS))})"
            )
    style = value.get("style", "both")
    if not isinstance(style, str) or style not in {"both", "packet", "flow"}:
        errors.append(f"{path}.style: must be one of both, packet, flow")
    speed = value.get("speed", 1.0)
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or speed <= 0 or speed > 10:
        errors.append(f"{path}.speed: must be a number greater than 0 and at most 10")
    dwell_ms = value.get("dwell_ms", 350)
    if isinstance(dwell_ms, bool) or not isinstance(dwell_ms, int) or dwell_ms < 0 or dwell_ms > 60000:
        errors.append(f"{path}.dwell_ms: must be an integer between 0 and 60000")
    loop = value.get("loop", False)
    if not isinstance(loop, bool):
        errors.append(f"{path}.loop: must be a boolean")


def _validate_route_chain(
    edge_ids: list[str],
    edge_lookup: dict[str, dict[str, Any]],
    path: str,
) -> list[str]:
    if len(edge_ids) < 2:
        return []

    first = edge_lookup[edge_ids[0]]
    second = edge_lookup[edge_ids[1]]
    first_nodes = {first.get("source"), first.get("target")}
    second_nodes = {second.get("source"), second.get("target")}
    shared = {node for node in first_nodes & second_nodes if isinstance(node, str)}
    if not shared:
        return [f"{path}: edge {edge_ids[0]!r} and {edge_ids[1]!r} are not contiguous"]

    current = first.get("target") if first.get("target") in shared else sorted(shared)[0]
    for position, edge_id in enumerate(edge_ids[1:], start=1):
        edge = edge_lookup[edge_id]
        if current == edge.get("source"):
            current = edge.get("target")
        elif current == edge.get("target"):
            current = edge.get("source")
        else:
            return [
                f"{path}: edge {edge_id!r} at position {position} does not continue from node {current!r}"
            ]
    return []


def _validate_items(
    payload: dict[str, Any],
    section: str,
    valid_fields: set[str],
    required: set[str],
    errors: list[str],
    id_field: str | None = "id",
) -> list[tuple[int, str]]:
    """Validate one list-of-objects section; return (index, id) pairs found."""

    value = payload.get(section, [])
    if not isinstance(value, list):
        errors.append(f"$.{section}: must be a list")
        return []
    ids: list[tuple[int, str]] = []
    for index, item in enumerate(value):
        path = f"$.{section}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: must be an object")
            continue
        for key in item:
            if key not in valid_fields:
                errors.append(f"{path}.{key}: unknown field (valid fields: {', '.join(sorted(valid_fields))})")
        for name in required:
            field_value = item.get(name)
            if not isinstance(field_value, str) or not field_value.strip():
                errors.append(f"{path}.{name}: required non-empty string")
        if "metadata" in item and not isinstance(item["metadata"], dict):
            errors.append(f"{path}.metadata: must be an object")
        for name in ("x", "y", "width", "height"):
            if name in item and item[name] is not None and not isinstance(item[name], int):
                errors.append(f"{path}.{name}: must be an integer or null")
        if id_field and isinstance(item.get(id_field), str) and item[id_field].strip():
            ids.append((index, item[id_field]))
    return ids


def _load_payload(path: Path) -> Any:
    if not path.exists():
        raise ModelValidationError([f"$: model file does not exist: {path}"])
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            raise ModelValidationError(
                [f"$: {path.name} is YAML but no yaml module is importable; provide the model as JSON instead"]
            ) from None
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelValidationError([f"$: model file is not valid JSON: {exc}"]) from None

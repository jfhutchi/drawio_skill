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

from .diagram_model import Annotation, Boundary, Diagram, Edge, LegendItem, Node


class ModelValidationError(ValueError):
    """Raised when a model payload fails structural validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


_STR_FIELDS = {"title", "subtitle", "diagram_type", "audience", "direction", "layout_strategy"}
_STR_LIST_FIELDS = {"layers", "groups", "assumptions", "unknowns", "sources", "quality_checks"}

_NODE_FIELDS = {field.name for field in fields(Node)}
_EDGE_FIELDS = {field.name for field in fields(Edge)}
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
    annotation_ids = _validate_items(payload, "annotations", _ANNOTATION_FIELDS, {"id", "text"}, errors)
    _validate_items(payload, "legends", _LEGEND_FIELDS, {"label", "meaning"}, errors, id_field=None)

    seen: dict[str, str] = {}
    for section, ids in (
        ("boundaries", boundary_ids),
        ("nodes", node_ids),
        ("edges", edge_ids),
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

    return errors


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

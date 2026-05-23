"""Structured intermediate diagram model.

The rest of the package consumes this model instead of generating draw.io XML
directly from prose. That keeps extraction, review, layout, and XML generation
separate and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Metadata = dict[str, Any]


@dataclass(slots=True)
class Node:
    """A diagram component or actor."""

    id: str
    label: str
    node_type: str = "component"
    icon: str | None = None
    group: str | None = None
    layer: str | None = None
    description: str | None = None
    technology: str | None = None
    risk_level: str | None = None
    metadata: Metadata = field(default_factory=dict)
    x: int | None = None
    y: int | None = None
    width: int = 150
    height: int = 70


@dataclass(slots=True)
class Edge:
    """A directional relationship between two nodes."""

    id: str
    source: str
    target: str
    label: str
    protocol: str | None = None
    direction: str = "forward"
    data_classification: str | None = None
    security_control: str | None = None
    style: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class Boundary:
    """A logical, trust, environment, cloud, or network boundary."""

    id: str
    label: str
    boundary_type: str = "logical"
    description: str | None = None
    metadata: Metadata = field(default_factory=dict)
    x: int | None = None
    y: int | None = None
    width: int = 760
    height: int = 420


@dataclass(slots=True)
class LegendItem:
    """A legend entry explaining colors, shapes, or line semantics."""

    label: str
    meaning: str
    color: str | None = None


@dataclass(slots=True)
class Annotation:
    """Supplemental text rendered near the diagram or in Markdown outputs."""

    id: str
    text: str
    severity: str = "info"


@dataclass(slots=True)
class Diagram:
    """Top-level model for one draw.io page."""

    title: str
    subtitle: str = ""
    diagram_type: str = "enterprise"
    audience: str = "architect"
    direction: str = "top-to-bottom"
    layout_strategy: str = "layered"
    layers: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    boundaries: list[Boundary] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    legends: list[LegendItem] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    quality_checks: list[str] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)

    def node_ids(self) -> set[str]:
        return {node.id for node in self.nodes}

    def boundary_ids(self) -> set[str]:
        return {boundary.id for boundary in self.boundaries}

    def all_ids(self) -> list[str]:
        return [
            *[boundary.id for boundary in self.boundaries],
            *[node.id for node in self.nodes],
            *[edge.id for edge in self.edges],
            *[annotation.id for annotation in self.annotations],
        ]

    def add_quality_check(self, text: str) -> None:
        if text not in self.quality_checks:
            self.quality_checks.append(text)

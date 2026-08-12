"""Deterministic edge-aware layered layout (Sugiyama-lite) for all diagrams.

One core drives the vertical, horizontal, and enterprise layouts:

1. Rank assignment: pattern/group columns are hard rank constraints;
   otherwise longest-path over the edge graph (back edges detected by DFS
   in stable id order and excluded from ranking).
2. Within-rank ordering: longest-path depth over same-rank edges first
   (kills upward primary flows), refined by barycenter sweeps with
   deterministic node-id tie-breaking.
3. Coordinates: column positions from cumulative max extents; shorter
   columns centered against the tallest; every node/boundary x/y/width/
   height snapped to the draw.io grid. Column gap = 2 * BOUNDARY_PAD +
   channel width, so adjacent boundary frames can never overlap.
4. Routing: every edge gets exit/entry ports, planned waypoints through
   reserved channels in the inter-column gaps (parallel edges offset by
   LANE_STEP), and a full polyline in edge.metadata["route"] consumed by
   the preview renderer and QA. The generator - not draw.io's runtime
   router - owns every route.

Works in flow/cross space: for horizontal layouts flow = x, for vertical
layouts flow = y; ``_Axis`` maps back to page coordinates.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from .diagram_model import Diagram, Edge, Node


GRID_SIZE = 10
BOUNDARY_PAD = 24
BOUNDARY_LABEL_PAD = 40
NODE_GAP = 40
CHANNEL_MIN = 48
LANE_STEP = 12
FLOW_MARGIN = 80
CROSS_MARGIN = 160
STUB = 12  # clearance for skip-edge excursions out of a column

VERTICAL_LAYERS = [
    "users",
    "edge",
    "application",
    "data",
    "platform",
    "security",
    "observability",
    "operations",
]

HORIZONTAL_TYPES = {"cicd", "workflow", "sequence", "code"}
ENTERPRISE_HORIZONTAL_TYPES = {"enterprise", "cloud"}
MIN_ENTERPRISE_NODE_WIDTH = 190
MIN_ENTERPRISE_NODE_HEIGHT = 90
ENTERPRISE_GROUP_ORDER = [
    "boundary-source-control",
    "boundary-automation-control",
    "boundary-customer-infrastructure",
    "boundary-controller-workspace",
    "boundary-reporting-evidence",
    "boundary-optional-external-storage",
    "boundary-report-consumers",
]

AWS_GROUP_ORDER = [
    "boundary-aws-external",
    "boundary-aws-account",
    "boundary-aws-edge",
    "boundary-aws-compute",
    "boundary-aws-data",
    "boundary-aws-analytics",
    "boundary-aws-consumers",
]

AZURE_GROUP_ORDER = [
    "boundary-azure-external",
    "boundary-azure-global",
    "boundary-azure-region-primary",
    "boundary-azure-region-secondary",
    "boundary-azure-data",
    "boundary-azure-identity",
    "boundary-azure-operations",
]

DATA_PLATFORM_GROUP_ORDER = [
    "boundary-data-sources",
    "boundary-data-ingest",
    "boundary-data-process",
    "boundary-data-store",
    "boundary-data-serve",
    "boundary-data-governance",
]

PATTERN_GROUP_ORDER = {
    "aws-reference": AWS_GROUP_ORDER,
    "azure-reference": AZURE_GROUP_ORDER,
    "data-platform-pipeline": DATA_PLATFORM_GROUP_ORDER,
    "enterprise-reference": ENTERPRISE_GROUP_ORDER,
}


def infer_layer(node: Node) -> str:
    node_type = (node.node_type or "").lower()
    label = node.label.lower()
    if node_type in {"actor", "user", "consumer"} or any(term in label for term in ["user", "consumer", "reviewer", "engineer"]):
        return "users"
    if node_type in {"cdn", "gateway", "waf", "firewall", "network"}:
        return "edge"
    if node_type in {"database", "cache", "queue", "data", "object_storage", "workbook", "report"} or any(term in label for term in ["postgres", "sql", "redis", "queue", "kafka", "rabbitmq", "sfs", "report", "workbook", "excel"]):
        return "data"
    if node_type in {"kubernetes", "container", "server", "linux_server", "windows_server", "terraform", "ansible"}:
        return "platform"
    if node_type in {"identity", "secret", "security"} or any(term in label for term in ["vault", "iam", "sso", "mfa", "rbac", "pam", "siem"]):
        return "security"
    if node_type in {"monitoring", "logging", "dashboard"} or any(term in label for term in ["prometheus", "grafana", "logs", "metrics", "traces", "monitor"]):
        return "observability"
    if node_type in {"process", "deployment", "repository", "artifact"}:
        return "operations"
    return "application"


def apply_layout(diagram: Diagram) -> Diagram:
    """Return a laid-out copy of the model without mutating the input."""

    laid_out = deepcopy(diagram)
    diagram_type = laid_out.diagram_type.lower()
    horizontal = (
        diagram_type in HORIZONTAL_TYPES
        or diagram_type in ENTERPRISE_HORIZONTAL_TYPES
        or laid_out.direction.lower() == "left-to-right"
    )

    for node in laid_out.nodes:
        if not node.layer:
            node.layer = infer_layer(node)
        _normalize_node_size(laid_out, node)
        node.width = _snap_up(node.width)
        node.height = _snap_up(node.height)

    if horizontal and diagram_type in ENTERPRISE_HORIZONTAL_TYPES:
        _layout_enterprise_horizontal(laid_out)
    elif horizontal:
        _layout_horizontal(laid_out)
    else:
        _layout_vertical(laid_out)

    _layout_boundaries(laid_out)
    return laid_out


def _normalize_node_size(diagram: Diagram, node: Node) -> None:
    if diagram.diagram_type.lower() not in ENTERPRISE_HORIZONTAL_TYPES:
        return
    node.width = max(node.width, MIN_ENTERPRISE_NODE_WIDTH)
    node.height = max(node.height, MIN_ENTERPRISE_NODE_HEIGHT)


def _layout_enterprise_horizontal(diagram: Diagram) -> None:
    grouped = _group_enterprise_nodes(diagram.nodes)
    pattern_id = str(diagram.metadata.get("visual_pattern_id") or "") or None
    ranks: dict[str, int] = {}
    for rank, group_id in enumerate(_ordered_group_ids(grouped, pattern_id)):
        for node in grouped[group_id]:
            ranks[node.id] = rank
    _layered_layout(diagram, ranks, _Axis(horizontal=True))


def _layout_horizontal(diagram: Diagram) -> None:
    ranks = _longest_path_ranks(diagram.nodes, diagram.edges)
    _layered_layout(diagram, ranks, _Axis(horizontal=True))


def _layout_vertical(diagram: Diagram) -> None:
    layers = diagram.layers or VERTICAL_LAYERS
    layer_rank = {layer: index for index, layer in enumerate(layers)}
    fallback = layer_rank.get("application", 0)
    ranks = {node.id: layer_rank.get(node.layer or "", fallback) for node in diagram.nodes}
    _layered_layout(diagram, ranks, _Axis(horizontal=False), flow_margin=140, cross_margin=80)


def _group_enterprise_nodes(nodes: list[Node]) -> dict[str, list[Node]]:
    grouped: dict[str, list[Node]] = {}
    for node in nodes:
        group_id = node.group or f"__layer_{node.layer or infer_layer(node)}"
        grouped.setdefault(group_id, []).append(node)
    return grouped


def _ordered_group_ids(grouped: dict[str, list[Node]], pattern_id: str | None = None) -> list[str]:
    orderings = []
    if pattern_id and pattern_id in PATTERN_GROUP_ORDER:
        orderings.append(PATTERN_GROUP_ORDER[pattern_id])
    orderings.append(ENTERPRISE_GROUP_ORDER)
    seen: set[str] = set()
    known: list[str] = []
    for ordering in orderings:
        for group_id in ordering:
            if group_id in grouped and group_id not in seen:
                known.append(group_id)
                seen.add(group_id)
    unknown = sorted(group_id for group_id in grouped if group_id not in seen)
    return [*known, *unknown]


def _layout_boundaries(diagram: Diagram) -> None:
    if not diagram.boundaries:
        return

    for boundary in diagram.boundaries:
        member_nodes = [node for node in diagram.nodes if node.group == boundary.id]
        if member_nodes:
            min_x = _snap_down(min((node.x or 0) for node in member_nodes) - BOUNDARY_PAD)
            min_y = _snap_down(min((node.y or 0) for node in member_nodes) - BOUNDARY_LABEL_PAD)
            max_x = _snap_up(max((node.x or 0) + node.width for node in member_nodes) + BOUNDARY_PAD)
            max_y = _snap_up(max((node.y or 0) + node.height for node in member_nodes) + BOUNDARY_PAD)
            boundary.x = min_x
            boundary.y = min_y
            boundary.width = max(260, max_x - min_x)
            boundary.height = max(170, max_y - min_y)
        else:
            boundary.x = boundary.x if boundary.x is not None else 40
            boundary.y = boundary.y if boundary.y is not None else 110


# ---------------------------------------------------------------------------
# Layered layout core


def _snap_down(value: float) -> int:
    return int(value // GRID_SIZE) * GRID_SIZE


def _snap_up(value: float) -> int:
    return -_snap_down(-value)


def route_midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Point halfway along a polyline's total length."""

    if not points:
        return (0.0, 0.0)
    segments = list(zip(points, points[1:]))
    total = sum(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 for (ax, ay), (bx, by) in segments)
    if total <= 0:
        return points[0]
    remaining = total / 2.0
    for (ax, ay), (bx, by) in segments:
        seg_len = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if seg_len >= remaining and seg_len > 0:
            t = remaining / seg_len
            return (ax + (bx - ax) * t, ay + (by - ay) * t)
        remaining -= seg_len
    return points[-1]


@dataclass(frozen=True, slots=True)
class _Axis:
    """Maps flow/cross space onto page x/y. Horizontal: flow = x."""

    horizontal: bool

    def point(self, flow: float, cross: float) -> tuple[float, float]:
        return (flow, cross) if self.horizontal else (cross, flow)

    def set_position(self, node: Node, flow: int, cross: int) -> None:
        if self.horizontal:
            node.x, node.y = flow, cross
        else:
            node.x, node.y = cross, flow

    def flow_extent(self, node: Node) -> int:
        return node.width if self.horizontal else node.height

    def cross_extent(self, node: Node) -> int:
        return node.height if self.horizontal else node.width

    def port(self, flow_rel: float, cross_rel: float) -> tuple[float, float]:
        return (flow_rel, cross_rel) if self.horizontal else (cross_rel, flow_rel)


@dataclass(slots=True)
class _Placed:
    node: Node
    rank: int
    order: int = 0
    flow: float = 0.0
    cross: float = 0.0

    def flow_mid(self, axis: _Axis) -> float:
        return self.flow + axis.flow_extent(self.node) / 2

    def cross_mid(self, axis: _Axis) -> float:
        return self.cross + axis.cross_extent(self.node) / 2


@dataclass(slots=True)
class _Route:
    edge: Edge
    kind: str  # straight | stack | jog | skip | long | backward
    gaps: list[int] = field(default_factory=list)
    lanes: dict[int, int] = field(default_factory=dict)
    bottom_lane: int | None = None


def _layered_layout(
    diagram: Diagram,
    ranks: dict[str, int],
    axis: _Axis,
    flow_margin: int = FLOW_MARGIN,
    cross_margin: int = CROSS_MARGIN,
) -> None:
    if not diagram.nodes:
        return
    # 1. Contiguous rank indexes in stable order.
    used_ranks = sorted({ranks.get(node.id, 0) for node in diagram.nodes})
    rank_index = {rank: index for index, rank in enumerate(used_ranks)}
    placed = {node.id: _Placed(node, rank_index[ranks.get(node.id, 0)]) for node in diagram.nodes}
    columns: list[list[_Placed]] = [[] for _ in used_ranks]
    for node in diagram.nodes:
        columns[placed[node.id].rank].append(placed[node.id])

    edges = [edge for edge in diagram.edges if edge.source in placed and edge.target in placed]

    # 2. Within-column order: same-column longest-path depth, then id.
    depth = _same_rank_depths(placed, edges)
    for column in columns:
        column.sort(key=lambda item: (depth[item.node.id], item.node.id))
        for order, item in enumerate(column):
            item.order = order

    # 3. Barycenter sweeps (down, up, down, up) with deterministic ties.
    neighbors = _neighbor_map(placed, edges)
    for sweep in range(4):
        forward = sweep % 2 == 0
        column_range = range(1, len(columns)) if forward else range(len(columns) - 2, -1, -1)
        for col_index in column_range:
            adjacent = col_index - 1 if forward else col_index + 1
            column = columns[col_index]
            barycenters = {}
            for item in column:
                positions = [placed[other].order for other in neighbors[item.node.id] if placed[other].rank == adjacent]
                barycenters[item.node.id] = sum(positions) / len(positions) if positions else float(item.order)
            column.sort(key=lambda item: (depth[item.node.id], barycenters[item.node.id], item.node.id))
            for order, item in enumerate(column):
                item.order = order

    # 4. Cross positions: stack per column, center against the tallest.
    column_heights: list[int] = []
    for column in columns:
        height = sum(axis.cross_extent(item.node) for item in column) + NODE_GAP * (len(column) - 1)
        column_heights.append(height)
    tallest = max(column_heights)
    for column, height in zip(columns, column_heights):
        cross = cross_margin + _snap_down((tallest - height) / 2)
        for item in column:
            item.cross = cross
            cross += axis.cross_extent(item.node) + NODE_GAP

    # 5. Classify routes and reserve channel lanes per inter-column gap.
    routes = [_classify_route(edge, placed, axis) for edge in sorted(edges, key=lambda e: e.id)]
    gap_lanes: dict[int, list[str]] = {}
    for route in routes:
        for gap in route.gaps:
            gap_lanes.setdefault(gap, []).append(route.edge.id)
    for gap, edge_ids in gap_lanes.items():
        for route in routes:
            if route.edge.id in edge_ids and gap in route.gaps:
                route.lanes[gap] = edge_ids.index(route.edge.id)
    bottom_edges = [route for route in routes if route.kind in {"long", "backward"}]
    for index, route in enumerate(bottom_edges):
        route.bottom_lane = index

    # 6. Flow positions with channel-aware gaps.
    column_extents = [max(axis.flow_extent(item.node) for item in column) for column in columns]
    column_flows: list[int] = []
    flow = flow_margin
    for col_index, extent in enumerate(column_extents):
        column_flows.append(_snap_up(flow))
        lane_count = len(gap_lanes.get(col_index, []))
        channel = max(CHANNEL_MIN, LANE_STEP * lane_count + 36)
        flow = column_flows[col_index] + extent + 2 * BOUNDARY_PAD + channel

    for column, col_flow in zip(columns, column_flows):
        for item in column:
            item.flow = col_flow
            axis.set_position(item.node, col_flow, _snap_up(item.cross))
            item.cross = float(_snap_up(item.cross))

    # 7. Concrete routes: ports, waypoints, and full polylines.
    content_bottom = max(item.cross + axis.cross_extent(item.node) for item in placed.values())
    lane_base = content_bottom + 60

    def lane_flow(gap: int, lane: int) -> float:
        return column_flows[gap] + column_extents[gap] + 36 + LANE_STEP * lane

    for route in routes:
        _apply_route(route, placed, axis, lane_flow, lane_base)


def _same_rank_depths(placed: dict[str, _Placed], edges: list[Edge]) -> dict[str, int]:
    """Longest-path depth over same-rank edges (cycles broken deterministically)."""

    same_rank = [edge for edge in edges if placed[edge.source].rank == placed[edge.target].rank and edge.source != edge.target]
    order = sorted(placed)
    non_back = _drop_back_edges(order, same_rank)
    return _longest_path(order, non_back)


def _longest_path_ranks(nodes: list[Node], edges: list[Edge]) -> dict[str, int]:
    node_ids = {node.id for node in nodes}
    usable = [edge for edge in edges if edge.source in node_ids and edge.target in node_ids and edge.source != edge.target]
    order = sorted(node_ids)
    non_back = _drop_back_edges(order, usable)
    return _longest_path(order, non_back)


def _drop_back_edges(order: list[str], edges: list[Edge]) -> list[tuple[str, str]]:
    """DFS in stable order; back edges (cycle closers) are excluded from ranking."""

    outgoing: dict[str, list[str]] = {node_id: [] for node_id in order}
    for edge in edges:
        outgoing[edge.source].append(edge.target)
    for targets in outgoing.values():
        targets.sort()

    state: dict[str, int] = {}  # 1 = in stack, 2 = done
    kept: list[tuple[str, str]] = []
    for start in order:
        if state.get(start):
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        state[start] = 1
        while stack:
            current, next_index = stack[-1]
            targets = outgoing[current]
            if next_index >= len(targets):
                state[current] = 2
                stack.pop()
                continue
            stack[-1] = (current, next_index + 1)
            target = targets[next_index]
            if state.get(target) == 1:
                continue  # back edge: drop from ranking
            kept.append((current, target))
            if not state.get(target):
                state[target] = 1
                stack.append((target, 0))
    return kept


def _longest_path(order: list[str], edge_pairs: list[tuple[str, str]]) -> dict[str, int]:
    pairs = sorted({(source, target) for source, target in edge_pairs if source != target})
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in order}
    indegree = {node_id: 0 for node_id in order}
    for source, target in pairs:
        outgoing[source].append(target)
        indegree[target] += 1
    depth = {node_id: 0 for node_id in order}
    ready = sorted(node_id for node_id in order if indegree[node_id] == 0)
    index = 0
    while index < len(ready):
        current = ready[index]
        index += 1
        for target in outgoing[current]:
            depth[target] = max(depth[target], depth[current] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return depth


def _neighbor_map(placed: dict[str, _Placed], edges: list[Edge]) -> dict[str, list[str]]:
    neighbors: dict[str, list[str]] = {node_id: [] for node_id in placed}
    for edge in sorted(edges, key=lambda e: e.id):
        neighbors[edge.source].append(edge.target)
        neighbors[edge.target].append(edge.source)
    return neighbors


def _classify_route(edge: Edge, placed: dict[str, _Placed], axis: _Axis) -> _Route:
    source = placed[edge.source]
    target = placed[edge.target]
    a, b = source.rank, target.rank
    if a == b:
        if abs(source.order - target.order) == 1:
            return _Route(edge, "stack")
        return _Route(edge, "skip", gaps=[a])
    if b == a + 1:
        if abs(source.cross_mid(axis) - target.cross_mid(axis)) < GRID_SIZE:
            return _Route(edge, "straight")
        return _Route(edge, "jog", gaps=[a])
    if b > a + 1:
        return _Route(edge, "long", gaps=sorted({a, b - 1}))
    if b == a - 1:
        if abs(source.cross_mid(axis) - target.cross_mid(axis)) < GRID_SIZE:
            return _Route(edge, "straight")
        return _Route(edge, "jog", gaps=[b])
    return _Route(edge, "backward", gaps=sorted({a - 1, b}))


def _apply_route(
    route: _Route,
    placed: dict[str, _Placed],
    axis: _Axis,
    lane_flow,
    lane_base: float,
) -> None:
    edge = route.edge
    source = placed[edge.source]
    target = placed[edge.target]
    s_node, t_node = source.node, target.node
    backward_pair = target.rank < source.rank

    waypoints_fc: list[tuple[float, float]] = []
    if route.kind == "stack":
        downward = target.order > source.order
        exit_port = axis.port(0.5, 1.0 if downward else 0.0)
        entry_port = axis.port(0.5, 0.0 if downward else 1.0)
        start = (source.flow_mid(axis), source.cross + (axis.cross_extent(s_node) if downward else 0))
        end = (target.flow_mid(axis), target.cross + (0 if downward else axis.cross_extent(t_node)))
    elif route.kind == "skip":
        downward = target.order > source.order
        gap = route.gaps[0]
        lane = lane_flow(gap, route.lanes[gap])
        exit_port = axis.port(0.5, 1.0 if downward else 0.0)
        entry_port = axis.port(0.5, 0.0 if downward else 1.0)
        start = (source.flow_mid(axis), source.cross + (axis.cross_extent(s_node) if downward else 0))
        end = (target.flow_mid(axis), target.cross + (0 if downward else axis.cross_extent(t_node)))
        out_cross = start[1] + (STUB if downward else -STUB)
        in_cross = end[1] - (STUB if downward else -STUB)
        waypoints_fc = [(start[0], out_cross), (lane, out_cross), (lane, in_cross), (end[0], in_cross)]
    elif route.kind in {"straight", "jog"} and not backward_pair:
        exit_port = axis.port(1.0, 0.5)
        entry_port = axis.port(0.0, 0.5)
        start = (source.flow + axis.flow_extent(s_node), source.cross_mid(axis))
        end = (target.flow, target.cross_mid(axis))
        if route.kind == "jog":
            gap = route.gaps[0]
            lane = lane_flow(gap, route.lanes[gap])
            waypoints_fc = [(lane, start[1]), (lane, end[1])]
    elif route.kind in {"straight", "jog"}:  # adjacent backward
        exit_port = axis.port(0.0, 0.5)
        entry_port = axis.port(1.0, 0.5)
        start = (source.flow, source.cross_mid(axis))
        end = (target.flow + axis.flow_extent(t_node), target.cross_mid(axis))
        if route.kind == "jog":
            gap = route.gaps[0]
            lane = lane_flow(gap, route.lanes[gap])
            waypoints_fc = [(lane, start[1]), (lane, end[1])]
    elif route.kind == "long":
        gap_out, gap_in = source.rank, target.rank - 1
        lane_out = lane_flow(gap_out, route.lanes[gap_out])
        lane_in = lane_flow(gap_in, route.lanes[gap_in])
        lane_cross = lane_base + LANE_STEP * (route.bottom_lane or 0)
        exit_port = axis.port(1.0, 0.5)
        entry_port = axis.port(0.0, 0.5)
        start = (source.flow + axis.flow_extent(s_node), source.cross_mid(axis))
        end = (target.flow, target.cross_mid(axis))
        waypoints_fc = [
            (lane_out, start[1]),
            (lane_out, lane_cross),
            (lane_in, lane_cross),
            (lane_in, end[1]),
        ]
    else:  # backward across more than one column: around the outside
        gap_left = source.rank - 1  # gap left of the source column
        gap_right = target.rank  # gap right of the target column
        lane_left = lane_flow(gap_left, route.lanes[gap_left])
        lane_right = lane_flow(gap_right, route.lanes[gap_right])
        lane_cross = lane_base + LANE_STEP * (route.bottom_lane or 0)
        exit_port = axis.port(0.0, 0.5)
        entry_port = axis.port(1.0, 0.5)
        start = (source.flow, source.cross_mid(axis))
        end = (target.flow + axis.flow_extent(t_node), target.cross_mid(axis))
        waypoints_fc = [
            (lane_left, start[1]),
            (lane_left, lane_cross),
            (lane_right, lane_cross),
            (lane_right, end[1]),
        ]

    points = [axis.point(*start), *[axis.point(*wp) for wp in waypoints_fc], axis.point(*end)]
    edge.metadata = {
        **edge.metadata,
        "exit_port": exit_port,
        "entry_port": entry_port,
        "waypoints": [axis.point(*wp) for wp in waypoints_fc],
        "route": points,
    }

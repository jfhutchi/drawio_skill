import sys
import unittest
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.cli import apply_visual_pattern_to_diagram
from drawio_generator.diagram_model import Boundary, Diagram, Edge, Node
from drawio_generator.layout_engine import (
    AWS_GROUP_ORDER,
    AZURE_GROUP_ORDER,
    DATA_PLATFORM_GROUP_ORDER,
    GRID_SIZE,
    apply_layout,
)


class LayoutEngineTests(unittest.TestCase):
    def test_aws_pattern_places_compute_left_of_data_and_data_left_of_analytics(self):
        diagram = Diagram(
            title="AWS Reference",
            diagram_type="cloud",
            direction="left-to-right",
            nodes=[
                Node(id="users", label="Internet Users", node_type="user"),
                Node(id="cf", label="Amazon CloudFront", node_type="cdn"),
                Node(id="lambda", label="AWS Lambda", node_type="process"),
                Node(id="dynamo", label="Amazon DynamoDB", node_type="database"),
                Node(id="quicksight", label="Amazon QuickSight", node_type="dashboard"),
                Node(id="sns", label="Amazon SNS Notifications", node_type="consumer"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "aws-reference")
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}

        self.assertEqual("aws-reference", diagram.metadata["visual_pattern_id"])
        self.assertEqual("boundary-aws-compute", by_id["lambda"].group)
        self.assertEqual("boundary-aws-data", by_id["dynamo"].group)
        self.assertEqual("boundary-aws-analytics", by_id["quicksight"].group)
        self.assertEqual("boundary-aws-consumers", by_id["sns"].group)
        self.assertLess(by_id["lambda"].x, by_id["dynamo"].x)
        self.assertLess(by_id["dynamo"].x, by_id["quicksight"].x)
        self.assertLess(by_id["quicksight"].x, by_id["sns"].x)

    def test_azure_pattern_separates_primary_and_secondary_regions(self):
        diagram = Diagram(
            title="Azure Reference",
            diagram_type="cloud",
            direction="left-to-right",
            nodes=[
                Node(id="front-door", label="Azure Front Door", node_type="cdn"),
                Node(id="aks-primary", label="AKS Primary Region", node_type="kubernetes"),
                Node(id="aks-secondary", label="AKS Secondary Region", node_type="kubernetes"),
                Node(id="sql", label="Azure SQL", node_type="database"),
                Node(id="vault", label="Azure Key Vault", node_type="secret"),
                Node(id="monitor", label="Azure Monitor", node_type="monitoring"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "azure-reference")
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}

        self.assertEqual("boundary-azure-global", by_id["front-door"].group)
        self.assertEqual("boundary-azure-region-primary", by_id["aks-primary"].group)
        self.assertEqual("boundary-azure-region-secondary", by_id["aks-secondary"].group)
        self.assertEqual("boundary-azure-data", by_id["sql"].group)
        self.assertEqual("boundary-azure-identity", by_id["vault"].group)
        self.assertEqual("boundary-azure-operations", by_id["monitor"].group)
        self.assertLess(by_id["aks-primary"].x, by_id["aks-secondary"].x)

    def test_data_platform_pattern_orders_sources_ingest_process_store_serve(self):
        diagram = Diagram(
            title="Data Platform",
            diagram_type="enterprise",
            direction="left-to-right",
            nodes=[
                Node(id="crm", label="CRM Source", node_type="api"),
                Node(id="eventhub", label="Azure Event Hubs", node_type="queue"),
                Node(id="databricks", label="Databricks Notebook", node_type="process"),
                Node(id="delta", label="Delta Lake (Bronze/Silver/Gold)", node_type="database"),
                Node(id="powerbi", label="Power BI Dashboard", node_type="dashboard"),
                Node(id="purview", label="Purview Data Governance", node_type="security"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "data-platform-pipeline")
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}

        self.assertEqual("boundary-data-sources", by_id["crm"].group)
        self.assertEqual("boundary-data-ingest", by_id["eventhub"].group)
        self.assertEqual("boundary-data-process", by_id["databricks"].group)
        self.assertEqual("boundary-data-store", by_id["delta"].group)
        self.assertEqual("boundary-data-serve", by_id["powerbi"].group)
        self.assertEqual("boundary-data-governance", by_id["purview"].group)
        self.assertLess(by_id["crm"].x, by_id["eventhub"].x)
        self.assertLess(by_id["eventhub"].x, by_id["databricks"].x)
        self.assertLess(by_id["databricks"].x, by_id["delta"].x)
        self.assertLess(by_id["delta"].x, by_id["powerbi"].x)

    def test_enterprise_reference_pattern_leaves_existing_groups_alone(self):
        diagram = Diagram(
            title="Enterprise",
            diagram_type="enterprise",
            direction="left-to-right",
            boundaries=[
                Boundary(id="boundary-source-control", label="Source Control Zone", boundary_type="logical"),
                Boundary(id="boundary-automation-control", label="Automation Control Zone", boundary_type="logical"),
            ],
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository", group="boundary-source-control"),
                Node(id="tower", label="Ansible Tower", node_type="ansible", group="boundary-automation-control"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "enterprise-reference")

        self.assertEqual("enterprise-reference", diagram.metadata["visual_pattern_id"])
        self.assertEqual("boundary-source-control", diagram.nodes[0].group)
        self.assertEqual({"boundary-source-control", "boundary-automation-control"}, {b.id for b in diagram.boundaries})

    def test_pattern_group_orders_cover_documented_columns(self):
        self.assertEqual(AWS_GROUP_ORDER[0], "boundary-aws-external")
        self.assertEqual(AWS_GROUP_ORDER[-1], "boundary-aws-consumers")
        self.assertEqual(AZURE_GROUP_ORDER[0], "boundary-azure-external")
        self.assertEqual(DATA_PLATFORM_GROUP_ORDER[0], "boundary-data-sources")
        self.assertEqual(DATA_PLATFORM_GROUP_ORDER[-1], "boundary-data-governance")


def _fixture_diagram() -> Diagram:
    """Azure-style fixture with same-column chains, long edges, and stacked columns."""

    diagram = Diagram(
        title="Layered Fixture",
        diagram_type="enterprise",
        direction="left-to-right",
        metadata={"visual_pattern_id": "azure-reference"},
        boundaries=[
            Boundary(id="boundary-azure-global", label="Global", boundary_type="cloud"),
            Boundary(id="boundary-azure-region-primary", label="Primary", boundary_type="cloud"),
            Boundary(id="boundary-azure-data", label="Data", boundary_type="logical"),
            Boundary(id="boundary-azure-operations", label="Ops", boundary_type="logical"),
        ],
        nodes=[
            # Deliberately listed so extraction order disagrees with flow order.
            Node(id="waf", label="Application Gateway WAF", group="boundary-azure-global"),
            Node(id="front-door", label="Azure Front Door", group="boundary-azure-global"),
            Node(id="aks", label="AKS", group="boundary-azure-region-primary"),
            Node(id="postgres", label="Azure Database for PostgreSQL", group="boundary-azure-data"),
            Node(id="grafana", label="Grafana", group="boundary-azure-operations"),
            Node(id="prometheus", label="Prometheus", group="boundary-azure-operations"),
            Node(id="log-analytics", label="Log Analytics", group="boundary-azure-operations"),
        ],
        edges=[
            Edge(id="edge-1", source="front-door", target="waf", label="HTTPS ingress", metadata={"sequence": 1}),
            Edge(id="edge-2", source="waf", target="aks", label="WAF-routed HTTPS", metadata={"sequence": 2}),
            Edge(id="edge-3", source="aks", target="postgres", label="SQL over TLS", metadata={"sequence": 3}),
            Edge(id="edge-4", source="aks", target="prometheus", label="metrics scrape", metadata={"sequence": 4}),
            Edge(id="edge-5", source="prometheus", target="grafana", label="dashboard data", metadata={"sequence": 5}),
            Edge(id="edge-6", source="aks", target="log-analytics", label="logs", metadata={"sequence": 6}),
        ],
    )
    return diagram


def _segment_intersects_rect(p1, p2, rect, slack=1.0) -> bool:
    """Axis-aligned segment vs rect interior intersection (routes are orthogonal)."""

    (x1, y1), (x2, y2) = p1, p2
    rx1, ry1, rx2, ry2 = rect
    rx1 += slack
    ry1 += slack
    rx2 -= slack
    ry2 -= slack
    lo_x, hi_x = sorted((x1, x2))
    lo_y, hi_y = sorted((y1, y2))
    return lo_x < rx2 and hi_x > rx1 and lo_y < ry2 and hi_y > ry1


class LayeredLayoutTests(unittest.TestCase):
    def _column_of(self, laid_out, node_id):
        node = next(node for node in laid_out.nodes if node.id == node_id)
        return node.x

    def test_ranks_monotonic_along_every_numbered_edge(self):
        laid_out = apply_layout(_fixture_diagram())
        by_id = {node.id: node for node in laid_out.nodes}
        for edge in laid_out.edges:
            source, target = by_id[edge.source], by_id[edge.target]
            if source.x == target.x:
                # Same column: flow must read downward, never upward.
                self.assertLess(source.y, target.y, f"{edge.id} points upward")
            else:
                self.assertLess(source.x, target.x, f"{edge.id} points backward")

    def test_no_planned_segment_crosses_a_non_endpoint_node(self):
        laid_out = apply_layout(_fixture_diagram())
        rects = {
            node.id: (float(node.x), float(node.y), float(node.x + node.width), float(node.y + node.height))
            for node in laid_out.nodes
        }
        for edge in laid_out.edges:
            route = edge.metadata.get("route")
            self.assertIsInstance(route, list, f"{edge.id} has no planned route")
            for p1, p2 in zip(route, route[1:]):
                for node_id, rect in rects.items():
                    if node_id in {edge.source, edge.target}:
                        continue
                    self.assertFalse(
                        _segment_intersects_rect(p1, p2, rect),
                        f"{edge.id} segment {p1}->{p2} crosses node {node_id}",
                    )

    def test_all_node_and_boundary_coordinates_are_grid_multiples(self):
        laid_out = apply_layout(_fixture_diagram())
        for node in laid_out.nodes:
            for value in (node.x, node.y, node.width, node.height):
                self.assertEqual(0, value % GRID_SIZE, f"{node.id}: {value} off grid")
        for boundary in laid_out.boundaries:
            for value in (boundary.x, boundary.y, boundary.width, boundary.height):
                self.assertEqual(0, value % GRID_SIZE, f"{boundary.id}: {value} off grid")

    def test_boundary_rects_are_pairwise_disjoint(self):
        laid_out = apply_layout(_fixture_diagram())
        rects = [
            (boundary.id, boundary.x, boundary.y, boundary.x + boundary.width, boundary.y + boundary.height)
            for boundary in laid_out.boundaries
        ]
        for index, (id_a, ax1, ay1, ax2, ay2) in enumerate(rects):
            for id_b, bx1, by1, bx2, by2 in rects[index + 1:]:
                overlap_x = min(ax2, bx2) - max(ax1, bx1)
                overlap_y = min(ay2, by2) - max(ay1, by1)
                self.assertFalse(overlap_x > 0 and overlap_y > 0, f"{id_a} overlaps {id_b}")

    def test_layout_is_stable_across_runs(self):
        first = apply_layout(_fixture_diagram())
        second = apply_layout(_fixture_diagram())
        self.assertEqual(asdict(first), asdict(second))

    def test_every_edge_gets_ports_and_route(self):
        laid_out = apply_layout(_fixture_diagram())
        for edge in laid_out.edges:
            self.assertIn("exit_port", edge.metadata, edge.id)
            self.assertIn("entry_port", edge.metadata, edge.id)
            self.assertGreaterEqual(len(edge.metadata["route"]), 2, edge.id)

    def test_parallel_channel_edges_do_not_share_a_lane(self):
        diagram = _fixture_diagram()
        # Both aks->prometheus and aks->log-analytics leave the primary column
        # as long edges; their vertical lanes must not coincide.
        laid_out = apply_layout(diagram)
        lanes = []
        for edge in laid_out.edges:
            waypoints = edge.metadata.get("waypoints") or []
            if len(waypoints) >= 2:
                lanes.append((edge.id, waypoints[0][0]))
        xs = [x for _, x in lanes]
        self.assertEqual(len(xs), len(set(xs)), f"channel lanes collide: {lanes}")

    def test_backward_edge_routes_around_the_outside(self):
        diagram = _fixture_diagram()
        diagram.edges.append(
            Edge(id="edge-back", source="grafana", target="front-door", label="feedback", metadata={"sequence": 7})
        )
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}
        back = next(edge for edge in laid_out.edges if edge.id == "edge-back")
        route = back.metadata["route"]
        content_bottom = max(node.y + node.height for node in laid_out.nodes)
        # The route must dip below all content instead of cutting through columns.
        self.assertTrue(any(point[1] > content_bottom for point in route), route)
        rects = {
            node.id: (float(node.x), float(node.y), float(node.x + node.width), float(node.y + node.height))
            for node in laid_out.nodes
        }
        for p1, p2 in zip(route, route[1:]):
            for node_id, rect in rects.items():
                if node_id in {back.source, back.target}:
                    continue
                self.assertFalse(_segment_intersects_rect(p1, p2, rect), f"backward edge crosses {node_id}")


if __name__ == "__main__":
    unittest.main()

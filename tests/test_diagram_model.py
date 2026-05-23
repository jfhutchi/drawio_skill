import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from drawio_generator.validators import validate_model


class DiagramModelTests(unittest.TestCase):
    def test_valid_model_with_boundaries_legend_and_edges_has_no_errors(self):
        diagram = Diagram(
            title="Azure Web Application",
            diagram_type="enterprise",
            audience="architect",
            boundaries=[
                Boundary(id="boundary-azure", label="Azure Subscription", boundary_type="cloud"),
            ],
            nodes=[
                Node(id="front-door", label="Azure Front Door", node_type="cdn", group="boundary-azure"),
                Node(id="aks", label="AKS Cluster", node_type="kubernetes", group="boundary-azure"),
                Node(id="postgres", label="Azure PostgreSQL", node_type="database", group="boundary-azure"),
            ],
            edges=[
                Edge(id="edge-1", source="front-door", target="aks", label="HTTPS", protocol="HTTPS"),
                Edge(id="edge-2", source="aks", target="postgres", label="SQL", protocol="TLS"),
            ],
            legends=[
                LegendItem(label="Platform/Application", meaning="Blue components are runtime services"),
            ],
        )

        self.assertEqual([], validate_model(diagram))

    def test_model_validation_catches_duplicate_ids_missing_labels_and_bad_edges(self):
        diagram = Diagram(
            title="Broken",
            diagram_type="enterprise",
            nodes=[
                Node(id="api", label="API", node_type="api"),
                Node(id="api", label="", node_type="worker"),
            ],
            edges=[
                Edge(id="edge-1", source="api", target="missing", label="calls"),
            ],
        )

        messages = [issue.message for issue in validate_model(diagram)]

        self.assertTrue(any("Duplicate id" in message for message in messages))
        self.assertTrue(any("empty label" in message for message in messages))
        self.assertTrue(any("missing target" in message for message in messages))


if __name__ == "__main__":
    unittest.main()

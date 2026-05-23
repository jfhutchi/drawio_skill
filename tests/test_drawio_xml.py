import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from drawio_generator.drawio_xml import generate_drawio_xml
from drawio_generator.validators import validate_drawio_xml


class DrawioXmlTests(unittest.TestCase):
    def test_generates_parseable_drawio_xml_with_required_cells(self):
        diagram = Diagram(
            title="CI/CD Flow",
            subtitle="Developer to production deployment",
            diagram_type="cicd",
            audience="sre",
            boundaries=[Boundary(id="boundary-prod", label="Production", boundary_type="environment")],
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository"),
                Node(id="build", label="Build and Test", node_type="process"),
                Node(id="deploy", label="Deploy to Production", node_type="deployment", group="boundary-prod"),
            ],
            edges=[
                Edge(id="edge-repo-build", source="repo", target="build", label="pull request"),
                Edge(id="edge-build-deploy", source="build", target="deploy", label="approved artifact"),
            ],
            legends=[LegendItem(label="Blue", meaning="Build and runtime systems")],
        )

        xml_text = generate_drawio_xml(diagram)
        root = ET.fromstring(xml_text)
        cells = {cell.attrib.get("id"): cell for cell in root.findall(".//mxCell")}
        edges = root.findall(".//mxCell[@edge='1']")

        self.assertEqual("mxfile", root.tag)
        self.assertIn("0", cells)
        self.assertIn("1", cells)
        self.assertEqual("repo", edges[0].attrib["source"])
        self.assertEqual("build", edges[0].attrib["target"])
        self.assertEqual([], validate_drawio_xml(xml_text))

    def test_xml_escapes_labels_and_rejects_missing_edge_references(self):
        diagram = Diagram(
            title="Escaping",
            diagram_type="code",
            nodes=[
                Node(id="handler", label="Handler <API>", node_type="api"),
                Node(id="db", label="Orders & Billing", node_type="database"),
            ],
            edges=[Edge(id="edge-1", source="handler", target="db", label="query <orders> & billing")],
        )

        xml_text = generate_drawio_xml(diagram)
        self.assertIn("&lt;API&gt;", xml_text)
        self.assertIn("Orders &amp; Billing", xml_text)
        self.assertEqual([], validate_drawio_xml(xml_text))


if __name__ == "__main__":
    unittest.main()

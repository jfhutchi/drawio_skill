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

    def test_enterprise_edges_use_numbered_labels_and_semantic_colors(self):
        diagram = Diagram(
            title="Enterprise Review",
            diagram_type="enterprise",
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository"),
                Node(id="tower", label="Ansible Tower / AWX", node_type="ansible"),
                Node(id="targets", label="Customer Targets", node_type="server"),
                Node(id="reports", label="Report Generation", node_type="workbook"),
                Node(id="sfs", label="Optional SFS", node_type="object_storage"),
                Node(id="vault", label="Delinea Secret Server", node_type="secret"),
            ],
            edges=[
                Edge(id="edge-control", source="repo", target="tower", label="Project sync pulls latest SHC repository", metadata={"sequence": 1, "flow_type": "control"}),
                Edge(id="edge-collect", source="tower", target="targets", label="Collect health and security evidence", metadata={"sequence": 2, "flow_type": "target_collection"}),
                Edge(id="edge-report", source="targets", target="reports", label="Stage evidence for Excel workbook generation", metadata={"sequence": 3, "flow_type": "report_evidence"}),
                Edge(id="edge-optional", source="reports", target="sfs", label="Optional secure SFS upload path", metadata={"sequence": 4, "flow_type": "optional_storage"}),
                Edge(id="edge-sensitive", source="tower", target="vault", label="Retrieve runtime secrets", metadata={"sequence": 5, "flow_type": "security_sensitive"}),
            ],
        )

        xml_text = generate_drawio_xml(diagram)
        root = ET.fromstring(xml_text)
        model = root.find(".//mxGraphModel")
        cells = {cell.attrib.get("id"): cell for cell in root.findall(".//mxCell")}

        self.assertGreaterEqual(int(model.attrib["pageWidth"]), 1300)
        self.assertEqual("1", cells["edge-control"].attrib["value"])
        self.assertIn("strokeColor=#4f46e5", cells["edge-control"].attrib["style"])
        self.assertIn("strokeColor=#2f9e44", cells["edge-collect"].attrib["style"])
        self.assertIn("strokeColor=#d97706", cells["edge-report"].attrib["style"])
        self.assertIn("strokeColor=#6c757d", cells["edge-optional"].attrib["style"])
        self.assertIn("dashed=1", cells["edge-optional"].attrib["style"])
        self.assertIn("strokeColor=#dc2626", cells["edge-sensitive"].attrib["style"])
        self.assertIn("dashed=1", cells["edge-sensitive"].attrib["style"])
        self.assertIn("1: Project sync pulls latest SHC repository", cells["__legend"].attrib["value"])

    def test_enterprise_layout_uses_wide_readable_nodes_and_trust_boundaries(self):
        diagram = Diagram(
            title="Page 1 - High-Level Architecture",
            diagram_type="enterprise",
            direction="left-to-right",
            boundaries=[
                Boundary(id="source-zone", label="Source Control Zone", boundary_type="logical"),
                Boundary(id="trust-boundary", label="Customer Trust Boundary", boundary_type="trust"),
            ],
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository", group="source-zone"),
                Node(id="targets", label="Customer Targets", node_type="server", group="trust-boundary"),
            ],
            edges=[Edge(id="edge-repo-targets", source="repo", target="targets", label="controlled automation flow")],
        )

        xml_text = generate_drawio_xml(diagram)
        root = ET.fromstring(xml_text)
        cells = {cell.attrib.get("id"): cell for cell in root.findall(".//mxCell")}
        repo_geometry = cells["repo"].find("mxGeometry")

        self.assertGreaterEqual(int(repo_geometry.attrib["width"]), 190)
        self.assertGreaterEqual(int(repo_geometry.attrib["height"]), 90)
        self.assertIn("fillColor=#f8fbff", cells["source-zone"].attrib["style"])
        self.assertIn("strokeColor=#dc2626", cells["trust-boundary"].attrib["style"])
        self.assertIn("dashed=1", cells["trust-boundary"].attrib["style"])


if __name__ == "__main__":
    unittest.main()

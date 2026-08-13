"""Definition-of-done regression: the shipped example must produce a clean,
review-quality executive page. Runs the full baseline command against
examples/azure-notes.md into a temp dir and asserts on the generated XML,
the QA verdict, and the preview."""

import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.cli import _azure_group_for_node, _park_disconnected_nodes, main
from drawio_generator.diagram_model import Boundary, Diagram, Edge, Node
from drawio_generator.icon_registry import canonical_component_key
from drawio_generator.visual_qa import _absolute_boxes, _box_kind, analyze_drawio_xml

REPO_ROOT = Path(__file__).resolve().parents[1]
GRID = 10

EXAMPLE_REQUEST = (
    "Create an Azure enterprise architecture diagram using AKS, Key Vault, "
    "PostgreSQL, GitHub Actions, Terraform, Prometheus, Grafana, and Log Analytics."
)


class VisualRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp_dir.name)
        cls.exit_code = main(
            [
                "--request",
                EXAMPLE_REQUEST,
                "--input",
                str(REPO_ROOT / "examples" / "azure-notes.md"),
                "--output",
                str(cls.output),
                "--validate",
            ]
        )
        cls.xml_text = (cls.output / "diagram.drawio").read_text(encoding="utf-8")
        cls.root = ET.fromstring(cls.xml_text)
        cls.page1 = cls.root.findall("diagram")[0].find("mxGraphModel")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_1_result_pass_and_exit_code_zero(self):
        self.assertEqual(0, self.exit_code)
        render_qa = (self.output / "render-qa.md").read_text(encoding="utf-8")
        self.assertTrue(render_qa.startswith("RESULT: PASS"), render_qa.splitlines()[0])

    def test_2_zero_overlaps_of_any_kind_furniture_included(self):
        issues = analyze_drawio_xml(self.xml_text)
        overlaps = [issue for issue in issues if "overlap" in issue.message.lower()]
        self.assertEqual([], overlaps)
        # Belt and braces: direct geometry check on page 1.
        boxes = [box for box in _absolute_boxes(self.page1) if _box_kind(box) in {"content", "furniture"}]
        for index, first in enumerate(boxes):
            for second in boxes[index + 1:]:
                x_overlap = min(first.right, second.right) - max(first.x, second.x)
                y_overlap = min(first.bottom, second.bottom) - max(first.y, second.y)
                self.assertFalse(
                    x_overlap > 0 and y_overlap > 0,
                    f"{first.item_id} overlaps {second.item_id}",
                )

    def test_3_boundaries_disjoint_and_members_parented_relative(self):
        boundaries = [box for box in _absolute_boxes(self.page1) if _box_kind(box) == "boundary"]
        self.assertGreater(len(boundaries), 1)
        for index, first in enumerate(boundaries):
            for second in boundaries[index + 1:]:
                x_overlap = min(first.right, second.right) - max(first.x, second.x)
                y_overlap = min(first.bottom, second.bottom) - max(first.y, second.y)
                self.assertFalse(x_overlap > 0 and y_overlap > 0, f"{first.item_id} overlaps {second.item_id}")

        cells = {cell.attrib["id"]: cell for cell in self.page1.findall(".//mxCell")}
        boundary_ids = {box.item_id for box in boundaries}
        members = 0
        for cell_id, cell in cells.items():
            if cell.attrib.get("vertex") != "1" or cell_id.endswith("__icon"):
                continue
            style = cell.attrib.get("style", "")
            if "swimlane" in style or "edgeLabel" in style:
                continue
            if cell_id.endswith(("__title", "__legend", "__page_notes")):
                continue
            # Every content node must live inside its boundary container.
            self.assertIn(cell.attrib.get("parent"), boundary_ids, cell_id)
            geometry = cell.find("mxGeometry")
            self.assertGreaterEqual(float(geometry.attrib["x"]), 0, cell_id)
            self.assertGreaterEqual(float(geometry.attrib["y"]), 32, cell_id)
            members += 1
        self.assertGreater(members, 5)

    def test_4_every_page1_node_has_degree_at_least_one(self):
        content_ids = {box.item_id for box in _absolute_boxes(self.page1) if _box_kind(box) == "content"}
        connected: set[str] = set()
        for edge in self.page1.findall(".//mxCell[@edge='1']"):
            connected.add(edge.attrib.get("source", ""))
            connected.add(edge.attrib.get("target", ""))
        for node_id in content_ids:
            self.assertIn(node_id, connected, f"degree-0 node on page 1: {node_id}")

    def test_5_numbered_flows_are_rank_monotonic(self):
        boxes = {box.item_id: box for box in _absolute_boxes(self.page1)}
        numbered_edges = set()
        for cell in self.page1.findall(".//mxCell[@vertex='1']"):
            if "edgeLabel" in cell.attrib.get("style", "") and cell.attrib.get("value", "").isdigit():
                numbered_edges.add(cell.attrib.get("parent"))
        self.assertGreater(len(numbered_edges), 3)
        for edge in self.page1.findall(".//mxCell[@edge='1']"):
            if edge.attrib.get("id") not in numbered_edges:
                continue
            source = boxes[edge.attrib["source"]]
            target = boxes[edge.attrib["target"]]
            if source.x == target.x:
                self.assertLess(source.y, target.y, f"{edge.attrib['id']} points upward")
            else:
                self.assertLess(source.x, target.x, f"{edge.attrib['id']} points backward")

    def test_6_every_absolute_coordinate_is_a_grid_multiple(self):
        for page in self.root.findall("diagram"):
            model = page.find("mxGraphModel")
            self.assertEqual("10", model.attrib.get("gridSize"))
            for cell in model.findall(".//mxCell[@vertex='1']"):
                geometry = cell.find("mxGeometry")
                if geometry is None or geometry.attrib.get("relative") == "1":
                    continue  # edge labels / glyph children ride their parents
                for name in ("x", "y", "width", "height"):
                    value = float(geometry.attrib.get(name, 0))
                    self.assertEqual(0, value % GRID, f"{cell.attrib.get('id')}.{name}={value}")

    def test_7_exactly_one_numbering_mechanism_no_orphan_badges(self):
        self.assertNotIn("__badge_", self.xml_text)
        for page in self.root.findall("diagram"):
            model = page.find("mxGraphModel")
            edge_ids = {cell.attrib.get("id") for cell in model.findall(".//mxCell[@edge='1']")}
            for edge in model.findall(".//mxCell[@edge='1']"):
                self.assertFalse(
                    edge.attrib.get("value", "").isdigit(),
                    f"digit value on edge {edge.attrib.get('id')} (old numbering mechanism)",
                )
            for cell in model.findall(".//mxCell[@vertex='1']"):
                style = cell.attrib.get("style", "")
                value = cell.attrib.get("value", "")
                if value.isdigit():
                    self.assertIn("edgeLabel", style, cell.attrib.get("id"))
                    self.assertIn(cell.attrib.get("parent"), edge_ids, cell.attrib.get("id"))
                self.assertFalse(
                    "ellipse" in style and value.isdigit(),
                    f"orphan ellipse badge {cell.attrib.get('id')}",
                )

    def test_8_preview_page_1_exists_and_node_count_matches(self):
        preview_path = self.output / "preview-page-1.svg"
        self.assertTrue(preview_path.exists())
        svg = ET.fromstring(preview_path.read_text(encoding="utf-8"))
        svg_nodes = [el for el in svg.iter() if el.attrib.get("class") == "node"]
        content_count = len([box for box in _absolute_boxes(self.page1) if _box_kind(box) == "content"])
        self.assertEqual(content_count, len(svg_nodes))


class CanonicalDedupeTests(unittest.TestCase):
    def test_gateway_synonyms_share_a_canonical_key(self):
        self.assertEqual(
            canonical_component_key("Application Gateway WAF"),
            canonical_component_key("Azure Application Gateway"),
        )

    def test_distinct_services_keep_distinct_keys(self):
        self.assertNotEqual(
            canonical_component_key("Azure Front Door"),
            canonical_component_key("Azure Application Gateway"),
        )
        self.assertNotEqual(
            canonical_component_key("Prometheus"),
            canonical_component_key("Grafana"),
        )

    def test_vendor_prefix_stripping_merges_unknown_labels(self):
        self.assertEqual(
            canonical_component_key("Azure Imaginary Widget"),
            canonical_component_key("Imaginary Widget"),
        )

    def test_aliases_source_has_no_duplicate_keys(self):
        source = (REPO_ROOT / "src" / "drawio_generator" / "icon_registry.py").read_text(encoding="utf-8")
        aliases_block = source.split("ALIASES: dict[str, str] = {", 1)[1].split("}", 1)[0]
        keys = re.findall(r'^\s*"([^"]+)":', aliases_block, flags=re.MULTILINE)
        duplicates = {key for key in keys if keys.count(key) > 1}
        self.assertEqual(set(), duplicates)


class DevopsBucketTests(unittest.TestCase):
    def test_cicd_tools_never_land_inside_a_region(self):
        self.assertEqual("boundary-azure-devops", _azure_group_for_node(Node(id="gh", label="GitHub Actions", node_type="process")))
        self.assertEqual("boundary-azure-devops", _azure_group_for_node(Node(id="tf", label="Terraform", node_type="terraform")))
        self.assertEqual("boundary-azure-region-primary", _azure_group_for_node(Node(id="aks", label="AKS", node_type="kubernetes")))


class ParkingTests(unittest.TestCase):
    def test_degree_zero_node_is_parked_and_recorded(self):
        diagram = Diagram(
            title="Park",
            diagram_type="enterprise",
            boundaries=[Boundary(id="boundary-a", label="A")],
            nodes=[
                Node(id="one", label="One", group="boundary-a"),
                Node(id="two", label="Two", group="boundary-a"),
                Node(id="floating", label="Floating Component", group="boundary-a"),
            ],
            edges=[Edge(id="e", source="one", target="two", label="link")],
        )
        _park_disconnected_nodes(diagram)
        floating = next(node for node in diagram.nodes if node.id == "floating")
        self.assertEqual("boundary-unconfirmed", floating.group)
        self.assertEqual("detail", floating.metadata.get("detail_level"))
        self.assertTrue(any("Floating Component" in item for item in diagram.assumptions))
        self.assertTrue(any(boundary.id == "boundary-unconfirmed" for boundary in diagram.boundaries))

    def test_edgeless_diagram_is_left_alone(self):
        diagram = Diagram(
            title="NoEdges",
            diagram_type="enterprise",
            nodes=[Node(id="one", label="One"), Node(id="two", label="Two")],
        )
        _park_disconnected_nodes(diagram)
        self.assertEqual([], diagram.boundaries)
        self.assertEqual([], diagram.assumptions)


if __name__ == "__main__":
    unittest.main()

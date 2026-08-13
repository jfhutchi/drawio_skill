import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.cli import main
from drawio_generator.visual_qa import analyze_drawio_xml

REPO_ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_REQUEST = (
    "Create an Azure enterprise architecture diagram using AKS, Key Vault, "
    "PostgreSQL, GitHub Actions, Terraform, Prometheus, Grafana, and Log Analytics."
)


def _generate_example(output: Path) -> str:
    exit_code = main(
        [
            "--request",
            EXAMPLE_REQUEST,
            "--input",
            str(REPO_ROOT / "examples" / "azure-notes.md"),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0, exit_code
    return (output / "diagram.drawio").read_text(encoding="utf-8")


class ContainerAndFurnitureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.xml_text = _generate_example(Path(cls.temp_dir.name))
        cls.root = ET.fromstring(cls.xml_text)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_shipped_example_has_zero_overlap_issues_furniture_included(self):
        issues = analyze_drawio_xml(self.xml_text)
        overlap_issues = [issue for issue in issues if "overlap" in issue.message.lower()]
        self.assertEqual([], overlap_issues)

    def test_member_nodes_are_parented_to_their_boundary_with_relative_geometry(self):
        page = self.root.findall("diagram")[0]
        model = page.find("mxGraphModel")
        cells = {cell.attrib["id"]: cell for cell in model.findall(".//mxCell")}

        boundary_cells = {
            cell_id: cell
            for cell_id, cell in cells.items()
            if "swimlane" in cell.attrib.get("style", "")
        }
        self.assertGreater(len(boundary_cells), 1)

        member_count = 0
        for cell_id, cell in cells.items():
            parent = cell.attrib.get("parent", "")
            if parent in boundary_cells and cell.attrib.get("vertex") == "1":
                member_count += 1
                geometry = cell.find("mxGeometry")
                boundary_geometry = boundary_cells[parent].find("mxGeometry")
                x = float(geometry.attrib["x"])
                y = float(geometry.attrib["y"])
                width = float(geometry.attrib["width"])
                height = float(geometry.attrib["height"])
                bw = float(boundary_geometry.attrib["width"])
                bh = float(boundary_geometry.attrib["height"])
                self.assertGreaterEqual(x, 0, cell_id)
                self.assertGreaterEqual(y, 32, f"{cell_id} sits under the title strip")
                self.assertLessEqual(x + width, bw, f"{cell_id} sticks out of {parent}")
                self.assertLessEqual(y + height, bh, f"{cell_id} sticks out of {parent}")
        self.assertGreater(member_count, 5)

    def test_boundaries_are_real_containers(self):
        page = self.root.findall("diagram")[0]
        model = page.find("mxGraphModel")
        for cell in model.findall(".//mxCell"):
            style = cell.attrib.get("style", "")
            if "swimlane" in style:
                self.assertIn("container=1", style)
                self.assertIn("collapsible=0", style)
                self.assertIn("startSize=32", style)

    def test_furniture_is_placed_after_content_not_at_fixed_coordinates(self):
        # The legend must sit right of the content extents or in the bottom
        # band below them - never at the old hardcoded (900, 30) on top of
        # content.
        page = self.root.findall("diagram")[0]
        model = page.find("mxGraphModel")
        legend = next(
            cell for cell in model.findall(".//mxCell") if cell.attrib.get("id", "").endswith("__legend")
        )
        legend_geometry = legend.find("mxGeometry")
        legend_x = float(legend_geometry.attrib["x"])
        legend_y = float(legend_geometry.attrib["y"])
        content_right = 0.0
        content_bottom = 0.0
        for cell in model.findall(".//mxCell"):
            if "swimlane" not in cell.attrib.get("style", ""):
                continue
            geometry = cell.find("mxGeometry")
            content_right = max(content_right, float(geometry.attrib["x"]) + float(geometry.attrib["width"]))
            content_bottom = max(content_bottom, float(geometry.attrib["y"]) + float(geometry.attrib["height"]))
        self.assertTrue(
            legend_x >= content_right or legend_y >= content_bottom,
            f"legend at ({legend_x}, {legend_y}) sits on content ({content_right}, {content_bottom})",
        )


if __name__ == "__main__":
    unittest.main()

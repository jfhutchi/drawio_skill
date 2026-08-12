import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator import preview
from drawio_generator.cli import main
from drawio_generator.diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from drawio_generator.layout_engine import apply_layout

SVG_NS = "{http://www.w3.org/2000/svg}"


def _sample_diagram() -> Diagram:
    return Diagram(
        title="Preview Sample",
        subtitle="test page",
        diagram_type="enterprise",
        boundaries=[Boundary(id="boundary-a", label="Zone A", boundary_type="trust")],
        nodes=[
            Node(id="alpha", label="Alpha Service", group="boundary-a"),
            Node(id="beta", label="Beta Data Store With A Long Label", group="boundary-a"),
        ],
        edges=[Edge(id="edge-1", source="alpha", target="beta", label="writes", metadata={"sequence": 1})],
        legends=[LegendItem("Blue", "Control flow")],
    )


class PreviewSceneTests(unittest.TestCase):
    def test_svg_is_well_formed_and_counts_match_model(self):
        diagram = apply_layout(_sample_diagram())
        scene = preview.build_scene("Page 1", diagram)
        svg_text = preview.render_page_svg(scene)

        root = ET.fromstring(svg_text)
        node_rects = [el for el in root.iter(f"{SVG_NS}rect") if el.attrib.get("class") == "node"]
        boundary_rects = [el for el in root.iter(f"{SVG_NS}rect") if el.attrib.get("class") == "boundary"]
        edge_lines = [el for el in root.iter(f"{SVG_NS}polyline") if el.attrib.get("class") == "edge"]

        self.assertEqual(len(diagram.nodes), len(node_rects))
        self.assertEqual(len(diagram.boundaries), len(boundary_rects))
        self.assertEqual(len(diagram.edges), len(edge_lines))
        self.assertEqual(len(diagram.nodes), scene.node_count)
        self.assertEqual(len(diagram.boundaries), scene.boundary_count)
        self.assertEqual(len(diagram.edges), scene.edge_count)

    def test_wrap_label_respects_estimated_width(self):
        lines = preview.wrap_label("Azure Database for PostgreSQL Flexible Server", 150, 13)
        self.assertGreater(len(lines), 1)
        max_chars = int(150 / (preview.CHAR_WIDTH_FACTOR * 13))
        self.assertTrue(all(len(line) <= max_chars for line in lines))

    def test_edge_label_and_legend_present(self):
        diagram = apply_layout(_sample_diagram())
        svg_text = preview.render_page_svg(preview.build_scene("Page 1", diagram))
        self.assertIn(">1</text>", svg_text)
        self.assertIn("furniture-legend", svg_text)


class PreviewWriteTests(unittest.TestCase):
    def test_write_previews_creates_svg_per_page(self):
        diagram = apply_layout(_sample_diagram())
        with tempfile.TemporaryDirectory() as temp_dir:
            written = preview.write_previews([("Page 1", diagram), ("Page 2", diagram)], Path(temp_dir))
            svgs = [path for path in written if path.suffix == ".svg"]
            self.assertEqual(2, len(svgs))
            self.assertTrue((Path(temp_dir) / "preview-page-1.svg").exists())
            self.assertTrue((Path(temp_dir) / "preview-page-2.svg").exists())
            for path in svgs:
                ET.fromstring(path.read_text(encoding="utf-8"))

    def test_png_skipped_cleanly_without_backend(self):
        diagram = apply_layout(_sample_diagram())
        original = preview._png_backend
        preview._png_backend = lambda: None
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                written = preview.write_previews([("Page 1", diagram)], Path(temp_dir))
                self.assertEqual([".svg"], [path.suffix for path in written])
                self.assertFalse((Path(temp_dir) / "preview-page-1.png").exists())
        finally:
            preview._png_backend = original


class FailClosedCliTests(unittest.TestCase):
    def test_validate_fails_with_exit_1_on_error_severity_visual_qa(self):
        from unittest import mock

        from drawio_generator.visual_qa import VisualQaIssue

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            forced = [VisualQaIssue("error", "Forced error for fail-closed test", "Executive Overview")]
            with mock.patch("drawio_generator.cli.analyze_drawio_xml", return_value=forced):
                exit_code = main(
                    [
                        "--request",
                        "Create an Azure enterprise architecture diagram with AKS and Key Vault.",
                        "--output",
                        str(output),
                        "--validate",
                    ]
                )
            self.assertEqual(1, exit_code)
            render_qa = (output / "render-qa.md").read_text(encoding="utf-8")
            self.assertTrue(render_qa.startswith("RESULT: FAIL (1 errors)"), render_qa.splitlines()[0])
            # Artifacts must be written even on failure.
            self.assertTrue((output / "diagram.drawio").exists())
            self.assertTrue((output / "preview-page-1.svg").exists())

    def test_without_validate_flag_errors_do_not_change_exit_code(self):
        from unittest import mock

        from drawio_generator.visual_qa import VisualQaIssue

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            forced = [VisualQaIssue("error", "Forced error for fail-closed test", "Executive Overview")]
            with mock.patch("drawio_generator.cli.analyze_drawio_xml", return_value=forced):
                exit_code = main(
                    [
                        "--request",
                        "Create an Azure enterprise architecture diagram with AKS and Key Vault.",
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(0, exit_code)
            render_qa = (output / "render-qa.md").read_text(encoding="utf-8")
            self.assertTrue(render_qa.startswith("RESULT: FAIL (1 errors)"), render_qa.splitlines()[0])

    def test_validate_passes_with_exit_0_on_clean_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            notes = Path(temp_dir) / "notes.md"
            notes.write_text(
                "Azure Front Door sends HTTPS traffic to AKS. AKS reads secrets "
                "from Key Vault and stores data in Azure Database for PostgreSQL. "
                "GitHub Actions runs Terraform. Prometheus and Grafana monitor it.",
                encoding="utf-8",
            )
            output = Path(temp_dir) / "out"
            exit_code = main(
                [
                    "--request",
                    "Create an enterprise architecture diagram for an Azure AKS application.",
                    "--input",
                    str(notes),
                    "--output",
                    str(output),
                    "--validate",
                ]
            )
            self.assertEqual(0, exit_code)
            render_qa = (output / "render-qa.md").read_text(encoding="utf-8")
            self.assertTrue(render_qa.startswith("RESULT: PASS"), render_qa.splitlines()[0])
            self.assertTrue((output / "preview-page-1.svg").exists())

if __name__ == "__main__":
    unittest.main()

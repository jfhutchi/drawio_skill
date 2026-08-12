import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.cli import main
from drawio_generator.icon_registry import CATEGORY_STROKES, get_node_visual

REPO_ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_REQUEST = (
    "Create an Azure enterprise architecture diagram using AKS, Key Vault, "
    "PostgreSQL, GitHub Actions, Terraform, Prometheus, Grafana, and Log Analytics."
)


class VisualGrammarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        exit_code = main(
            [
                "--request",
                EXAMPLE_REQUEST,
                "--input",
                str(REPO_ROOT / "examples" / "azure-notes.md"),
                "--output",
                cls.temp_dir.name,
            ]
        )
        assert exit_code == 0
        cls.xml_text = (Path(cls.temp_dir.name) / "diagram.drawio").read_text(encoding="utf-8")
        cls.root = ET.fromstring(cls.xml_text)
        cls.vertices = [cell for cell in cls.root.findall(".//mxCell") if cell.attrib.get("vertex") == "1"]

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_no_emitted_style_uses_vertical_label_position_bottom(self):
        for cell in self.vertices:
            self.assertNotIn(
                "verticalLabelPosition=bottom",
                cell.attrib.get("style", ""),
                cell.attrib.get("id"),
            )

    def test_every_glyph_child_is_fixed_aspect_forty_px(self):
        glyphs = [cell for cell in self.vertices if cell.attrib.get("id", "").endswith("__icon")]
        self.assertGreater(len(glyphs), 0, "example should produce vendor glyphs")
        for glyph in glyphs:
            style = glyph.attrib.get("style", "")
            self.assertIn("aspect=fixed", style, glyph.attrib.get("id"))
            self.assertTrue("shape=" in style or "image=" in style, glyph.attrib.get("id"))
            geometry = glyph.find("mxGeometry")
            self.assertEqual("40", geometry.attrib.get("width"), glyph.attrib.get("id"))
            self.assertEqual("40", geometry.attrib.get("height"), glyph.attrib.get("id"))
            self.assertEqual("1", geometry.attrib.get("relative"), glyph.attrib.get("id"))
            # Glyphs are decoration children of their card, never standalone.
            self.assertNotIn(glyph.attrib.get("parent"), {"0", "1"})

    def test_surface_fills_are_a_subset_of_the_theme(self):
        theme = json.loads(
            (REPO_ROOT / "templates" / "default-enterprise-theme.json").read_text(encoding="utf-8")
        )
        allowed = {value.lower() for value in theme["colors"].values()}
        for cell in self.vertices:
            cell_id = cell.attrib.get("id", "")
            if cell_id.endswith("__icon"):
                continue  # vendor glyph internals carry vendor-fixed colors
            style = cell.attrib.get("style", "")
            match = re.search(r"fillColor=(#[0-9a-fA-F]{6})", style)
            if match is None:
                continue
            self.assertIn(match.group(1).lower(), allowed, f"{cell_id}: {match.group(1)}")

    def test_edges_are_uniform_rounded_one_point_five(self):
        edges = [cell for cell in self.root.findall(".//mxCell") if cell.attrib.get("edge") == "1"]
        self.assertGreater(len(edges), 0)
        for edge in edges:
            style = edge.attrib.get("style", "")
            self.assertIn("rounded=1", style, edge.attrib.get("id"))
            self.assertIn("strokeWidth=1.5", style, edge.attrib.get("id"))
            self.assertIn("fontFamily=Helvetica", style, edge.attrib.get("id"))

    def test_cards_set_helvetica_and_dark_text_explicitly(self):
        cards = [
            cell
            for cell in self.vertices
            if not cell.attrib.get("id", "").endswith("__icon")
            and "swimlane" not in cell.attrib.get("style", "")
            and "edgeLabel" not in cell.attrib.get("style", "")
            and cell.attrib.get("id", "") not in {"0", "1"}
            and not cell.attrib.get("id", "").endswith(("__title", "__legend", "__page_notes"))
        ]
        self.assertGreater(len(cards), 0)
        for card in cards:
            style = card.attrib.get("style", "")
            self.assertIn("fontFamily=Helvetica", style, card.attrib.get("id"))
            self.assertNotIn("fontColor=#23A2D9", style, card.attrib.get("id"))

    def test_card_visual_resolution(self):
        visual = get_node_visual("kubernetes", None, "AKS")
        self.assertIn("fillColor=#ffffff", visual.card_style)
        self.assertIn("spacingLeft=12", visual.card_style)
        self.assertIn("align=left", visual.card_style)
        self.assertIsNotNone(visual.glyph_style)
        self.assertIn("aspect=fixed", visual.glyph_style)
        self.assertNotIn("verticalLabelPosition=bottom", visual.glyph_style)

        plain = get_node_visual("backend", None, "Custom Billing Service")
        self.assertIsNone(plain.glyph_style)
        self.assertNotIn("spacingRight", plain.card_style)

    def test_category_strokes_match_theme_strokes(self):
        theme = json.loads(
            (REPO_ROOT / "templates" / "default-enterprise-theme.json").read_text(encoding="utf-8")
        )
        theme_strokes = {value.lower() for value in theme["strokes"].values()}
        for category, stroke in CATEGORY_STROKES.items():
            self.assertIn(stroke.lower(), theme_strokes, category)


if __name__ == "__main__":
    unittest.main()

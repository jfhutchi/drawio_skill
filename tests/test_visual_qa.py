import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.visual_qa import analyze_drawio_xml, detect_renderer, render_visual_qa


class VisualQaTests(unittest.TestCase):
    def test_static_visual_qa_flags_overlapping_nodes_and_long_edge_labels(self):
        xml_text = """<mxfile host="app.diagrams.net">
  <diagram name="QA">
    <mxGraphModel pageWidth="500" pageHeight="300">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="a" value="Application A" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="100" y="100" width="220" height="100" as="geometry" /></mxCell>
        <mxCell id="b" value="Application B" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="140" y="120" width="220" height="100" as="geometry" /></mxCell>
        <mxCell id="edge-a-b" value="This is too much edge text for a review-quality arrow label" style="edgeStyle=orthogonalEdgeStyle;html=1;" edge="1" parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry" /></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

        issues = analyze_drawio_xml(xml_text)
        messages = "\n".join(issue.message for issue in issues)

        self.assertIn("overlap", messages.lower())
        self.assertIn("long edge label", messages.lower())

    def test_disconnected_node_on_executive_page_is_an_error(self):
        xml_text = """<mxfile host="app.diagrams.net">
  <diagram name="Executive Overview">
    <mxGraphModel pageWidth="1200" pageHeight="800">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="a" value="Service A" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="100" y="100" width="180" height="80" as="geometry" /></mxCell>
        <mxCell id="lonely" value="Floating Node" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="400" y="100" width="180" height="80" as="geometry" /></mxCell>
        <mxCell id="c" value="Service C" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="700" y="100" width="180" height="80" as="geometry" /></mxCell>
        <mxCell id="e" value="1" style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="a" target="c"><mxGeometry relative="1" as="geometry" /></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

        issues = analyze_drawio_xml(xml_text)
        disconnected = [issue for issue in issues if "Disconnected" in issue.message]

        self.assertEqual(1, len(disconnected))
        self.assertEqual("error", disconnected[0].severity)
        self.assertIn("Floating Node", disconnected[0].message)

    def test_disconnected_node_on_detail_page_is_a_warning(self):
        xml_text = """<mxfile host="app.diagrams.net">
  <diagram name="Implementation Detail">
    <mxGraphModel pageWidth="1200" pageHeight="800">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="alone" value="Detail Note" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="100" y="100" width="180" height="80" as="geometry" /></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

        issues = analyze_drawio_xml(xml_text)
        disconnected = [issue for issue in issues if "Disconnected" in issue.message]

        self.assertEqual(1, len(disconnected))
        self.assertEqual("warning", disconnected[0].severity)

    def test_visual_qa_markdown_reports_renderer_availability_without_claiming_render(self):
        renderer = detect_renderer()
        markdown = render_visual_qa([], renderer)

        self.assertIn("# Render and Visual QA", markdown)
        if renderer.available:
            self.assertIn("Renderer available", markdown)
        else:
            self.assertIn("Renderer unavailable", markdown)
        self.assertNotIn("screenshot captured", markdown.lower())


if __name__ == "__main__":
    unittest.main()

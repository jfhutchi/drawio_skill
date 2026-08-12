import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.diagram_model import Boundary, Diagram, Edge, Node
from drawio_generator.layout_engine import apply_layout
from drawio_generator.visual_qa import analyze_drawio_xml, analyze_page_models


def _laid_out_fixture() -> Diagram:
    diagram = Diagram(
        title="QA Depth",
        diagram_type="enterprise",
        direction="left-to-right",
        boundaries=[
            Boundary(id="boundary-source-control", label="Source", boundary_type="logical"),
            Boundary(id="boundary-automation-control", label="Automation", boundary_type="logical"),
        ],
        nodes=[
            Node(id="repo", label="GitHub Repository", group="boundary-source-control"),
            Node(id="tower", label="Ansible Tower", group="boundary-automation-control"),
            Node(id="vault", label="Delinea Secret Server", group="boundary-automation-control"),
        ],
        edges=[
            Edge(id="edge-1", source="repo", target="tower", label="sync", metadata={"sequence": 1}),
            Edge(id="edge-2", source="tower", target="vault", label="secrets", metadata={"sequence": 2}),
        ],
    )
    return apply_layout(diagram)


class RouteCollisionTests(unittest.TestCase):
    def test_clean_layout_has_no_route_collisions(self):
        laid_out = _laid_out_fixture()
        issues = analyze_page_models([("Executive Overview", laid_out)])
        collisions = [issue for issue in issues if "crosses" in issue.message]
        self.assertEqual([], collisions)

    def test_tampered_route_through_node_is_error_on_page_1_warning_later(self):
        laid_out = _laid_out_fixture()
        victim = next(node for node in laid_out.nodes if node.id == "vault")
        edge = laid_out.edges[0]
        # Force the planned route straight through the vault node's center.
        center = (victim.x + victim.width / 2, victim.y + victim.height / 2)
        edge.metadata["route"] = [(0.0, center[1]), (center[0], center[1]), (center[0] + 500, center[1])]

        page1 = analyze_page_models([("Executive Overview", laid_out)])
        collisions = [issue for issue in page1 if "crosses node vault" in issue.message]
        self.assertTrue(collisions)
        self.assertEqual("error", collisions[0].severity)

        page2 = analyze_page_models([("Executive Overview", _laid_out_fixture()), ("Detail", laid_out)])
        later = [issue for issue in page2 if "crosses node vault" in issue.message]
        self.assertTrue(later)
        self.assertEqual("warning", later[0].severity)


class MonotonicFlowTests(unittest.TestCase):
    def test_backward_numbered_flow_is_an_error(self):
        laid_out = _laid_out_fixture()
        laid_out.edges.append(
            Edge(id="edge-back", source="vault", target="repo", label="loop", metadata={"sequence": 3})
        )
        issues = analyze_page_models([("Executive Overview", laid_out)])
        backward = [issue for issue in issues if "points backward" in issue.message]
        self.assertEqual(1, len(backward))
        self.assertEqual("error", backward[0].severity)

    def test_explicitly_declared_backward_flow_is_allowed(self):
        laid_out = _laid_out_fixture()
        laid_out.edges.append(
            Edge(
                id="edge-back",
                source="vault",
                target="repo",
                label="loop",
                direction="backward",
                metadata={"sequence": 3},
            )
        )
        issues = analyze_page_models([("Executive Overview", laid_out)])
        backward = [issue for issue in issues if "points backward" in issue.message]
        self.assertEqual([], backward)


class TextOverflowTests(unittest.TestCase):
    def test_unbreakable_wide_label_warns(self):
        diagram = Diagram(
            title="Overflow",
            diagram_type="enterprise",
            nodes=[
                Node(id="a", label="Supercalifragilisticexpialidocious-Hyperconverged-Aggregator", width=190, height=90),
                Node(id="b", label="Peer", width=190, height=90),
            ],
            edges=[Edge(id="e", source="a", target="b", label="x", metadata={"sequence": 1})],
        )
        laid_out = apply_layout(diagram)
        issues = analyze_page_models([("Executive Overview", laid_out)])
        overflow = [issue for issue in issues if "wider than card" in issue.message]
        self.assertEqual(1, len(overflow))
        self.assertEqual("warning", overflow[0].severity)

    def test_too_many_lines_warns(self):
        diagram = Diagram(
            title="Overflow",
            diagram_type="code",
            nodes=[
                Node(
                    id="a",
                    label="one two three four five six seven eight nine ten eleven twelve thirteen fourteen",
                    width=150,
                    height=40,
                ),
                Node(id="b", label="Peer", width=150, height=40),
            ],
            edges=[Edge(id="e", source="a", target="b", label="x", metadata={"sequence": 1})],
        )
        laid_out = apply_layout(diagram)
        issues = analyze_page_models([("Executive Overview", laid_out)])
        overflow = [issue for issue in issues if "taller than card" in issue.message]
        self.assertEqual(1, len(overflow))


class ContrastAndAspectTests(unittest.TestCase):
    def _xml(self, cell: str) -> str:
        return f"""<mxfile host="app.diagrams.net">
  <diagram name="QA">
    <mxGraphModel pageWidth="800" pageHeight="600">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {cell}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

    def test_low_contrast_font_on_fill_warns(self):
        xml_text = self._xml(
            '<mxCell id="pale" value="Faint Label" style="rounded=1;fillColor=#0072C6;fontColor=#23A2D9;" '
            'vertex="1" parent="1"><mxGeometry x="20" y="20" width="180" height="80" as="geometry" /></mxCell>'
        )
        issues = analyze_drawio_xml(xml_text)
        contrast = [issue for issue in issues if "Low text contrast" in issue.message]
        self.assertEqual(1, len(contrast))
        self.assertEqual("warning", contrast[0].severity)

    def test_dark_text_on_white_card_passes(self):
        xml_text = self._xml(
            '<mxCell id="card" value="Readable Label" style="rounded=1;fillColor=#ffffff;fontColor=#212529;" '
            'vertex="1" parent="1"><mxGeometry x="20" y="20" width="180" height="80" as="geometry" /></mxCell>'
        )
        issues = analyze_drawio_xml(xml_text)
        self.assertEqual([], [issue for issue in issues if "contrast" in issue.message.lower()])

    def test_stretched_stencil_without_fixed_aspect_warns(self):
        xml_text = self._xml(
            '<mxCell id="stretch" value="AKS" style="shape=mxgraph.azure.kubernetes_services;fillColor=#0072C6;" '
            'vertex="1" parent="1"><mxGeometry x="20" y="20" width="190" height="90" as="geometry" /></mxCell>'
        )
        issues = analyze_drawio_xml(xml_text)
        stretched = [issue for issue in issues if "without aspect=fixed" in issue.message]
        self.assertEqual(1, len(stretched))

    def test_fixed_aspect_off_square_warns(self):
        xml_text = self._xml(
            '<mxCell id="warped" value="" style="shape=mxgraph.azure.key_vaults;aspect=fixed;" '
            'vertex="1" parent="1"><mxGeometry x="20" y="20" width="60" height="40" as="geometry" /></mxCell>'
        )
        issues = analyze_drawio_xml(xml_text)
        warped = [issue for issue in issues if "deviating" in issue.message]
        self.assertEqual(1, len(warped))

    def test_square_glyph_passes(self):
        xml_text = self._xml(
            '<mxCell id="n1" value="Card" style="rounded=1;fillColor=#ffffff;fontColor=#212529;" vertex="1" parent="1">'
            '<mxGeometry x="20" y="20" width="190" height="90" as="geometry" /></mxCell>'
            '<mxCell id="n1__icon" value="" style="shape=mxgraph.azure.key_vaults;aspect=fixed;" vertex="1" parent="n1">'
            '<mxGeometry x="1" width="40" height="40" relative="1" as="geometry" /></mxCell>'
        )
        issues = analyze_drawio_xml(xml_text)
        self.assertEqual([], [issue for issue in issues if "aspect" in issue.message.lower() or "deviating" in issue.message])


if __name__ == "__main__":
    unittest.main()

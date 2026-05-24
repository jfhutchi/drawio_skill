import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.diagram_model import Diagram, Node
from drawio_generator.visual_patterns import recommend_visual_pattern, render_visual_guide


class VisualPatternTests(unittest.TestCase):
    def test_recommends_azure_reference_pattern_for_azure_cloud_architecture(self):
        diagram = Diagram(
            title="Azure Cloud Architecture",
            diagram_type="cloud",
            nodes=[
                Node(id="traffic-manager", label="Traffic Manager", node_type="gateway"),
                Node(id="web-tier", label="Web Tier", node_type="server"),
                Node(id="sql", label="SQL Server Always On", node_type="database"),
            ],
        )

        pattern = recommend_visual_pattern(
            diagram,
            "Azure cloud architecture with primary region, secondary region, web tier, business tier, and SQL Server Always On.",
        )

        self.assertEqual("azure-reference", pattern.pattern_id)
        self.assertIn("region", pattern.layout_rules[0].lower())
        self.assertIn("Azure blue", pattern.palette)
        self.assertIn("Primary/secondary region containers", pattern.bands)

    def test_recommends_data_platform_pattern_for_lakehouse_pipeline(self):
        diagram = Diagram(
            title="Data Platform",
            diagram_type="enterprise",
            nodes=[
                Node(id="event-hubs", label="Azure Event Hubs", node_type="queue"),
                Node(id="databricks", label="Azure Databricks", node_type="process"),
                Node(id="delta", label="Delta Lake", node_type="database"),
                Node(id="power-bi", label="Power BI", node_type="dashboard"),
            ],
        )

        pattern = recommend_visual_pattern(
            diagram,
            "Create a Microsoft Azure data platform diagram with sources, process, store, serve, Databricks, Delta Lake, Fabric, and Power BI.",
        )

        self.assertEqual("data-platform-pipeline", pattern.pattern_id)
        self.assertIn("Sources -> Process -> Store -> Serve", pattern.flow)
        self.assertIn("numbered green callouts", " ".join(pattern.callout_rules).lower())

    def test_recommends_presentation_pattern_for_branded_protocol_diagram(self):
        diagram = Diagram(
            title="Immutable Proof",
            diagram_type="enterprise",
            nodes=[
                Node(id="devices", label="Devices", node_type="server"),
                Node(id="agent", label="Protocol Agent", node_type="process"),
                Node(id="blockchain", label="Post-Quantum Blockchain", node_type="database"),
            ],
        )

        pattern = recommend_visual_pattern(
            diagram,
            "Create a branded Naoris Protocol immutable real time proof architecture slide.",
        )
        markdown = render_visual_guide(pattern)

        self.assertEqual("presentation-architecture", pattern.pattern_id)
        self.assertIn("dark presentation canvas", pattern.palette.lower())
        self.assertIn("# Visual Guide", markdown)
        self.assertIn("Presentation Architecture", markdown)


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.diagram_model import Diagram, Edge, Node
from drawio_generator.drawio_xml import generate_drawio_xml


class ValidationScriptTests(unittest.TestCase):
    def test_validation_script_accepts_valid_drawio_and_emits_json(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            drawio_path = Path(temp_dir) / "valid.drawio"
            drawio_path.write_text(
                generate_drawio_xml(
                    Diagram(
                        title="Valid",
                        nodes=[
                            Node(id="api", label="API", node_type="api"),
                            Node(id="db", label="Database", node_type="database"),
                        ],
                        edges=[Edge(id="edge-api-db", source="api", target="db", label="SQL")],
                    )
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(root / "validation" / "validate_drawio.py"), str(drawio_path), "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(payload["valid"])
            self.assertEqual([], payload["errors"])

    def test_validation_script_rejects_missing_edge_target(self):
        root = Path(__file__).resolve().parents[1]
        bad_xml = """<mxfile host="app.diagrams.net"><diagram name="bad"><mxGraphModel><root>
        <mxCell id="0"/><mxCell id="1" parent="0"/>
        <mxCell id="api" value="API" vertex="1" parent="1"><mxGeometry x="10" y="10" width="80" height="40" as="geometry"/></mxCell>
        <mxCell id="edge-1" value="bad" edge="1" parent="1" source="api" target="missing"><mxGeometry relative="1" as="geometry"/></mxCell>
        </root></mxGraphModel></diagram></mxfile>"""
        with tempfile.TemporaryDirectory() as temp_dir:
            drawio_path = Path(temp_dir) / "invalid.drawio"
            drawio_path.write_text(bad_xml, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(root / "validation" / "validate_drawio.py"), str(drawio_path)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("missing target", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()

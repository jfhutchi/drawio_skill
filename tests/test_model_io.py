import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import asdict, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator import model_io
from drawio_generator.cli import main
from drawio_generator.diagram_model import Boundary, Diagram, Edge, LegendItem, Node
from drawio_generator.drawio_xml import generate_drawio_xml
from drawio_generator.model_io import ModelValidationError, diagram_from_dict, diagram_to_dict


def _sample_model() -> dict:
    return {
        "title": "Model Sample",
        "diagram_type": "enterprise",
        "direction": "left-to-right",
        "boundaries": [{"id": "boundary-app", "label": "Application Zone", "boundary_type": "logical"}],
        "nodes": [
            {"id": "web", "label": "Web Frontend", "node_type": "frontend", "group": "boundary-app"},
            {"id": "db", "label": "Orders Database", "node_type": "database", "group": "boundary-app"},
        ],
        "edges": [
            {"id": "edge-web-db", "source": "web", "target": "db", "label": "SQL over TLS", "metadata": {"sequence": 1}},
        ],
        "legends": [{"label": "Blue", "meaning": "Application flow"}],
        "assumptions": ["Authored by the agent."],
    }


class ModelIoTests(unittest.TestCase):
    def test_round_trip_model_to_diagram_to_xml(self):
        payload = _sample_model()
        diagram = diagram_from_dict(payload)
        self.assertEqual("Model Sample", diagram.title)
        self.assertEqual(["web", "db"], [node.id for node in diagram.nodes])

        # dict -> Diagram -> dict -> Diagram is stable
        second = diagram_from_dict(json.loads(json.dumps(diagram_to_dict(diagram))))
        self.assertEqual(asdict(diagram), asdict(second))

        xml_text = generate_drawio_xml(diagram)
        root = ET.fromstring(xml_text)
        self.assertEqual("mxfile", root.tag)

    def test_dangling_edge_endpoint_rejected_with_json_path(self):
        payload = _sample_model()
        payload["edges"][0]["target"] = "missing-node"
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any("$.edges[0].target" in error and "missing-node" in error for error in ctx.exception.errors), ctx.exception.errors)

    def test_duplicate_ids_rejected_with_useful_message(self):
        payload = _sample_model()
        payload["nodes"].append({"id": "web", "label": "Second Web"})
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any("duplicate id" in error and "'web'" in error for error in ctx.exception.errors), ctx.exception.errors)

    def test_unknown_field_rejected(self):
        payload = _sample_model()
        payload["nodes"][0]["nodetype"] = "typo"
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any("$.nodes[0].nodetype: unknown field" in error for error in ctx.exception.errors), ctx.exception.errors)

    def test_missing_nodes_rejected(self):
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict({"title": "Empty", "edges": []})
        self.assertTrue(any("$.nodes" in error for error in ctx.exception.errors), ctx.exception.errors)

    def test_group_referencing_missing_boundary_rejected(self):
        payload = _sample_model()
        payload["nodes"][0]["group"] = "boundary-nope"
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any("$.nodes[0].group" in error for error in ctx.exception.errors), ctx.exception.errors)

    def test_dump_and_load_file_round_trip(self):
        diagram = diagram_from_dict(_sample_model())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.json"
            model_io.dump_model(diagram, path)
            loaded = model_io.load_model(path)
            self.assertEqual(asdict(diagram), asdict(loaded))


class SchemaDriftTests(unittest.TestCase):
    def test_schema_properties_match_dataclass_fields(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "schemas" / "diagram-model.schema.json").read_text(encoding="utf-8"))

        from drawio_generator.diagram_model import Annotation

        self.assertEqual({field.name for field in fields(Diagram)}, set(schema["properties"]))
        pairs = [
            (Boundary, schema["properties"]["boundaries"]["items"]),
            (Node, schema["properties"]["nodes"]["items"]),
            (Edge, schema["properties"]["edges"]["items"]),
            (LegendItem, schema["properties"]["legends"]["items"]),
            (Annotation, schema["properties"]["annotations"]["items"]),
        ]
        for dataclass_type, item_schema in pairs:
            self.assertEqual(
                {field.name for field in fields(dataclass_type)},
                set(item_schema["properties"]),
                dataclass_type.__name__,
            )


class ModelCliTests(unittest.TestCase):
    def test_cli_model_flag_trusts_the_model(self):
        payload = _sample_model()
        # An icon the agent found via draw.io shape search rides through
        # the model into the emitted XML as a glyph child.
        payload["nodes"][0]["icon"] = "mxgraph.weblogos.github"
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            model_path.write_text(json.dumps(payload), encoding="utf-8")
            output = Path(temp_dir) / "out"
            exit_code = main(["--model", str(model_path), "--output", str(output), "--validate"])
            self.assertEqual(0, exit_code)
            xml_text = (output / "diagram.drawio").read_text(encoding="utf-8")
            # Labels are exactly as authored - no extraction, no regrouping.
            self.assertIn("Web Frontend", xml_text)
            self.assertIn("Orders Database", xml_text)
            self.assertIn("shape=mxgraph.weblogos.github", xml_text)
            render_qa = (output / "render-qa.md").read_text(encoding="utf-8")
            self.assertTrue(render_qa.startswith("RESULT:"), render_qa.splitlines()[0])

    def test_cli_model_validation_errors_exit_2(self):
        payload = _sample_model()
        payload["edges"][0]["target"] = "missing-node"
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            model_path.write_text(json.dumps(payload), encoding="utf-8")
            output = Path(temp_dir) / "out"
            exit_code = main(["--model", str(model_path), "--output", str(output)])
            self.assertEqual(2, exit_code)

    def test_cli_model_and_input_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            model_path.write_text(json.dumps(_sample_model()), encoding="utf-8")
            with self.assertRaises(SystemExit):
                main(["--model", str(model_path), "--input", str(model_path), "--output", temp_dir])

    def test_cli_requires_request_or_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(SystemExit):
                main(["--output", temp_dir])


if __name__ == "__main__":
    unittest.main()

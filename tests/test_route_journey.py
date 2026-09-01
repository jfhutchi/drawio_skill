import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.interactive_html import main, render_interactive_html, route_node_sequence
from drawio_generator.model_io import ModelValidationError, diagram_from_dict


def _payload() -> dict:
    return {
        "title": "Animated Request Route",
        "direction": "left-to-right",
        "nodes": [
            {"id": "user", "label": "User", "node_type": "user", "layer": "client"},
            {"id": "api", "label": "API Gateway", "node_type": "api", "layer": "application"},
            {"id": "db", "label": "Orders DB", "node_type": "database", "layer": "data"},
        ],
        "edges": [
            {
                "id": "user-api",
                "source": "user",
                "target": "api",
                "label": "HTTPS",
                "protocol": "HTTPS :443",
            },
            {
                "id": "db-api",
                "source": "db",
                "target": "api",
                "label": "SQL over TLS",
                "protocol": "TDS :1433",
                "security_control": "TLS",
            },
        ],
        "routes": [
            {
                "id": "request",
                "label": "User Request",
                "edge_ids": ["user-api", "db-api"],
                "description": "Trace the request from the user through the API to the database.",
                "animation": {"style": "both", "speed": 1.25, "dwell_ms": 250, "loop": False},
            }
        ],
    }


class RouteModelTests(unittest.TestCase):
    def test_route_round_trip_and_reverse_edge_traversal(self):
        diagram = diagram_from_dict(_payload())
        self.assertEqual(["user", "api", "db"], route_node_sequence(diagram, diagram.routes[0]))
        self.assertEqual("both", diagram.routes[0].animation.style)
        self.assertEqual(1.25, diagram.routes[0].animation.speed)

    def test_missing_route_edge_is_rejected(self):
        payload = _payload()
        payload["routes"][0]["edge_ids"].append("missing")
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any("$.routes[0].edge_ids" in error and "missing" in error for error in ctx.exception.errors))

    def test_noncontiguous_route_is_rejected(self):
        payload = _payload()
        payload["nodes"].append({"id": "queue", "label": "Queue"})
        payload["nodes"].append({"id": "worker", "label": "Worker"})
        payload["edges"].append({"id": "queue-worker", "source": "queue", "target": "worker", "label": "AMQP"})
        payload["routes"][0]["edge_ids"] = ["user-api", "queue-worker"]
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any("not contiguous" in error for error in ctx.exception.errors), ctx.exception.errors)

    def test_invalid_animation_settings_are_rejected(self):
        payload = _payload()
        payload["routes"][0]["animation"]["style"] = "hologram"
        payload["routes"][0]["animation"]["speed"] = 0
        with self.assertRaises(ModelValidationError) as ctx:
            diagram_from_dict(payload)
        self.assertTrue(any(".animation.style" in error for error in ctx.exception.errors))
        self.assertTrue(any(".animation.speed" in error for error in ctx.exception.errors))


class InteractiveRouteViewerTests(unittest.TestCase):
    def test_html_contains_accessible_finite_route_journey_runtime(self):
        html = render_interactive_html(diagram_from_dict(_payload()))
        self.assertIn('aria-label="Route journey controls"', html)
        self.assertIn('aria-label="Play route journey"', html)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn("getPointAtLength", html)
        self.assertIn("prefers-reduced-motion: reduce", html)
        self.assertIn('window.addEventListener("beforeprint"', html)
        self.assertIn("preserveProgress: true", html)
        self.assertIn("#route=", html)
        self.assertNotIn("#journey=", html)
        self.assertIn('data-edge-id="user-api"', html)
        self.assertIn('data-edge-id="db-api"', html)
        self.assertIn('"reverse": true', html)
        self.assertIn('data-node-id="api"', html)
        self.assertIn("Overview", html)

    def test_command_writes_self_contained_html(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model = Path(temp_dir) / "route.json"
            output = Path(temp_dir) / "route.interactive.html"
            model.write_text(json.dumps(_payload()), encoding="utf-8")
            self.assertEqual(0, main(["--model", str(model), "--output", str(output)]))
            html = output.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            self.assertIn("User Request", html)
            self.assertIn("<svg", html)


if __name__ == "__main__":
    unittest.main()

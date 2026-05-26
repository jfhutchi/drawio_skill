import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.adversarial_review import improve_diagram, review_diagram
from drawio_generator.diagram_model import Diagram, Edge, Node
from drawio_generator.validators import (
    contains_secret,
    redact_sensitive_text,
    validate_model,
    validate_vendor_shape_accuracy,
)


class SecurityAndReviewTests(unittest.TestCase):
    def test_redacts_connection_strings_tokens_and_private_keys(self):
        text = """
        postgres://app:super-secret-password@db.internal:5432/orders
        Authorization: Bearer eyJhbGciOiJIUzI1Ni.fake.token
        -----BEGIN PRIVATE KEY-----
        abc123
        -----END PRIVATE KEY-----
        """

        redacted = redact_sensitive_text(text)

        self.assertNotIn("super-secret-password", redacted)
        self.assertNotIn("eyJhbGciOiJIUzI1Ni.fake.token", redacted)
        self.assertNotIn("abc123", redacted)
        self.assertIn("REDACTED", redacted)
        self.assertFalse(contains_secret(redacted))

    def test_adversarial_review_flags_missing_enterprise_controls_and_improves_model(self):
        diagram = Diagram(
            title="Application",
            diagram_type="enterprise",
            nodes=[
                Node(id="web", label="Web App", node_type="frontend"),
                Node(id="db", label="Database", node_type="database"),
            ],
            edges=[Edge(id="edge-1", source="web", target="db", label="reads and writes")],
        )

        findings = review_diagram(diagram)
        messages = [finding.message for finding in findings]
        improved = improve_diagram(diagram, findings)

        self.assertTrue(any("legend" in message.lower() for message in messages))
        self.assertTrue(any("trust boundary" in message.lower() for message in messages))
        self.assertGreater(len(improved.legends), len(diagram.legends))
        self.assertTrue(improved.assumptions)
        self.assertTrue(improved.quality_checks)


    def test_vendor_shape_accuracy_flags_unrecognized_vendor_service(self):
        diagram = Diagram(
            title="Test",
            nodes=[
                Node(id="known", label="Azure Key Vault"),
                Node(id="generic", label="Azure Imaginary Service"),
                Node(id="aws_known", label="Amazon S3"),
                Node(id="aws_generic", label="Amazon Imaginary"),
                Node(id="non_vendor", label="Custom Service"),
            ],
        )

        issues = validate_vendor_shape_accuracy(diagram)
        flagged_ids = sorted(issue.item_id for issue in issues if issue.item_id)

        self.assertEqual(["aws_generic", "generic"], flagged_ids)
        for issue in issues:
            self.assertEqual("warning", issue.severity)
            self.assertIn("generic fallback", issue.message.lower())

    def test_validate_model_includes_vendor_shape_accuracy_warnings(self):
        diagram = Diagram(
            title="Test",
            nodes=[Node(id="bogus", label="Azure Bogus Service")],
        )

        issues = validate_model(diagram)
        warnings = [issue for issue in issues if issue.severity == "warning"]

        self.assertTrue(
            any("generic fallback" in issue.message.lower() for issue in warnings),
            warnings,
        )


if __name__ == "__main__":
    unittest.main()

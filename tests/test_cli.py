import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.cli import _title_from_request, detect_diagram_type


class CliTests(unittest.TestCase):
    def test_explicit_enterprise_architecture_request_wins_over_tool_keywords(self):
        diagram_type = detect_diagram_type(
            "Create an enterprise architecture diagram for an Azure-hosted web application "
            "using AKS, PostgreSQL, GitHub Actions, Terraform, Prometheus, and Grafana."
        )

        self.assertEqual("enterprise", diagram_type)

    def test_title_builder_creates_polished_enterprise_titles(self):
        title = _title_from_request(
            "Create an enterprise architecture diagram for an Azure-hosted web application "
            "using AKS, PostgreSQL, GitHub Actions, Terraform, Prometheus, and Grafana.",
            "enterprise",
        )

        self.assertEqual("Azure Enterprise Architecture", title)

    def test_cli_writes_required_enterprise_outputs(self):
        skill_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            notes = temp_path / "azure-notes.md"
            output = temp_path / "output"
            notes.write_text(
                "Azure Front Door sends HTTPS traffic to AKS. AKS reads secrets "
                "from Key Vault and stores data in Azure Database for PostgreSQL. "
                "GitHub Actions runs Terraform. Prometheus and Grafana monitor it.",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PYTHONPATH"] = str(skill_root / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "drawio_generator.cli",
                    "--request",
                    "Create an enterprise architecture diagram for an Azure AKS application.",
                    "--input",
                    str(notes),
                    "--output",
                    str(output),
                    "--validate",
                ],
                cwd=skill_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((output / "diagram.drawio").exists())
            self.assertTrue((output / "diagram-summary.md").exists())
            self.assertTrue((output / "assumptions.md").exists())
            self.assertTrue((output / "adversarial-review.md").exists())
            self.assertTrue((output / "quality-checklist.md").exists())
            self.assertTrue((output / "page-plan.md").exists())
            ET.fromstring((output / "diagram.drawio").read_text(encoding="utf-8"))
            self.assertIn("AKS", (output / "diagram-summary.md").read_text(encoding="utf-8"))
            page_plan = (output / "page-plan.md").read_text(encoding="utf-8")
            self.assertIn("Executive Overview", page_plan)
            self.assertIn("Page 1 should be understandable", page_plan)


if __name__ == "__main__":
    unittest.main()

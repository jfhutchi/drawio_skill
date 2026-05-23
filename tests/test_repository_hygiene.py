import unittest
from pathlib import Path


class RepositoryHygieneTests(unittest.TestCase):
    def test_gitignore_excludes_generated_and_local_artifacts_but_keeps_source(self):
        root = Path(__file__).resolve().parents[1]
        gitignore = (root / ".gitignore").read_text(encoding="utf-8")

        for pattern in [
            "__pycache__/",
            "*.py[cod]",
            ".pytest_cache/",
            "output/*",
            "*.egg-info/",
            ".venv/",
            ".env",
            "enterprise-drawio-diagrammer-ms365.zip",
        ]:
            self.assertIn(pattern, gitignore)

        self.assertIn("!output/.gitkeep", gitignore)

    def test_ci_workflow_runs_tests_validation_install_dry_run_and_ms365_packaging(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        for expected in [
            "python -m unittest discover -s tests",
            "python validation/validate_drawio.py output/diagram.drawio",
            "python install.py --all-local --dry-run",
            "python platforms/ms365-copilot/package_ms365.py",
            "actions/setup-python@v5",
        ]:
            self.assertIn(expected, workflow)

    def test_package_workflow_uploads_skill_and_ms365_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "package.yml").read_text(encoding="utf-8")

        for expected in [
            "workflow_dispatch:",
            "tags:",
            "enterprise-drawio-diagrammer.skill.zip",
            "enterprise-drawio-diagrammer-ms365.zip",
            "actions/upload-artifact@v4",
        ]:
            self.assertIn(expected, workflow)


if __name__ == "__main__":
    unittest.main()

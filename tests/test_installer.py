import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InstallerTests(unittest.TestCase):
    def test_installer_dry_run_reports_destination_without_copying(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "skills"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "install.py"),
                    "--target-dir",
                    str(target),
                    "--dry-run",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("DRY RUN", result.stdout)
            self.assertIn("enterprise-drawio-diagrammer", result.stdout)
            self.assertFalse((target / "enterprise-drawio-diagrammer").exists())

    def test_installer_copies_skill_without_generated_output(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "skills"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "install.py"),
                    "--target-dir",
                    str(target),
                    "--yes",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            installed = target / "enterprise-drawio-diagrammer"
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((installed / "SKILL.md").exists())
            self.assertTrue((installed / "src" / "drawio_generator" / "validators.py").exists())
            self.assertTrue((installed / "validation" / "validate_drawio.py").exists())
            self.assertFalse((installed / "output").exists())

    def test_installer_all_local_dry_run_mentions_codex_claude_and_copilot_targets(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "install.py"),
                    "--all-local",
                    "--home",
                    str(home),
                    "--dry-run",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(str(home / ".codex" / "skills" / "enterprise-drawio-diagrammer"), result.stdout)
            self.assertIn(str(home / ".claude" / "skills" / "enterprise-drawio-diagrammer"), result.stdout)
            self.assertIn(str(home / ".copilot" / "skills" / "enterprise-drawio-diagrammer"), result.stdout)


if __name__ == "__main__":
    unittest.main()

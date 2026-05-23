import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


class PlatformAdapterTests(unittest.TestCase):
    def test_platform_adapter_files_exist(self):
        root = Path(__file__).resolve().parents[1]
        required = [
            root / "platforms" / "claude" / "README.md",
            root / "platforms" / "github-copilot" / "README.md",
            root / "platforms" / "github-copilot" / ".github" / "copilot-instructions.md",
            root / "platforms" / "github-copilot" / ".github" / "prompts" / "enterprise-drawio-diagrammer.prompt.md",
            root / "platforms" / "github-copilot" / "AGENTS.md",
            root / "platforms" / "ms365-copilot" / "README.md",
            root / "platforms" / "ms365-copilot" / "package_ms365.py",
            root / "platforms" / "ms365-copilot" / "appPackage" / "manifest.json",
            root / "platforms" / "ms365-copilot" / "appPackage" / "declarativeAgent.json",
            root / "platforms" / "ms365-copilot" / "appPackage" / "color.png",
            root / "platforms" / "ms365-copilot" / "appPackage" / "outline.png",
        ]

        for path in required:
            self.assertTrue(path.exists(), f"Missing platform adapter: {path}")
            self.assertGreater(path.stat().st_size, 20, f"Adapter file is unexpectedly small: {path}")

    def test_ms365_manifest_references_declarative_agent_and_icons(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "platforms" / "ms365-copilot" / "appPackage" / "manifest.json").read_text(encoding="utf-8"))
        agent = json.loads((root / "platforms" / "ms365-copilot" / "appPackage" / "declarativeAgent.json").read_text(encoding="utf-8"))

        declarative_agents = manifest["copilotAgents"]["declarativeAgents"]
        self.assertEqual("declarativeAgent.json", declarative_agents[0]["file"])
        self.assertEqual("color.png", manifest["icons"]["color"])
        self.assertEqual("outline.png", manifest["icons"]["outline"])
        self.assertEqual("v1.6", agent["version"])
        self.assertIn("draw.io", agent["instructions"])

    def test_ms365_package_script_creates_zip_with_required_app_package_files(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / "enterprise-drawio-diagrammer-ms365.zip"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "platforms" / "ms365-copilot" / "package_ms365.py"),
                    "--output",
                    str(package_path),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            with zipfile.ZipFile(package_path) as archive:
                names = set(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("declarativeAgent.json", names)
            self.assertIn("color.png", names)
            self.assertIn("outline.png", names)


if __name__ == "__main__":
    unittest.main()

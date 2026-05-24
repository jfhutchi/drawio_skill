import json
import unittest
from pathlib import Path


class SkillArtifactTests(unittest.TestCase):
    def test_required_skill_files_and_directories_exist(self):
        root = Path(__file__).resolve().parents[1]
        required_paths = [
            root / "SKILL.md",
            root / "README.md",
            root / "examples" / "azure-enterprise-request.txt",
            root / "templates" / "model-template.yaml",
            root / "stencils" / "icon-registry.md",
            root / "schemas" / "diagram-model.schema.json",
            root / "prompts" / "adversarial-review.md",
            root / "validation" / "drawio-validation-checklist.md",
            root / "src" / "drawio_generator" / "visual_patterns.py",
            root / "src" / "drawio_generator" / "page_planner.py",
            root / "docs" / "extending-the-skill.md",
            root / "docs" / "limitations.md",
            root / "validation" / "validate_drawio.py",
            root / "install.py",
            root / "install.bat",
            root / "install.ps1",
            root / "install.sh",
        ]

        for path in required_paths:
            self.assertTrue(path.exists(), f"Missing required artifact: {path}")
            self.assertGreater(path.stat().st_size, 100, f"Artifact is too small to be useful: {path}")

    def test_schema_is_valid_json_and_documents_core_model_fields(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "schemas" / "diagram-model.schema.json").read_text(encoding="utf-8"))

        required = set(schema["required"])
        self.assertIn("title", required)
        self.assertIn("nodes", required)
        self.assertIn("edges", required)
        self.assertIn("assumptions", schema["properties"])
        self.assertIn("unknowns", schema["properties"])

    def test_skill_and_readme_document_page_plan_output(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")

        self.assertIn("page-plan.md", skill)
        self.assertIn("page-plan.md", readme)

    def test_skill_and_readme_document_visual_guide_output(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")

        self.assertIn("visual-guide.md", skill)
        self.assertIn("visual-guide.md", readme)


if __name__ == "__main__":
    unittest.main()

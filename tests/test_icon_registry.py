import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.icon_registry import get_icon_style, refresh_icon_packs


class IconRegistryTests(unittest.TestCase):
    def tearDown(self):
        refresh_icon_packs([])

    def test_vendor_service_aliases_use_safe_builtin_fallbacks_by_default(self):
        refresh_icon_packs([])
        aks = get_icon_style("component", "Azure Kubernetes Service")
        s3 = get_icon_style("component", "Amazon S3")
        lambda_fn = get_icon_style("component", "AWS Lambda")

        self.assertEqual("azure", aks.vendor)
        self.assertEqual("aws", s3.vendor)
        self.assertEqual("aws", lambda_fn.vendor)
        self.assertFalse(aks.official)
        self.assertFalse(s3.official)
        self.assertFalse(lambda_fn.official)
        self.assertIn("built-in fallback", aks.license_notice.lower())
        self.assertIn("built-in fallback", s3.license_notice.lower())
        self.assertIn("built-in fallback", lambda_fn.license_notice.lower())
        self.assertNotIn("official", aks.fallback_label.lower())
        self.assertNotIn("official", s3.fallback_label.lower())

    def test_unknown_vendor_label_does_not_claim_official_icon(self):
        refresh_icon_packs([])
        style = get_icon_style("component", "Azure Imaginary Service")

        self.assertFalse(style.official)
        self.assertEqual("fallback", style.category)
        self.assertIn("fillColor=#f8f9fa", style.drawio_style)

    def test_licensed_pack_marks_icon_official(self):
        with tempfile.TemporaryDirectory() as tmp:
            stencils = Path(tmp) / "stencils"
            azure_dir = stencils / "azure"
            azure_dir.mkdir(parents=True)
            (azure_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "vendor": "azure",
                        "license_acknowledged": True,
                        "license_notice": "Azure icons licensed under enterprise agreement EA-123",
                        "shapes": {
                            "azure kubernetes service": "shape=mscae/Kubernetes_Services;html=1;",
                            "key vault": "shape=mscae/Key_Vaults;html=1;",
                        },
                    }
                ),
                encoding="utf-8",
            )
            refresh_icon_packs([stencils])

            aks = get_icon_style("component", "Azure Kubernetes Service")
            vault = get_icon_style("component", "Key Vault")
            other = get_icon_style("component", "Amazon S3")

            self.assertTrue(aks.official)
            self.assertEqual("azure-official", aks.category)
            self.assertIn("mscae/Kubernetes_Services", aks.drawio_style)
            self.assertIn("Azure icons licensed", aks.license_notice)
            self.assertTrue(vault.official)
            self.assertFalse(other.official)

    def test_manifest_without_license_acknowledgement_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            stencils = Path(tmp) / "stencils"
            azure_dir = stencils / "azure"
            azure_dir.mkdir(parents=True)
            (azure_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "vendor": "azure",
                        "license_acknowledged": False,
                        "shapes": {
                            "azure kubernetes service": "shape=mscae/Kubernetes_Services;html=1;",
                        },
                    }
                ),
                encoding="utf-8",
            )
            refresh_icon_packs([stencils])

            aks = get_icon_style("component", "Azure Kubernetes Service")

            self.assertFalse(aks.official)
            self.assertIn("built-in fallback", aks.license_notice.lower())


if __name__ == "__main__":
    unittest.main()

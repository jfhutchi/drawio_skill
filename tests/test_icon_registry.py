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

    def test_recognized_azure_services_use_builtin_vendor_stencils(self):
        refresh_icon_packs([])
        aks = get_icon_style("component", "Azure Kubernetes Service")
        vault = get_icon_style("component", "Key Vault")
        front_door = get_icon_style("component", "Azure Front Door")

        self.assertEqual("azure", aks.vendor)
        self.assertEqual("azure", vault.vendor)
        self.assertEqual("azure", front_door.vendor)
        self.assertFalse(aks.official)
        self.assertIn("shape=mxgraph.azure.kubernetes_services", aks.drawio_style)
        self.assertIn("shape=mxgraph.azure.key_vaults", vault.drawio_style)
        self.assertIn("shape=mxgraph.azure.front_doors", front_door.drawio_style)
        self.assertIn("built-in azure stencil", aks.license_notice.lower())

    def test_recognized_aws_services_use_builtin_vendor_stencils(self):
        refresh_icon_packs([])
        s3 = get_icon_style("component", "Amazon S3")
        lambda_fn = get_icon_style("component", "AWS Lambda")
        eks = get_icon_style("component", "Amazon EKS")
        iam = get_icon_style("component", "AWS IAM")

        self.assertEqual("aws", s3.vendor)
        self.assertEqual("aws", lambda_fn.vendor)
        self.assertEqual("aws", eks.vendor)
        self.assertEqual("aws", iam.vendor)
        self.assertFalse(s3.official)
        self.assertIn("resIcon=mxgraph.aws4.simple_storage_service_s3", s3.drawio_style)
        self.assertIn("resIcon=mxgraph.aws4.lambda", lambda_fn.drawio_style)
        self.assertIn("resIcon=mxgraph.aws4.elastic_kubernetes_service", eks.drawio_style)
        self.assertIn("resIcon=mxgraph.aws4.identity_and_access_management_iam", iam.drawio_style)

    def test_recognized_gcp_services_use_builtin_vendor_stencils(self):
        refresh_icon_packs([])
        gke = get_icon_style("component", "Google Kubernetes Engine")
        bq = get_icon_style("component", "BigQuery")
        run = get_icon_style("component", "Cloud Run")

        self.assertEqual("gcp", gke.vendor)
        self.assertEqual("gcp", bq.vendor)
        self.assertEqual("gcp", run.vendor)
        self.assertIn("shape=mxgraph.gcp2.kubernetes_engine", gke.drawio_style)
        self.assertIn("shape=mxgraph.gcp2.bigquery", bq.drawio_style)
        self.assertIn("shape=mxgraph.gcp2.cloud_run", run.drawio_style)

    def test_recognized_kubernetes_resources_use_builtin_vendor_stencils(self):
        refresh_icon_packs([])
        pod = get_icon_style("component", "Kubernetes Pod")
        svc = get_icon_style("component", "Kubernetes Service")
        ing = get_icon_style("component", "Kubernetes Ingress")
        cm = get_icon_style("component", "Kubernetes ConfigMap")

        self.assertEqual("kubernetes", pod.vendor)
        self.assertEqual("kubernetes", svc.vendor)
        self.assertEqual("kubernetes", ing.vendor)
        self.assertEqual("kubernetes", cm.vendor)
        self.assertIn("shape=mxgraph.kubernetes.icon", pod.drawio_style)
        self.assertIn("prIcon=pod", pod.drawio_style)
        self.assertIn("prIcon=svc", svc.drawio_style)
        self.assertIn("prIcon=ing", ing.drawio_style)
        self.assertIn("prIcon=cm", cm.drawio_style)

    def test_alias_to_kubernetes_still_resolves_to_builtin(self):
        # Existing alias "azure kubernetes service" -> "kubernetes" generic key.
        # That alias should no longer downgrade an Azure service to a generic
        # shape: the Azure built-in stencil must win.
        refresh_icon_packs([])
        style = get_icon_style("component", "Azure Kubernetes Service")

        self.assertEqual("azure", style.vendor)
        self.assertIn("mxgraph.azure", style.drawio_style)
        self.assertNotIn("fillColor=#dae8fc", style.drawio_style)

    def test_unknown_vendor_service_keeps_vendor_tagged_fallback(self):
        refresh_icon_packs([])
        style = get_icon_style("component", "Azure Imaginary Service")

        self.assertEqual("azure", style.vendor)
        self.assertFalse(style.official)
        self.assertEqual("fallback", style.category)
        self.assertIn("fillColor=#f8f9fa", style.drawio_style)
        self.assertIn("built-in fallback", style.license_notice.lower())

    def test_non_vendor_node_unchanged(self):
        refresh_icon_packs([])
        style = get_icon_style("database", None)

        self.assertIsNone(style.vendor)
        self.assertIn("cylinder3d", style.drawio_style)

    def test_licensed_pack_marks_icon_official_and_overrides_builtin(self):
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
            # AWS service still resolves to its built-in vendor stencil.
            self.assertFalse(other.official)
            self.assertIn("resIcon=mxgraph.aws4.simple_storage_service_s3", other.drawio_style)

    def test_manifest_without_license_acknowledgement_falls_back_to_builtin(self):
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
            # Without acknowledgement the licensed pack is ignored, but the
            # built-in diagrams.net Azure stencil is still used.
            self.assertIn("shape=mxgraph.azure.kubernetes_services", aks.drawio_style)


if __name__ == "__main__":
    unittest.main()

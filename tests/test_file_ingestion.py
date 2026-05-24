import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.file_ingestion import ExtractionResult, extract_components_from_text


class FileIngestionTests(unittest.TestCase):
    def test_extracts_components_from_architecture_markdown(self):
        text = """
        The Azure application uses Azure Front Door, Application Gateway WAF,
        AKS, Key Vault, Azure Database for PostgreSQL, GitHub Actions,
        Terraform, Prometheus, Grafana, and Log Analytics.
        """

        result = extract_components_from_text("notes.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("Azure Front Door", labels)
        self.assertIn("AKS", labels)
        self.assertIn("Azure Database for PostgreSQL", labels)
        self.assertIn("GitHub Actions", labels)
        self.assertNotIn("Application Gateway", labels)
        self.assertNotIn("PostgreSQL", labels)

    def test_aggregate_prefers_specific_components_over_generic_earlier_mentions(self):
        aggregate = ExtractionResult()
        aggregate.extend(extract_components_from_text("request", "Use PostgreSQL and Application Gateway."))
        aggregate.extend(
            extract_components_from_text(
                "notes.md",
                "The target platform is Azure Database for PostgreSQL behind Application Gateway WAF.",
            )
        )

        labels = {component.label for component in aggregate.components}

        self.assertIn("Azure Database for PostgreSQL", labels)
        self.assertIn("Application Gateway WAF", labels)
        self.assertNotIn("PostgreSQL", labels)
        self.assertNotIn("Application Gateway", labels)

    def test_extracts_kubernetes_terraform_github_actions_and_otel_hints(self):
        text = """
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: payments-api
          namespace: commerce
        ---
        resource "azurerm_key_vault" "main" {}
        jobs:
          build:
            steps:
              - uses: actions/checkout@v4
        receivers:
          otlp:
        exporters:
          prometheus:
        """

        result = extract_components_from_text("mixed.yaml", text)
        labels = {component.label for component in result.components}

        self.assertIn("Deployment/payments-api", labels)
        self.assertIn("Terraform azurerm_key_vault.main", labels)
        self.assertIn("GitHub Actions job: build", labels)
        self.assertIn("OpenTelemetry receiver: otlp", labels)
        self.assertIn("OpenTelemetry exporter: prometheus", labels)

    def test_collapses_ansible_tower_and_awx_into_one_controller_node(self):
        text = "Ansible Tower / AWX launches SHC jobs from a GitHub Repository."

        result = extract_components_from_text("tower-notes.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("Ansible Tower / AWX", labels)
        self.assertNotIn("Ansible Tower", labels)
        self.assertNotIn("AWX", labels)

    def test_extracts_shc_detail_nodes_for_page_planning(self):
        text = "Tower Runtime Inputs feed SHC Role Execution before reports are generated."

        result = extract_components_from_text("shc-notes.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("Tower Runtime Inputs", labels)
        self.assertIn("SHC Role Execution", labels)

    def test_does_not_invent_relationships_from_component_lists(self):
        text = (
            "Azure Front Door receives public HTTPS traffic and forwards approved traffic to Application Gateway WAF. "
            "Application Gateway routes traffic to workloads running in AKS. "
            "Workloads retrieve secrets from Key Vault and store application data in Azure Database for PostgreSQL. "
            "GitHub Actions runs Terraform to provision cloud resources and deploy changes. "
            "Prometheus collects metrics, Grafana displays dashboards, and Log Analytics stores logs."
        )

        result = extract_components_from_text("azure-notes.md", text)
        pairs = {(edge.source, edge.target) for edge in result.relationships}

        self.assertNotIn(("azure-database-for-postgresql", "prometheus"), pairs)
        self.assertNotIn(("azure-database-for-postgresql", "grafana"), pairs)


if __name__ == "__main__":
    unittest.main()

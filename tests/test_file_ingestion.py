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


    def test_auto_derives_vendor_services_from_shape_registry(self):
        # Services NOT in _CORE_KNOWN_COMPONENTS but present in
        # builtin_vendor_shapes should still get extracted.
        text = (
            "Architecture uses Azure Synapse Analytics for warehousing, "
            "AWS Glue for ETL, Google Vertex AI for ML serving, and "
            "Google Firestore for client sync."
        )

        result = extract_components_from_text("multi.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("Azure Synapse Analytics", labels)
        self.assertIn("AWS Glue", labels)
        self.assertIn("Google Vertex AI", labels)
        self.assertIn("Google Firestore", labels)

    def test_fuzzy_matches_variant_phrasings(self):
        text = (
            "Lambdas process events from EventBridge buses and write to S3 buckets. "
            "EKS clusters host pods that read from DynamoDB tables. "
            "Function apps push messages to Service Bus queues. "
            "k8s pods read ConfigMaps and persistent volume claims. "
            "BigQuery datasets feed Vertex AI endpoints. "
            "Cosmos DB containers store session state."
        )

        result = extract_components_from_text("variant.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("AWS Lambda", labels)
        self.assertIn("Amazon EventBridge", labels)
        self.assertIn("Amazon S3", labels)
        self.assertIn("Amazon EKS", labels)
        self.assertIn("Kubernetes Pod", labels)
        self.assertIn("Amazon DynamoDB", labels)
        self.assertIn("Azure Functions", labels)
        self.assertIn("Azure Service Bus", labels)
        self.assertIn("Kubernetes ConfigMap", labels)
        # The auto-derived label uses the PVC acronym for compactness;
        # accept either form so the test reflects what users see.
        self.assertTrue(
            "Kubernetes PVC" in labels or "Kubernetes Persistent Volume Claim" in labels,
            labels,
        )
        self.assertIn("Google BigQuery", labels)
        self.assertIn("Google Vertex AI", labels)
        self.assertIn("Azure Cosmos DB", labels)

    def test_preserves_input_casing_for_well_formed_labels(self):
        # Input has "AKS" -> label stays "AKS", not canonicalized away.
        text = "We deploy services to AKS in production."

        result = extract_components_from_text("notes.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("AKS", labels)

    def test_application_gateway_waf_does_not_also_extract_plain_gateway(self):
        text = "Inbound traffic flows through Application Gateway WAF only."

        result = extract_components_from_text("notes.md", text)
        labels = {component.label for component in result.components}

        self.assertIn("Application Gateway WAF", labels)
        # The shorter "application gateway" needle should not produce a
        # duplicate vendor node when it overlaps a longer match.
        self.assertNotIn("Azure Application Gateway", labels)


if __name__ == "__main__":
    unittest.main()

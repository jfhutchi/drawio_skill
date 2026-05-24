import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.cli import apply_visual_pattern_to_diagram
from drawio_generator.diagram_model import Boundary, Diagram, Node
from drawio_generator.layout_engine import (
    AWS_GROUP_ORDER,
    AZURE_GROUP_ORDER,
    DATA_PLATFORM_GROUP_ORDER,
    apply_layout,
)


class LayoutEngineTests(unittest.TestCase):
    def test_aws_pattern_places_compute_left_of_data_and_data_left_of_analytics(self):
        diagram = Diagram(
            title="AWS Reference",
            diagram_type="cloud",
            direction="left-to-right",
            nodes=[
                Node(id="users", label="Internet Users", node_type="user"),
                Node(id="cf", label="Amazon CloudFront", node_type="cdn"),
                Node(id="lambda", label="AWS Lambda", node_type="process"),
                Node(id="dynamo", label="Amazon DynamoDB", node_type="database"),
                Node(id="quicksight", label="Amazon QuickSight", node_type="dashboard"),
                Node(id="sns", label="Amazon SNS Notifications", node_type="consumer"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "aws-reference")
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}

        self.assertEqual("aws-reference", diagram.metadata["visual_pattern_id"])
        self.assertEqual("boundary-aws-compute", by_id["lambda"].group)
        self.assertEqual("boundary-aws-data", by_id["dynamo"].group)
        self.assertEqual("boundary-aws-analytics", by_id["quicksight"].group)
        self.assertEqual("boundary-aws-consumers", by_id["sns"].group)
        self.assertLess(by_id["lambda"].x, by_id["dynamo"].x)
        self.assertLess(by_id["dynamo"].x, by_id["quicksight"].x)
        self.assertLess(by_id["quicksight"].x, by_id["sns"].x)

    def test_azure_pattern_separates_primary_and_secondary_regions(self):
        diagram = Diagram(
            title="Azure Reference",
            diagram_type="cloud",
            direction="left-to-right",
            nodes=[
                Node(id="front-door", label="Azure Front Door", node_type="cdn"),
                Node(id="aks-primary", label="AKS Primary Region", node_type="kubernetes"),
                Node(id="aks-secondary", label="AKS Secondary Region", node_type="kubernetes"),
                Node(id="sql", label="Azure SQL", node_type="database"),
                Node(id="vault", label="Azure Key Vault", node_type="secret"),
                Node(id="monitor", label="Azure Monitor", node_type="monitoring"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "azure-reference")
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}

        self.assertEqual("boundary-azure-global", by_id["front-door"].group)
        self.assertEqual("boundary-azure-region-primary", by_id["aks-primary"].group)
        self.assertEqual("boundary-azure-region-secondary", by_id["aks-secondary"].group)
        self.assertEqual("boundary-azure-data", by_id["sql"].group)
        self.assertEqual("boundary-azure-identity", by_id["vault"].group)
        self.assertEqual("boundary-azure-operations", by_id["monitor"].group)
        self.assertLess(by_id["aks-primary"].x, by_id["aks-secondary"].x)

    def test_data_platform_pattern_orders_sources_ingest_process_store_serve(self):
        diagram = Diagram(
            title="Data Platform",
            diagram_type="enterprise",
            direction="left-to-right",
            nodes=[
                Node(id="crm", label="CRM Source", node_type="api"),
                Node(id="eventhub", label="Azure Event Hubs", node_type="queue"),
                Node(id="databricks", label="Databricks Notebook", node_type="process"),
                Node(id="delta", label="Delta Lake (Bronze/Silver/Gold)", node_type="database"),
                Node(id="powerbi", label="Power BI Dashboard", node_type="dashboard"),
                Node(id="purview", label="Purview Data Governance", node_type="security"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "data-platform-pipeline")
        laid_out = apply_layout(diagram)
        by_id = {node.id: node for node in laid_out.nodes}

        self.assertEqual("boundary-data-sources", by_id["crm"].group)
        self.assertEqual("boundary-data-ingest", by_id["eventhub"].group)
        self.assertEqual("boundary-data-process", by_id["databricks"].group)
        self.assertEqual("boundary-data-store", by_id["delta"].group)
        self.assertEqual("boundary-data-serve", by_id["powerbi"].group)
        self.assertEqual("boundary-data-governance", by_id["purview"].group)
        self.assertLess(by_id["crm"].x, by_id["eventhub"].x)
        self.assertLess(by_id["eventhub"].x, by_id["databricks"].x)
        self.assertLess(by_id["databricks"].x, by_id["delta"].x)
        self.assertLess(by_id["delta"].x, by_id["powerbi"].x)

    def test_enterprise_reference_pattern_leaves_existing_groups_alone(self):
        diagram = Diagram(
            title="Enterprise",
            diagram_type="enterprise",
            direction="left-to-right",
            boundaries=[
                Boundary(id="boundary-source-control", label="Source Control Zone", boundary_type="logical"),
                Boundary(id="boundary-automation-control", label="Automation Control Zone", boundary_type="logical"),
            ],
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository", group="boundary-source-control"),
                Node(id="tower", label="Ansible Tower", node_type="ansible", group="boundary-automation-control"),
            ],
        )

        apply_visual_pattern_to_diagram(diagram, "enterprise-reference")

        self.assertEqual("enterprise-reference", diagram.metadata["visual_pattern_id"])
        self.assertEqual("boundary-source-control", diagram.nodes[0].group)
        self.assertEqual({"boundary-source-control", "boundary-automation-control"}, {b.id for b in diagram.boundaries})

    def test_pattern_group_orders_cover_documented_columns(self):
        self.assertEqual(AWS_GROUP_ORDER[0], "boundary-aws-external")
        self.assertEqual(AWS_GROUP_ORDER[-1], "boundary-aws-consumers")
        self.assertEqual(AZURE_GROUP_ORDER[0], "boundary-azure-external")
        self.assertEqual(DATA_PLATFORM_GROUP_ORDER[0], "boundary-data-sources")
        self.assertEqual(DATA_PLATFORM_GROUP_ORDER[-1], "boundary-data-governance")


if __name__ == "__main__":
    unittest.main()

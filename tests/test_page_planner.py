import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drawio_generator.diagram_model import Boundary, Diagram, Edge, Node
from drawio_generator.page_planner import build_page_plan, render_page_plan


class PagePlannerTests(unittest.TestCase):
    def test_page_plan_separates_executive_path_from_detail_pages(self):
        diagram = Diagram(
            title="SHC Automation",
            diagram_type="enterprise",
            boundaries=[
                Boundary(id="boundary-source-control", label="Source Control Zone", boundary_type="logical"),
                Boundary(id="boundary-customer-infrastructure", label="Customer Infrastructure Trust Boundary", boundary_type="trust"),
            ],
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository"),
                Node(id="tower", label="Ansible Tower / AWX", node_type="ansible"),
                Node(id="roles", label="SHC Role Execution", node_type="process", metadata={"detail_level": "deep"}),
                Node(id="runtime-inputs", label="Tower Runtime Inputs", node_type="process", metadata={"detail_level": "detail"}),
                Node(id="targets", label="Customer Targets", node_type="server"),
                Node(id="health-data", label="Collected Health Data", node_type="report"),
                Node(id="reports", label="Customer Excel Workbooks", node_type="workbook"),
                Node(id="consumers", label="Report Consumers", node_type="consumer"),
                Node(id="sfs", label="Secure File Storage (SFS)", node_type="object_storage"),
                Node(id="vault", label="Delinea Secret Server", node_type="secret"),
            ],
            edges=[
                Edge(id="sync", source="repo", target="tower", label="Project sync pulls latest SHC repository", metadata={"flow_type": "control"}),
                Edge(id="collect", source="tower", target="targets", label="Collect health and security evidence", metadata={"flow_type": "target_collection"}),
                Edge(id="stage", source="targets", target="health-data", label="Stage collected health data", metadata={"flow_type": "report_evidence"}),
                Edge(id="workbook", source="health-data", target="reports", label="Generate Excel workbook", metadata={"flow_type": "report_evidence"}),
                Edge(id="consume", source="reports", target="consumers", label="Completed report for review", metadata={"flow_type": "report_evidence"}),
                Edge(id="upload", source="reports", target="sfs", label="Optional secure SFS upload path", metadata={"flow_type": "optional_storage"}),
                Edge(id="secrets", source="tower", target="vault", label="Retrieve runtime secrets", metadata={"flow_type": "security_sensitive"}),
            ],
        )

        plan = build_page_plan(diagram)
        pages = {page.title: page for page in plan.pages}

        self.assertIn("Executive Overview", pages)
        self.assertIn("Implementation Detail", pages)
        self.assertIn("Security and Trust Boundaries", pages)
        self.assertIn("Data and Evidence Flow", pages)
        self.assertIn("Operations and Follow-Up", pages)
        self.assertIn("repo", pages["Executive Overview"].node_ids)
        self.assertIn("tower", pages["Executive Overview"].node_ids)
        self.assertIn("targets", pages["Executive Overview"].node_ids)
        self.assertIn("reports", pages["Executive Overview"].node_ids)
        self.assertIn("consumers", pages["Executive Overview"].node_ids)
        self.assertNotIn("roles", pages["Executive Overview"].node_ids)
        self.assertNotIn("runtime-inputs", pages["Executive Overview"].node_ids)
        self.assertIn("roles", pages["Implementation Detail"].node_ids)
        self.assertIn("runtime-inputs", pages["Implementation Detail"].node_ids)
        self.assertIn("vault", pages["Security and Trust Boundaries"].node_ids)
        self.assertIn("secrets", pages["Security and Trust Boundaries"].edge_ids)
        self.assertIn("sfs", pages["Data and Evidence Flow"].node_ids)
        self.assertIn("upload", pages["Data and Evidence Flow"].edge_ids)
        self.assertLessEqual(len(pages["Executive Overview"].node_ids), 8)

    def test_render_page_plan_includes_quality_gates_and_security_callout(self):
        diagram = Diagram(
            title="SHC Automation",
            diagram_type="enterprise",
            nodes=[
                Node(id="repo", label="GitHub Repository", node_type="repository"),
                Node(id="tower", label="Ansible Tower / AWX", node_type="ansible"),
                Node(id="vault", label="Delinea Secret Server", node_type="secret"),
            ],
            edges=[
                Edge(id="sync", source="repo", target="tower", label="Project sync", metadata={"flow_type": "control"}),
                Edge(id="secrets", source="tower", target="vault", label="Retrieve runtime secrets", metadata={"flow_type": "security_sensitive"}),
            ],
        )

        markdown = render_page_plan(build_page_plan(diagram))

        self.assertIn("# Page Plan", markdown)
        self.assertIn("Page 1 should be understandable in about 30 seconds.", markdown)
        self.assertIn("No secrets in source control or reports", markdown)
        self.assertIn("## Executive Overview", markdown)
        self.assertIn("- Nodes: repo, tower", markdown)
        self.assertIn("## Security and Trust Boundaries", markdown)
        self.assertIn("- Edges: secrets", markdown)


if __name__ == "__main__":
    unittest.main()

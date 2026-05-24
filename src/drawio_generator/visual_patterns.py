"""Visual pattern recommendations for reference-quality architecture diagrams."""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagram_model import Diagram


@dataclass(frozen=True, slots=True)
class VisualPattern:
    pattern_id: str
    title: str
    flow: str
    palette: str
    bands: list[str] = field(default_factory=list)
    layout_rules: list[str] = field(default_factory=list)
    icon_rules: list[str] = field(default_factory=list)
    callout_rules: list[str] = field(default_factory=list)
    routing_rules: list[str] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)


def recommend_visual_pattern(diagram: Diagram, request: str = "") -> VisualPattern:
    """Recommend a visual pattern based on request text and extracted model terms."""

    text = _combined_text(diagram, request)
    if _contains_any(text, ["presentation", "slide", "branded", "protocol", "immutable", "blockchain", "proof"]):
        return _presentation_architecture()
    if _contains_any(text, ["databricks", "delta lake", "fabric", "power bi", "lakehouse", "bronze", "silver", "gold"]):
        return _data_platform_pipeline()
    if _contains_any(text, ["aws", "amazon ", "lambda", "dynamodb", "s3", "kinesis", "redshift", "appsync"]):
        return _aws_reference()
    if _contains_any(text, ["azure", "traffic manager", "sql server", "active directory", "bastion", "aks"]):
        return _azure_reference()
    return _enterprise_reference()


def render_visual_guide(pattern: VisualPattern) -> str:
    lines = [
        "# Visual Guide",
        "",
        f"- Pattern: {pattern.title}",
        f"- Flow: {pattern.flow}",
        f"- Palette: {pattern.palette}",
        "",
        "## Bands",
        *_render_items(pattern.bands),
        "",
        "## Layout Rules",
        *_render_items(pattern.layout_rules),
        "",
        "## Icon Rules",
        *_render_items(pattern.icon_rules),
        "",
        "## Callout Rules",
        *_render_items(pattern.callout_rules),
        "",
        "## Routing Rules",
        *_render_items(pattern.routing_rules),
        "",
        "## Quality Gates",
        *_render_items(pattern.quality_gates),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _azure_reference() -> VisualPattern:
    return VisualPattern(
        pattern_id="azure-reference",
        title="Azure Reference Architecture",
        flow="Internet -> global routing -> regional tiers -> data services -> replication/supporting services",
        palette="Azure blue with light gray tier bands, pale yellow data zones, dark text, and sparse accent colors",
        bands=[
            "Primary/secondary region containers",
            "Web, business, data, identity, bastion, and operations tiers",
            "Dashed network, subnet, and peering boundaries",
        ],
        layout_rules=[
            "Use region containers first, then tier columns inside each region.",
            "Mirror primary and secondary regions vertically when HA/DR is in scope.",
            "Keep global services outside region boundaries unless they are region-scoped.",
        ],
        icon_rules=[
            "Use Azure service icon-like shapes or safe blue Azure-style fallbacks.",
            "Use database cylinders for SQL, document/workbook shapes for reports, and server tiles for VM tiers.",
        ],
        callout_rules=[
            "Use compact numbered blue callouts for cross-region, routing, and replication flows.",
        ],
        routing_rules=[
            "Prefer orthogonal left-to-right ingress and vertical replication paths.",
            "Avoid routing arrows through region/tier labels.",
        ],
        quality_gates=[
            "Primary/secondary scope is obvious at a glance.",
            "Each tier has a clear owner label and no overloaded text blocks.",
        ],
    )


def _aws_reference() -> VisualPattern:
    return VisualPattern(
        pattern_id="aws-reference",
        title="AWS Reference Architecture",
        flow="Edge/on-premises -> AWS account/VPC -> streaming/data lake -> microservices -> analytics/notifications",
        palette="AWS orange accents with service-category colors, dashed domain boxes, and white canvas",
        bands=[
            "External or edge environment",
            "AWS account, VPC, data lake, data governance, processing, AI/ML, analytics, and notifications",
        ],
        layout_rules=[
            "Use large dashed domain containers with clear AWS service group labels.",
            "Place data stores centrally and analytics/notification consumers to the right.",
        ],
        icon_rules=[
            "Use AWS service icon-like colored fallbacks and category-consistent shapes.",
        ],
        callout_rules=[
            "Use numbered blue callout badges for review steps and architectural hotspots.",
        ],
        routing_rules=[
            "Use orthogonal service-to-service arrows; keep event/data flows visually separate from control flows.",
        ],
        quality_gates=[
            "AWS account/VPC boundary is explicit.",
            "Data lake, governance, processing, and analytics domains are separated.",
        ],
    )


def _data_platform_pipeline() -> VisualPattern:
    return VisualPattern(
        pattern_id="data-platform-pipeline",
        title="Data Platform Pipeline",
        flow="Sources -> Process -> Store -> Serve",
        palette="Microsoft/Azure light canvas with green numbered callouts, light gray swimlanes, and data-tier gold accents",
        bands=[
            "Sources",
            "Process",
            "Store",
            "Serve",
            "Discover and govern",
            "Platform",
        ],
        layout_rules=[
            "Use vertical swimlanes for Sources, Process, and Serve, with Store spanning the lower middle.",
            "Place governance and platform services as supporting horizontal bands below the main flow.",
        ],
        icon_rules=[
            "Use queue, data lake, notebook/process, warehouse, dashboard, identity, key, and monitor shapes.",
        ],
        callout_rules=[
            "Use numbered green callouts to mark ordered ingestion, processing, governance, and serving steps.",
        ],
        routing_rules=[
            "Keep source ingestion arrows left-to-right and data-tier movement horizontal or vertical, not diagonal.",
        ],
        quality_gates=[
            "Bronze/silver/gold or equivalent data states are visible when present.",
            "Governance and platform services do not obscure the main data path.",
        ],
    )


def _presentation_architecture() -> VisualPattern:
    return VisualPattern(
        pattern_id="presentation-architecture",
        title="Presentation Architecture",
        flow="Core subject -> agent/control plane -> validation/evidence services -> consumers or ecosystem",
        palette="Dark presentation canvas with high-contrast accent color, large type, and sparse supporting text",
        bands=[
            "Hero title",
            "Primary architecture path",
            "Supporting services",
            "Consumer or ecosystem row",
        ],
        layout_rules=[
            "Use a large central subject and two to four major blocks with generous spacing.",
            "Put secondary inputs and audiences around the main architecture path.",
        ],
        icon_rules=[
            "Use simple line icons or safe built-in device/server/user shapes; avoid dense cloud-service icon grids.",
        ],
        callout_rules=[
            "Use accent-color labels sparingly; do not put a callout on every arrow.",
        ],
        routing_rules=[
            "Use clean horizontal/vertical connections and avoid visual clutter around the central subject.",
        ],
        quality_gates=[
            "The title and primary architecture claim are legible at slide distance.",
            "No block has more than four short lines of text.",
        ],
    )


def _enterprise_reference() -> VisualPattern:
    return VisualPattern(
        pattern_id="enterprise-reference",
        title="Enterprise Reference Architecture",
        flow="Sources -> control plane -> target systems -> data/evidence -> reports/storage -> consumers",
        palette="Light enterprise canvas with blue control, green collection, amber evidence, gray optional, red sensitive paths",
        bands=[
            "Source/control",
            "Automation/control plane",
            "Customer or target environment",
            "Data/evidence",
            "Consumers and optional storage",
        ],
        layout_rules=[
            "Use left-to-right swimlanes and keep Page 1 to the main review path.",
            "Move role internals, variables, and inventories to detail pages.",
        ],
        icon_rules=[
            "Use icon-like built-in shapes for repositories, controllers, servers, data objects, reports, vaults, and consumers.",
        ],
        callout_rules=[
            "Use numbered callouts for busy flows and put full descriptions in the legend.",
        ],
        routing_rules=[
            "Use orthogonal arrows and separate optional/security paths visually.",
        ],
        quality_gates=[
            "Page 1 is readable in about 30 seconds.",
            "Trust boundaries and sensitive flows are visible.",
        ],
    )


def _combined_text(diagram: Diagram, request: str) -> str:
    parts = [
        request,
        diagram.title,
        diagram.subtitle,
        diagram.diagram_type,
        *[node.label for node in diagram.nodes],
        *[node.node_type for node in diagram.nodes],
        *[edge.label for edge in diagram.edges],
    ]
    return " ".join(parts).lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _render_items(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]

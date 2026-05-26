"""Draw.io style registry with safe fallbacks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from . import builtin_vendor_shapes
from .icon_packs import IconPack, discover_icon_packs


BASE_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;arcSize=8;fontColor=#212529;fontSize=13;"
)

DEFAULT_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;arcSize=8;"
    "fillColor=#f8f9fa;strokeColor=#6c757d;fontColor=#212529;fontSize=13;"
)


@dataclass(frozen=True, slots=True)
class IconStyle:
    category: str
    drawio_style: str
    fallback_label: str
    vendor: str | None = None
    official: bool = False
    license_notice: str = "diagrams.net built-in fallback shape; no official vendor icon embedded"


STYLE_REGISTRY: dict[str, IconStyle] = {
    "actor": IconStyle("general", "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#212529;fontSize=13;", "Actor"),
    "user": IconStyle("general", "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#212529;fontSize=13;", "User"),
    "frontend": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Frontend"),
    "api": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "API"),
    "backend": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Backend"),
    "worker": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Worker"),
    "process": IconStyle("workflow", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Process"),
    "deployment": IconStyle("workflow", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Deployment"),
    "repository": IconStyle("devops", "shape=folder;tabWidth=40;tabHeight=14;tabPosition=left;html=1;whiteSpace=wrap;fillColor=#e1d5e7;strokeColor=#9673a6;fontColor=#212529;fontSize=13;", "Repository"),
    "artifact": IconStyle("devops", "shape=package;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontColor=#212529;fontSize=13;", "Artifact"),
    "workbook": IconStyle("data", "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;size=16;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#212529;fontSize=13;", "Workbook"),
    "report": IconStyle("data", "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#212529;fontSize=13;", "Report"),
    "database": IconStyle("data", "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#212529;fontSize=13;", "Database"),
    "cache": IconStyle("data", "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#ffe6cc;strokeColor=#d79b00;fontColor=#212529;fontSize=13;", "Cache"),
    "queue": IconStyle("data", "shape=mxgraph.basic.queue;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#212529;fontSize=13;", "Queue"),
    "object_storage": IconStyle("data", "shape=cloud;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#6c757d;fontColor=#212529;fontSize=13;", "Object Storage"),
    "cloud": IconStyle("cloud", "ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontColor=#212529;fontSize=13;", "Cloud"),
    "cdn": IconStyle("network", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "CDN"),
    "gateway": IconStyle("network", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Gateway"),
    "waf": IconStyle("security", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "WAF"),
    "firewall": IconStyle("security", BASE_STYLE + "fillColor=#f8cecc;strokeColor=#b85450;", "Firewall"),
    "identity": IconStyle("security", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Identity"),
    "secret": IconStyle("security", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Secret Store"),
    "security": IconStyle("security", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Security"),
    "kubernetes": IconStyle("platform", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Kubernetes"),
    "container": IconStyle("platform", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Container"),
    "server": IconStyle("infrastructure", BASE_STYLE + "fillColor=#f5f5f5;strokeColor=#666666;", "Server"),
    "linux_server": IconStyle("infrastructure", "shape=mxgraph.cisco19.rect;prIcon=server;html=1;whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#212529;fontSize=13;", "Linux Server"),
    "windows_server": IconStyle("infrastructure", "shape=mxgraph.cisco19.rect;prIcon=server;html=1;whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#212529;fontSize=13;", "Windows Server"),
    "network": IconStyle("network", BASE_STYLE + "fillColor=#f5f5f5;strokeColor=#666666;", "Network"),
    "monitoring": IconStyle("operations", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Monitoring"),
    "logging": IconStyle("operations", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Logging"),
    "dashboard": IconStyle("operations", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Dashboard"),
    "terraform": IconStyle("devops", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Terraform"),
    "ansible": IconStyle("devops", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Ansible"),
    "consumer": IconStyle("general", BASE_STYLE + "fillColor=#fff2cc;strokeColor=#d6b656;", "Consumer"),
}


ALIASES: dict[str, str] = {
    "aks": "kubernetes",
    "azure kubernetes service": "kubernetes",
    "azure app service": "backend",
    "azure functions": "process",
    "azure front door": "cdn",
    "azure application gateway": "gateway",
    "application gateway": "gateway",
    "azure traffic manager": "cdn",
    "azure key vault": "secret",
    "key vault": "secret",
    "azure database for postgresql": "database",
    "azure sql database": "database",
    "azure sql": "database",
    "azure monitor": "monitoring",
    "log analytics": "logging",
    "aws lambda": "process",
    "amazon lambda": "process",
    "amazon s3": "object_storage",
    "aws s3": "object_storage",
    "amazon dynamodb": "database",
    "aws dynamodb": "database",
    "amazon rds": "database",
    "aws rds": "database",
    "amazon cloudfront": "cdn",
    "aws cloudfront": "cdn",
    "aws waf": "waf",
    "aws iam": "identity",
    "amazon api gateway": "gateway",
    "aws api gateway": "gateway",
    "postgresql": "database",
    "delinea secret server": "secret",
    "github repository": "repository",
    "github actions": "process",
    "gitlab ci": "process",
    "jenkins": "process",
    "prometheus": "monitoring",
    "grafana": "dashboard",
    "log analytics": "logging",
    "opentelemetry collector": "monitoring",
    "application gateway": "gateway",
    "azure front door": "cdn",
    "excel": "workbook",
    "excel workbook": "workbook",
    "workbook": "workbook",
    "sfs": "object_storage",
    "object storage": "object_storage",
    "linux": "linux_server",
    "windows": "windows_server",
    "report consumers": "consumer",
}

VENDOR_TERMS: dict[str, tuple[str, ...]] = {
    "azure": (
        "azure",
        "aks",
        "key vault",
        "front door",
        "traffic manager",
        "application gateway",
        "entra",
        "cosmos db",
        "service bus",
        "event hubs",
        "event grid",
        "log analytics",
        "application insights",
        "sentinel",
        "defender for cloud",
    ),
    "aws": (
        "aws",
        "amazon",
        "cloudfront",
        "dynamodb",
        "lambda",
        "s3",
        "route 53",
        "eks",
        "ecs",
        "fargate",
        "sqs",
        "sns",
        "eventbridge",
        "cloudwatch",
        "guardduty",
    ),
    "gcp": (
        "google cloud",
        "gcp",
        "gke",
        "bigquery",
        "vertex ai",
        "cloud run",
        "cloud functions",
        "cloud storage",
        "pub/sub",
        "pub sub",
        "cloud spanner",
        "firestore",
    ),
    "kubernetes": (
        "kubernetes pod",
        "k8s pod",
        "kubernetes deployment",
        "kubernetes service",
        "kubernetes ingress",
        "kubernetes configmap",
        "kubernetes secret",
        "kubernetes namespace",
        "kubernetes pv",
        "kubernetes pvc",
        "kubernetes statefulset",
        "kubernetes daemonset",
        "kubernetes job",
        "kubernetes cronjob",
        "kubernetes node",
    ),
}


def _vendor_for(label: str) -> str | None:
    lowered = label.lower()
    # Exact match against any built-in vendor shape map is the strongest
    # signal -- service names like "Google Kubernetes Engine" do not share an
    # obvious vendor token with the substring-based fallback below.
    for vendor in ("azure", "aws", "gcp", "kubernetes"):
        if builtin_vendor_shapes.lookup(vendor, lowered) is not None:
            return vendor
    for vendor, terms in VENDOR_TERMS.items():
        if any(term in lowered for term in terms):
            return vendor
    return None


def _with_vendor(style: IconStyle, vendor: str | None) -> IconStyle:
    if vendor is None:
        return style
    return replace(
        style,
        vendor=vendor,
        official=False,
        license_notice=f"{vendor.upper()} diagrams.net built-in fallback shape; no official vendor icon embedded",
    )


_PACK_CACHE: dict[str, IconPack] | None = None


def _packs() -> dict[str, IconPack]:
    global _PACK_CACHE
    if _PACK_CACHE is None:
        _PACK_CACHE = discover_icon_packs()
    return _PACK_CACHE


def refresh_icon_packs(extra_roots: Iterable[Path] | None = None) -> dict[str, IconPack]:
    """Force a rediscovery of local vendor icon packs. Returns the active packs."""

    global _PACK_CACHE
    _PACK_CACHE = discover_icon_packs(extra_roots)
    return _PACK_CACHE


def _official_for(label: str, vendor: str | None) -> IconStyle | None:
    if vendor is None:
        return None
    pack = _packs().get(vendor)
    if pack is None:
        return None
    style = pack.lookup(label)
    if not style:
        return None
    return IconStyle(
        category=f"{vendor}-official",
        drawio_style=style,
        fallback_label=label.strip().title() or vendor.title(),
        vendor=vendor,
        official=True,
        license_notice=pack.license_notice,
    )


def _builtin_vendor_style(label: str, vendor: str | None) -> IconStyle | None:
    """Resolve a label to a diagrams.net built-in vendor stencil.

    Built-in vendor shapes (``mxgraph.azure.*``, ``mxgraph.aws4.*``,
    ``mxgraph.gcp2.*``, ``mxgraph.kubernetes.*``) ship with diagrams.net and
    are free to use in any ``.drawio`` file. They are used by default for
    recognized vendor service names so the helper produces real vendor icons
    instead of generic colored rectangles. A licensed third-party icon pack
    still takes precedence when one is configured.
    """

    if vendor is None:
        return None
    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in (label, ALIASES.get(label)):
        if not candidate:
            continue
        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)
    for candidate in candidates:
        match = builtin_vendor_shapes.lookup(vendor, candidate)
        if match is None:
            continue
        return IconStyle(
            category=match.category,
            drawio_style=match.drawio_style,
            fallback_label=match.label,
            vendor=match.vendor,
            official=False,
            license_notice=(
                f"diagrams.net built-in {vendor} stencil "
                f"(no proprietary icon pack required)"
            ),
        )
    return None


def get_icon_style(
    node_type: str | None,
    icon: str | None = None,
    label: str | None = None,
) -> IconStyle:
    """Return the closest available draw.io style for a node.

    Resolution order, tried for each non-empty candidate in ``(icon, label,
    node_type)``:

    1. Locally licensed vendor icon pack (manifest in ``stencils/<vendor>/``).
    2. Built-in diagrams.net vendor stencils (``mxgraph.azure``, ``aws4``,
       ``gcp2``, ``kubernetes``) for recognized service names.
    3. Generic registry entry via vendor-aware alias.
    4. Vendor-tagged generic fallback (rounded rectangle).

    ``label`` is tried between ``icon`` and ``node_type`` so a specific service
    name like "Azure Kubernetes Service" wins over a generic
    ``node_type="kubernetes"`` that would otherwise downgrade the node to a
    plain generic shape.
    """

    fallback_vendor: str | None = None
    for candidate in (icon, label, node_type):
        if not candidate:
            continue
        raw_key = candidate.strip().lower()
        vendor = _vendor_for(raw_key)
        fallback_vendor = fallback_vendor or vendor
        official = _official_for(raw_key, vendor)
        if official is not None:
            return official
        key = ALIASES.get(raw_key, raw_key)
        official_alias = _official_for(key, vendor)
        if official_alias is not None:
            return official_alias
        builtin = _builtin_vendor_style(raw_key, vendor)
        if builtin is not None:
            return builtin
        if key in STYLE_REGISTRY:
            return _with_vendor(STYLE_REGISTRY[key], vendor)
    if fallback_vendor:
        return _with_vendor(IconStyle("fallback", DEFAULT_STYLE, "Component"), fallback_vendor)
    return IconStyle("fallback", DEFAULT_STYLE, "Component")


def supported_categories() -> dict[str, list[str]]:
    """Return registry entries grouped by broad category for documentation."""

    grouped: dict[str, list[str]] = {}
    for key, style in STYLE_REGISTRY.items():
        grouped.setdefault(style.category, []).append(key)
    return {category: sorted(names) for category, names in sorted(grouped.items())}

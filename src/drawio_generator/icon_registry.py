"""Draw.io style registry with safe fallbacks."""

from __future__ import annotations

from dataclasses import dataclass


BASE_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;arcSize=8;fontColor=#212529;"
)

DEFAULT_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;arcSize=8;"
    "fillColor=#f8f9fa;strokeColor=#6c757d;fontColor=#212529;"
)


@dataclass(frozen=True, slots=True)
class IconStyle:
    category: str
    drawio_style: str
    fallback_label: str


STYLE_REGISTRY: dict[str, IconStyle] = {
    "actor": IconStyle("general", "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#fff2cc;strokeColor=#d6b656;", "Actor"),
    "user": IconStyle("general", "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#fff2cc;strokeColor=#d6b656;", "User"),
    "frontend": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Frontend"),
    "api": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "API"),
    "backend": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Backend"),
    "worker": IconStyle("application", BASE_STYLE + "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Worker"),
    "process": IconStyle("workflow", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Process"),
    "deployment": IconStyle("workflow", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Deployment"),
    "repository": IconStyle("devops", "shape=folder;tabWidth=40;tabHeight=14;tabPosition=left;html=1;whiteSpace=wrap;fillColor=#e1d5e7;strokeColor=#9673a6;", "Repository"),
    "artifact": IconStyle("devops", "shape=package;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;", "Artifact"),
    "database": IconStyle("data", "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#fff2cc;strokeColor=#d6b656;", "Database"),
    "cache": IconStyle("data", "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#ffe6cc;strokeColor=#d79b00;", "Cache"),
    "queue": IconStyle("data", "shape=mxgraph.basic.queue;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;", "Queue"),
    "cloud": IconStyle("cloud", "ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;", "Cloud"),
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
    "network": IconStyle("network", BASE_STYLE + "fillColor=#f5f5f5;strokeColor=#666666;", "Network"),
    "monitoring": IconStyle("operations", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Monitoring"),
    "logging": IconStyle("operations", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Logging"),
    "dashboard": IconStyle("operations", BASE_STYLE + "fillColor=#d5e8d4;strokeColor=#82b366;", "Dashboard"),
    "terraform": IconStyle("devops", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Terraform"),
    "ansible": IconStyle("devops", BASE_STYLE + "fillColor=#e1d5e7;strokeColor=#9673a6;", "Ansible"),
}


ALIASES: dict[str, str] = {
    "aks": "kubernetes",
    "azure kubernetes service": "kubernetes",
    "postgresql": "database",
    "azure database for postgresql": "database",
    "key vault": "secret",
    "azure key vault": "secret",
    "github actions": "process",
    "gitlab ci": "process",
    "jenkins": "process",
    "prometheus": "monitoring",
    "grafana": "dashboard",
    "log analytics": "logging",
    "opentelemetry collector": "monitoring",
    "application gateway": "gateway",
    "azure front door": "cdn",
}


def get_icon_style(node_type: str | None, icon: str | None = None) -> IconStyle:
    """Return the closest available draw.io style for a node."""

    for candidate in (icon, node_type):
        if not candidate:
            continue
        key = candidate.strip().lower()
        key = ALIASES.get(key, key)
        if key in STYLE_REGISTRY:
            return STYLE_REGISTRY[key]
    return IconStyle("fallback", DEFAULT_STYLE, "Component")


def supported_categories() -> dict[str, list[str]]:
    """Return registry entries grouped by broad category for documentation."""

    grouped: dict[str, list[str]] = {}
    for key, style in STYLE_REGISTRY.items():
        grouped.setdefault(style.category, []).append(key)
    return {category: sorted(names) for category, names in sorted(grouped.items())}

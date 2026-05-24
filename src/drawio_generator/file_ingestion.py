"""Best-effort extraction from architecture, infrastructure, and source files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .diagram_model import Edge, Node
from .validators import redact_sensitive_text


@dataclass(slots=True)
class ExtractionResult:
    components: list[Node] = field(default_factory=list)
    relationships: list[Edge] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def extend(self, other: "ExtractionResult") -> None:
        for component in other.components:
            if _is_generic_duplicate(component.label, [existing.label for existing in self.components]):
                continue
            self.components = [
                existing
                for existing in self.components
                if not _is_more_specific(component.label, existing.label)
            ]
            existing_ids = {existing.id for existing in self.components}
            if component.id not in existing_ids:
                self.components.append(component)
        existing_edges = {edge.id for edge in self.relationships}
        for edge in other.relationships:
            if edge.id not in existing_edges:
                self.relationships.append(edge)
                existing_edges.add(edge.id)
        self.assumptions.extend(item for item in other.assumptions if item not in self.assumptions)
        self.unknowns.extend(item for item in other.unknowns if item not in self.unknowns)
        self.sources.extend(item for item in other.sources if item not in self.sources)


KNOWN_COMPONENTS: list[tuple[str, str, str]] = [
    ("GitHub Repository", "github repository", "repository"),
    ("Source Control Repository", "source control repository", "repository"),
    ("Azure Front Door", "azure front door", "cdn"),
    ("Application Gateway WAF", "application gateway waf", "waf"),
    ("Application Gateway", "application gateway", "gateway"),
    ("AKS", "aks", "kubernetes"),
    ("Azure Kubernetes Service", "azure kubernetes service", "kubernetes"),
    ("Key Vault", "key vault", "secret"),
    ("Azure Database for PostgreSQL", "azure database for postgresql", "database"),
    ("PostgreSQL", "postgresql", "database"),
    ("GitHub Actions", "github actions", "process"),
    ("GitLab CI", "gitlab ci", "process"),
    ("Jenkins", "jenkins", "process"),
    ("Terraform", "terraform", "terraform"),
    ("Ansible", "ansible", "ansible"),
    ("Prometheus", "prometheus", "monitoring"),
    ("Grafana", "grafana", "dashboard"),
    ("Log Analytics", "log analytics", "logging"),
    ("OpenTelemetry Collector", "opentelemetry collector", "monitoring"),
    ("RabbitMQ", "rabbitmq", "queue"),
    ("Linux Server", "linux server", "linux_server"),
    ("Linux Server", "linux servers", "linux_server"),
    ("Windows Server", "windows server", "windows_server"),
    ("Windows Server", "windows servers", "windows_server"),
    ("IIS", "iis", "server"),
    ("PgBouncer", "pgbouncer", "server"),
    ("Zabbix", "zabbix", "monitoring"),
    ("Kafka", "kafka", "queue"),
    ("Redis", "redis", "cache"),
    ("Docker", "docker", "container"),
    ("Helm", "helm", "deployment"),
    ("ArgoCD", "argocd", "deployment"),
    ("Flux", "flux", "deployment"),
    ("Delinea Secret Server", "delinea secret server", "secret"),
    ("Ansible Tower", "ansible tower", "ansible"),
    ("AWX", "awx", "ansible"),
    ("Tower Runtime Inputs", "tower runtime inputs", "process"),
    ("SHC Role Execution", "shc role execution", "process"),
    ("Controller Runtime Workspace", "controller runtime workspace", "process"),
    ("Collected Health Data", "collected health data", "report"),
    ("Report Generation", "report generation", "report"),
    ("Customer Excel Workbooks", "customer excel workbooks", "workbook"),
    ("Excel Workbook", "excel workbook", "workbook"),
    ("Report Consumers", "report consumers", "consumer"),
    ("Secure File Storage (SFS)", "secure file storage", "object_storage"),
    ("Secure File Storage (SFS)", "sfs", "object_storage"),
    ("Object Storage", "object storage", "object_storage"),
]


def extract_components_from_file(path: Path) -> ExtractionResult:
    """Read a file as text and extract diagram components."""

    text = path.read_text(encoding="utf-8", errors="replace")
    return extract_components_from_text(str(path), text)


def extract_components_from_text(source_name: str, text: str) -> ExtractionResult:
    """Extract components and high-signal relationships from text."""

    redacted = redact_sensitive_text(text)
    result = ExtractionResult(sources=[source_name])
    _extract_known_components(redacted, result)
    _extract_json_components(source_name, redacted, result)
    _extract_kubernetes_components(redacted, result)
    _extract_terraform_components(redacted, result)
    _extract_github_actions_components(redacted, result)
    _extract_opentelemetry_components(redacted, result)
    _extract_source_code_hints(source_name, redacted, result)
    _extract_relationship_hints(redacted, result)

    if not result.components:
        result.unknowns.append(f"No high-confidence components extracted from {source_name}; manual review may be needed.")
    return result


def load_inputs(input_files: list[str] | None, input_dir: str | None) -> ExtractionResult:
    """Load all requested files and directories."""

    aggregate = ExtractionResult()
    paths: list[Path] = []
    if input_files:
        paths.extend(Path(item) for item in input_files)
    if input_dir:
        root = Path(input_dir)
        paths.extend(path for path in root.rglob("*") if path.is_file() and _is_supported_text_file(path))

    for path in paths:
        if not path.exists():
            aggregate.unknowns.append(f"Input path does not exist: {path}")
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and _is_supported_text_file(child):
                    aggregate.extend(extract_components_from_file(child))
            continue
        if _is_supported_text_file(path):
            aggregate.extend(extract_components_from_file(path))
        else:
            aggregate.unknowns.append(f"Skipped unsupported binary or unknown file type: {path}")
    return aggregate


def _extract_known_components(text: str, result: ExtractionResult) -> None:
    lowered = text.lower()
    tower_awx_combined = "ansible tower" in lowered and "awx" in lowered
    if tower_awx_combined:
        _add_component(result, "Ansible Tower / AWX", "ansible")
    for label, needle, node_type in KNOWN_COMPONENTS:
        if tower_awx_combined and label in {"Ansible Tower", "AWX"}:
            continue
        if needle in lowered:
            _add_component(result, label, node_type)


def _extract_json_components(source_name: str, text: str, result: ExtractionResult) -> None:
    if not source_name.lower().endswith((".json", ".swagger", ".openapi")):
        return
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        result.unknowns.append(f"JSON-like file could not be parsed: {source_name}")
        return
    if isinstance(payload, dict):
        if "openapi" in payload or "swagger" in payload:
            title = payload.get("info", {}).get("title", "OpenAPI Service")
            _add_component(result, str(title), "api")
            for path in payload.get("paths", {}):
                _add_component(result, f"Endpoint {path}", "api")
        if "panels" in payload or "dashboard" in payload:
            _add_component(result, "Grafana Dashboard", "dashboard")


def _extract_kubernetes_components(text: str, result: ExtractionResult) -> None:
    pattern = re.compile(
        r"(?ims)^\s*kind:\s*(?P<kind>[A-Za-z0-9]+)\s*$.*?^\s*metadata:\s*$.*?^\s+name:\s*(?P<name>[A-Za-z0-9_.-]+)\s*$"
    )
    for match in pattern.finditer(text):
        kind = match.group("kind")
        name = match.group("name")
        node_type = "kubernetes" if kind.lower() in {"deployment", "service", "pod", "ingress"} else "component"
        _add_component(result, f"{kind}/{name}", node_type)


def _extract_terraform_components(text: str, result: ExtractionResult) -> None:
    for resource_type, name in re.findall(r'resource\s+"([^"]+)"\s+"([^"]+)"', text):
        _add_component(result, f"Terraform {resource_type}.{name}", _terraform_node_type(resource_type))


def _extract_github_actions_components(text: str, result: ExtractionResult) -> None:
    if "jobs:" not in text or "steps:" not in text:
        return
    for match in re.finditer(r"(?m)^\s+([A-Za-z0-9_-]+):\s*$\n\s+steps:", text):
        _add_component(result, f"GitHub Actions job: {match.group(1)}", "process")


def _extract_opentelemetry_components(text: str, result: ExtractionResult) -> None:
    current_section: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {"receivers:", "processors:", "exporters:"}:
            current_section = stripped.rstrip(":")
            continue
        if current_section and line.startswith("  ") and stripped.endswith(":"):
            name = stripped.rstrip(":")
            _add_component(result, f"OpenTelemetry {current_section[:-1]}: {name}", "monitoring")
        elif stripped and not line.startswith(" "):
            current_section = None


def _extract_source_code_hints(source_name: str, text: str, result: ExtractionResult) -> None:
    suffix = Path(source_name).suffix.lower()
    if suffix not in {".py", ".js", ".ts", ".java", ".cs", ".go", ".ps1", ".sh", ".sql"}:
        return
    if re.search(r"\b(def|function|func|class)\b", text):
        _add_component(result, f"Code module {Path(source_name).name}", "backend")
    if re.search(r"\b(GET|POST|PUT|DELETE|router|Controller|Handler)\b", text):
        _add_component(result, f"API entry point {Path(source_name).name}", "api")
    if re.search(r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b", text, re.IGNORECASE):
        _add_component(result, f"Database access {Path(source_name).name}", "database")


def _extract_relationship_hints(text: str, result: ExtractionResult) -> None:
    labels_by_lower = {component.label.lower(): component for component in result.components}
    verbs = r"(calls|sends|forwards|routes|writes|reads|retrieves|exports|runs|provisions|deploys|stores)"
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence_lower = sentence.lower()
        present = {
            label: component
            for label, component in labels_by_lower.items()
            if label in sentence_lower
        }
        for source_label, source_component in present.items():
            for target_label, target_component in present.items():
                if source_label == target_label:
                    continue
                pattern = re.escape(source_label) + rf".{{0,100}}\b{verbs}\b.{{0,100}}" + re.escape(target_label)
                if re.search(pattern, sentence_lower, re.DOTALL):
                    edge_id = f"edge-{source_component.id}-{target_component.id}"
                    if not any(edge.id == edge_id for edge in result.relationships):
                        result.relationships.append(Edge(id=edge_id, source=source_component.id, target=target_component.id, label="documented flow"))


def _add_component(result: ExtractionResult, label: str, node_type: str) -> None:
    component_id = _slug(label)
    existing_labels = [component.label for component in result.components]
    if _is_generic_duplicate(label, existing_labels):
        return
    result.components = [
        component
        for component in result.components
        if not _is_more_specific(label, component.label)
    ]
    if any(component.id == component_id for component in result.components):
        return
    result.components.append(Node(id=component_id, label=label, node_type=node_type))


def _is_generic_duplicate(candidate_label: str, existing_labels: list[str]) -> bool:
    lowered = candidate_label.lower()
    return any(lowered in existing.lower() and lowered != existing.lower() for existing in existing_labels)


def _is_more_specific(candidate_label: str, existing_label: str) -> bool:
    candidate = candidate_label.lower()
    existing = existing_label.lower()
    return existing in candidate and existing != candidate


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "component"


def _terraform_node_type(resource_type: str) -> str:
    lowered = resource_type.lower()
    if "key_vault" in lowered or "secret" in lowered:
        return "secret"
    if "postgres" in lowered or "sql" in lowered or "database" in lowered:
        return "database"
    if "kubernetes" in lowered or "aks" in lowered:
        return "kubernetes"
    if "gateway" in lowered or "frontdoor" in lowered:
        return "gateway"
    return "terraform"


def _is_supported_text_file(path: Path) -> bool:
    return path.suffix.lower() in {
        ".md",
        ".txt",
        ".csv",
        ".json",
        ".yaml",
        ".yml",
        ".xml",
        ".drawio",
        ".puml",
        ".plantuml",
        ".mmd",
        ".tf",
        ".tfvars",
        ".hcl",
        ".dockerfile",
        ".compose",
        ".py",
        ".js",
        ".ts",
        ".java",
        ".cs",
        ".go",
        ".ps1",
        ".sh",
        ".sql",
        ".conf",
        ".config",
    } or path.name.lower() in {"dockerfile", "jenkinsfile"}

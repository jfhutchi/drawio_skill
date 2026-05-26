"""Best-effort extraction from architecture, infrastructure, and source files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import builtin_vendor_shapes
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


# Hand-curated non-vendor enterprise components. Vendor cloud services are
# auto-derived from builtin_vendor_shapes (see below) so this list stays focused
# on tools, identity systems, on-prem servers, and report/data artifacts that
# don't have a dedicated vendor stencil.
_CORE_KNOWN_COMPONENTS: list[tuple[str, str, str]] = [
    ("GitHub Repository", "github repository", "repository"),
    ("Source Control Repository", "source control repository", "repository"),
    # Composite vendor labels that need to win over the simpler vendor names.
    ("Application Gateway WAF", "application gateway waf", "waf"),
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


def _build_known_components() -> list[tuple[str, str, str]]:
    """Combine hand-curated core components with auto-derived vendor entries.

    The vendor entries come from ``builtin_vendor_shapes.iter_extractor_entries``,
    so every shape the icon resolver knows about is also extractable from
    input prose. Hand-curated entries appear first and win on the slug-dedup
    in ``_add_component``.
    """

    seen_needles: set[str] = {needle for _, needle, _ in _CORE_KNOWN_COMPONENTS}
    combined = list(_CORE_KNOWN_COMPONENTS)
    for entry in builtin_vendor_shapes.iter_extractor_entries():
        if entry.needle in seen_needles:
            continue
        seen_needles.add(entry.needle)
        combined.append((entry.label, entry.needle, entry.node_type))
    return combined


KNOWN_COMPONENTS: list[tuple[str, str, str]] = _build_known_components()


def extract_components_from_file(path: Path) -> ExtractionResult:
    """Read a file as text and extract diagram components."""

    text = path.read_text(encoding="utf-8", errors="replace")
    return extract_components_from_text(str(path), text)


def extract_components_from_text(source_name: str, text: str) -> ExtractionResult:
    """Extract components and high-signal relationships from text."""

    redacted = redact_sensitive_text(text)
    result = ExtractionResult(sources=[source_name])
    _extract_known_components(redacted, result)
    _fuzzy_extract(redacted, result)
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


# Fuzzy patterns for variant phrasings that don't appear verbatim in
# KNOWN_COMPONENTS. Each entry maps a regex (compiled at module load) to the
# canonical needle it represents; we then look up the canonical needle in
# KNOWN_COMPONENTS to get a label and node_type. This keeps the fuzzy layer
# tied to the single source of truth (builtin_vendor_shapes) rather than
# duplicating service metadata.
_FUZZY_PATTERN_SOURCES: list[tuple[str, str]] = [
    # AWS variants
    (r"\b(?:aws\s+)?lambdas?(?:\s+functions?)?\b", "aws lambda"),
    (r"\b(?:amazon\s+|aws\s+)?s3\s+buckets?\b", "amazon s3"),
    (r"\b(?:amazon\s+|aws\s+)?ec2\s+(?:instances?|hosts?|nodes?)\b", "amazon ec2"),
    (r"\b(?:amazon\s+|aws\s+)?eks\s+clusters?\b", "amazon eks"),
    (r"\b(?:amazon\s+|aws\s+)?ecs\s+(?:clusters?|services?|tasks?)\b", "amazon ecs"),
    (r"\bfargate\s+(?:tasks?|services?)\b", "aws fargate"),
    (r"\b(?:amazon\s+|aws\s+)?dynamodb\s+tables?\b", "amazon dynamodb"),
    (r"\b(?:amazon\s+|aws\s+)?rds\s+(?:instances?|databases?)\b", "amazon rds"),
    (r"\b(?:amazon\s+|aws\s+)?sqs\s+queues?\b", "amazon sqs"),
    (r"\b(?:amazon\s+|aws\s+)?sns\s+topics?\b", "amazon sns"),
    (r"\beventbridge\s+(?:buses?|rules?|events?)\b", "amazon eventbridge"),
    (r"\bstep\s+functions?\s+(?:workflows?|state\s+machines?)\b", "aws step functions"),
    (r"\bcloudfront\s+distributions?\b", "amazon cloudfront"),
    (r"\bcloudwatch\s+(?:logs?|metrics?|alarms?|dashboards?)\b", "amazon cloudwatch"),
    (r"\biam\s+(?:roles?|policies?|users?|groups?)\b", "aws iam"),
    (r"\bsecrets?\s+manager\s+secrets?\b", "aws secrets manager"),
    (r"\bkms\s+keys?\b", "aws kms"),
    # Azure variants
    (r"\bfunction\s+apps?\b", "function app"),
    (r"\b(?:azure\s+)?app\s+services?\b", "azure app service"),
    (r"\b(?:azure\s+)?cosmos(?:\s+db)?\s+(?:containers?|collections?|databases?|accounts?)\b", "azure cosmos db"),
    (r"\b(?:azure\s+)?key\s+vaults?\b", "key vault"),
    (r"\b(?:azure\s+)?storage\s+accounts?\b", "azure storage account"),
    (r"\b(?:azure\s+)?blob\s+(?:storage|containers?)\b", "azure blob storage"),
    (r"\b(?:azure\s+)?service\s+bus(?:\s+queues?|\s+topics?)?\b", "azure service bus"),
    (r"\b(?:azure\s+)?event\s+hubs?\b", "azure event hubs"),
    (r"\b(?:azure\s+)?event\s+grid\b", "azure event grid"),
    (r"\b(?:azure\s+)?api\s+management\b", "azure api management"),
    (r"\b(?:azure\s+)?front\s+door\b", "azure front door"),
    (r"\b(?:azure\s+)?application\s+gateway(?!\s+waf)\b", "azure application gateway"),
    (r"\baks\s+clusters?\b", "aks"),
    (r"\b(?:azure\s+)?virtual\s+networks?\b", "azure virtual network"),
    (r"\bvnets?\b", "vnet"),
    (r"\bentra(?:\s+id)?\s+(?:users?|groups?|tenants?)?\b", "entra id"),
    (r"\bazure\s+monitor\s+(?:alerts?|metrics?|workbooks?)?\b", "azure monitor"),
    (r"\blog\s+analytics\s+workspaces?\b", "log analytics workspace"),
    (r"\bapplication\s+insights\b", "application insights"),
    # GCP variants
    (r"\b(?:google\s+)?bigquery\s+(?:datasets?|tables?|jobs?|projects?)\b", "google bigquery"),
    (r"\bgke\s+clusters?\b", "gke"),
    (r"\b(?:google\s+)?cloud\s+run\s+(?:services?|jobs?)\b", "cloud run"),
    (r"\b(?:google\s+)?cloud\s+functions?\b", "cloud functions"),
    (r"\b(?:google\s+)?cloud\s+storage\s+buckets?\b", "google cloud storage"),
    (r"\bgcs\s+buckets?\b", "gcs"),
    (r"\b(?:google\s+)?pub[/\s]sub\s+(?:topics?|subscriptions?)\b", "pub/sub"),
    (r"\bfirestore\s+(?:databases?|collections?|documents?)\b", "google firestore"),
    (r"\bspanner\s+(?:databases?|instances?)\b", "google cloud spanner"),
    (r"\bvertex\s+ai\s+(?:endpoints?|models?|pipelines?)\b", "vertex ai"),
    (r"\bcloud\s+sql\s+(?:instances?|databases?)\b", "cloud sql"),
    # Kubernetes variants
    (r"\b(?:kubernetes|k8s)\s+pods?\b", "kubernetes pod"),
    (r"\b(?:kubernetes|k8s)\s+deployments?\b", "kubernetes deployment"),
    (r"\b(?:kubernetes|k8s)\s+services?\b", "kubernetes service"),
    (r"\b(?:kubernetes|k8s)\s+ingress(?:es)?\b", "kubernetes ingress"),
    (r"\b(?:kubernetes|k8s)\s+configmaps?\b", "kubernetes configmap"),
    (r"\b(?:kubernetes|k8s)\s+secrets?\b", "kubernetes secret"),
    (r"\b(?:kubernetes|k8s)\s+namespaces?\b", "kubernetes namespace"),
    (r"\b(?:kubernetes|k8s)\s+nodes?\b", "kubernetes node"),
    (r"\b(?:kubernetes|k8s)\s+statefulsets?\b", "kubernetes statefulset"),
    (r"\b(?:kubernetes|k8s)\s+daemonsets?\b", "kubernetes daemonset"),
    (r"\b(?:kubernetes|k8s)\s+(?:cron)?jobs?\b", "kubernetes job"),
    (r"\b(?:kubernetes|k8s)\s+persistent\s+volumes?(?:\s+claims?)?\b", "kubernetes pv"),
    (r"\bpersistent\s+volume\s+claims?\b", "kubernetes pvc"),
    (r"\bservice\s+accounts?\b", "kubernetes serviceaccount"),
    # Bare K8s-distinctive terms (these compound nouns are K8s-only and
    # unambiguous, so they don't need a "k8s" prefix to resolve correctly).
    (r"\bconfigmaps?\b", "kubernetes configmap"),
    (r"\bdaemonsets?\b", "kubernetes daemonset"),
    (r"\bstatefulsets?\b", "kubernetes statefulset"),
    (r"\breplicasets?\b", "kubernetes replicaset"),
    (r"\bcronjobs?\b", "kubernetes cronjob"),
    (r"\bnetworkpolic(?:y|ies)\b", "kubernetes networkpolicy"),
    (r"\bclusterroles?\b", "kubernetes clusterrole"),
]

_FUZZY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), needle) for pattern, needle in _FUZZY_PATTERN_SOURCES
]


def _needle_lookup() -> dict[str, tuple[str, str]]:
    """needle -> (canonical_label, node_type) for fuzzy resolution."""

    table: dict[str, tuple[str, str]] = {}
    for label, needle, node_type in KNOWN_COMPONENTS:
        table.setdefault(needle, (label, node_type))
    return table


_NEEDLE_LOOKUP = _needle_lookup()


def _fuzzy_extract(text: str, result: ExtractionResult) -> None:
    """Match variant phrasings (plurals, "X buckets", "k8s pods", etc.).

    Runs after the exact-match pass so already-extracted components win on
    the slug dedup. Each fuzzy regex resolves to a canonical needle whose
    label and node_type come from KNOWN_COMPONENTS (which is itself derived
    from builtin_vendor_shapes), so adding a new vendor stencil + one fuzzy
    pattern is enough to recognize a new family of phrasings.
    """

    for pattern, needle in _FUZZY_PATTERNS:
        if not pattern.search(text):
            continue
        canonical = _NEEDLE_LOOKUP.get(needle)
        if canonical is None:
            continue
        label, node_type = canonical
        _add_component(result, label, node_type)


def _extract_known_components(text: str, result: ExtractionResult) -> None:
    """Match KNOWN_COMPONENTS needles against input prose.

    Strategy:
      1. Process needles longest-first so composite names like
         "application gateway waf" win over their substrings.
      2. Track the character spans already consumed by a longer match and
         skip shorter needles whose first occurrence falls entirely inside
         a consumed span.
      3. Use the actual matched substring from the input as the display
         label so the user's casing is preserved (e.g. "AKS" stays "AKS",
         "Azure Kubernetes Service" stays as typed) -- aligning with the
         "pick icons based on the input" principle.
    """

    lowered = text.lower()
    tower_awx_combined = "ansible tower" in lowered and "awx" in lowered
    if tower_awx_combined:
        _add_component(result, "Ansible Tower / AWX", "ansible")

    # Stable, deterministic ordering: longest needle first, then KNOWN_COMPONENTS
    # order as a tiebreaker (preserves hand-curated _CORE_KNOWN_COMPONENTS
    # precedence for equally-long needles).
    indexed = list(enumerate(KNOWN_COMPONENTS))
    indexed.sort(key=lambda item: (-len(item[1][1]), item[0]))

    consumed: list[tuple[int, int]] = []
    for _, (canonical_label, needle, node_type) in indexed:
        if tower_awx_combined and canonical_label in {"Ansible Tower", "AWX"}:
            continue
        match = _find_word_bounded(lowered, needle)
        if match is None:
            continue
        start, end = match
        if any(c_start <= start and end <= c_end for c_start, c_end in consumed):
            continue
        consumed.append((start, end))
        display_label = _preserve_input_label(text, start, end, canonical_label)
        _add_component(result, display_label, node_type)


def _find_word_bounded(haystack: str, needle: str) -> tuple[int, int] | None:
    """Find ``needle`` in ``haystack`` only if surrounded by word boundaries.

    Without this, the needle "function app" would match the "function app" inside
    "function apps", and "aks" would match inside "stacks". The boundary rule:
    the character immediately before the match must not be alphanumeric, and the
    character immediately after must not be alphanumeric.
    """

    if not needle:
        return None
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return None
        before_ok = idx == 0 or not _is_word_char(haystack[idx - 1])
        end = idx + len(needle)
        after_ok = end == len(haystack) or not _is_word_char(haystack[end])
        if before_ok and after_ok:
            return idx, end
        start = idx + 1


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char == "_"


def _preserve_input_label(text: str, start: int, end: int, canonical: str) -> str:
    """Use the actual matched input text as the label when it's well-formed.

    "Azure Kubernetes Service" in input keeps that exact casing. "AKS" stays
    "AKS". A scruffy all-lowercase or all-uppercase match (rare) falls back
    to the canonical hand-curated label so diagrams stay readable.
    """

    matched = text[start:end]
    if not matched.strip():
        return canonical
    # If the input is all-lowercase (e.g. "azure kubernetes service" in casual
    # prose), the canonical label reads better.
    if matched.islower() and matched != matched.upper():
        return canonical
    return matched


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

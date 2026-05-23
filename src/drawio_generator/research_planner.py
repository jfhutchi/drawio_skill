"""Research planning guidance for agents with search or local docs access."""

from __future__ import annotations


SOURCE_PRIORITY = [
    "Official vendor documentation",
    "Official architecture centers",
    "Official API documentation",
    "Official icon or stencil libraries",
    "Standards bodies where relevant",
    "Well-known engineering references",
    "Internal uploaded files",
    "Existing repository documentation",
    "General web sources only when better sources are unavailable",
]


def build_research_plan(request: str, diagram_type: str) -> list[str]:
    """Return concrete research tasks for a diagram request."""

    lowered = request.lower()
    tasks = [f"Identify authoritative references for a {diagram_type} diagram."]
    for vendor in ["azure", "aws", "google cloud", "kubernetes", "terraform", "github actions", "opentelemetry", "postgresql"]:
        if vendor in lowered:
            tasks.append(f"Check official {vendor.title()} architecture and service documentation.")
    if any(term in lowered for term in ["iam", "pam", "iga", "zero trust", "secret", "vault", "security"]):
        tasks.append("Check official identity/security architecture guidance and record trust boundary facts.")
    tasks.append("Separate confirmed facts, researched facts, assumptions, and open questions before drawing.")
    return tasks


def render_research_summary(request: str, diagram_type: str, completed_findings: list[str] | None = None) -> str:
    """Render a lightweight research summary scaffold."""

    findings = completed_findings or ["No live research was executed by the helper CLI; agent should fill this when web/local docs are available."]
    lines = [
        "# Research Summary",
        "",
        f"- Request: {request}",
        f"- Diagram type: {diagram_type}",
        "",
        "## Preferred Source Order",
        *[f"{index}. {source}" for index, source in enumerate(SOURCE_PRIORITY, start=1)],
        "",
        "## Findings",
        *[f"- {finding}" for finding in findings],
    ]
    return "\n".join(lines) + "\n"

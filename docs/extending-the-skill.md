# Extending The Skill

## Add Icon Mappings

Edit `src/drawio_generator/icon_registry.py`:

1. Add a style to `STYLE_REGISTRY`.
2. Add common synonyms to `ALIASES`.
3. Prefer diagrams.net built-in shapes.
4. Keep colors consistent with `templates/default-enterprise-theme.json`.
5. Add or update tests when the mapping changes behavior.

## Add File Parsers

Edit `src/drawio_generator/file_ingestion.py`:

1. Add a focused `_extract_*` function.
2. Return `Node` and `Edge` instances, not XML.
3. Redact text before extraction.
4. Avoid hard failures for partial or malformed files; record unknowns.
5. Add tests in `tests/test_file_ingestion.py`.

Good parser targets:

- Helm chart templates.
- Docker Compose services and networks.
- OpenAPI operations and servers.
- Mermaid and PlantUML relationship conversion.
- Terraform dependency graph extraction.
- Kubernetes namespace and service-to-deployment linking.

## Add Layout Strategies

Edit `src/drawio_generator/layout_engine.py`. Keep layout deterministic so tests and diffs stay stable. Prefer simple layered placement over complex auto-layout unless you also add visual regression or XML geometry tests.

## Add Validation Rules

Edit `src/drawio_generator/validators.py`. Validation should return explicit `ValidationIssue` records instead of raising for recoverable problems. Reserve exceptions for programming errors.

## Add Skill Documentation

Keep `SKILL.md` operational and concise enough for an AI agent to follow. Put heavy reference material in `docs/`, `templates/`, or `validation/` and link to it from the skill.

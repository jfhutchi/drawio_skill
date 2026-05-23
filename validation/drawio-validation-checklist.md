# Draw.io Validation Checklist

Use this checklist before claiming completion.

- XML parses without errors.
- Root element is `<mxfile>`.
- At least one `<diagram>` exists.
- A valid `<mxGraphModel>` exists.
- Root cells `id="0"` and `id="1"` exist.
- Every `mxCell` has a unique non-empty ID.
- Every vertex and edge has `mxGeometry`.
- Every edge source and target references an existing node.
- Critical nodes have readable labels.
- Important flows have directional arrows and labels.
- Boundaries are meaningful and visible.
- Legend explains color and boundary meaning.
- Secrets, tokens, private keys, passwords, and raw credentials are absent.
- `diagram-summary.md`, `assumptions.md`, `adversarial-review.md`, and `quality-checklist.md` exist.
- Assumptions, unknowns, and recommended follow-up diagrams are documented.

Run:

```bash
python -m unittest discover -s tests
PYTHONPATH=src python -m drawio_generator.cli --request "Create an Azure architecture diagram using AKS, Key Vault, PostgreSQL, GitHub Actions, Terraform, Prometheus, and Grafana." --input examples/azure-notes.md --output output --validate
python validation/validate_drawio.py output/diagram.drawio
```

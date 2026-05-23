# Microsoft 365 Copilot Adapter

Microsoft 365 Copilot does not consume a local `SKILL.md` folder directly. It uses a Microsoft 365 app package containing:

- `manifest.json`
- app icons
- a declarative agent manifest such as `declarativeAgent.json`

This folder provides a declarative-agent package template that ports the skill instructions into Microsoft 365 Copilot format.

## Build Package

```bash
python platforms/ms365-copilot/package_ms365.py --output enterprise-drawio-diagrammer-ms365.zip
```

The ZIP contains the files from `appPackage/` at the root, which is the shape expected by Microsoft 365 app package upload tooling.

## Important Limits

This declarative agent can guide Microsoft 365 Copilot to produce draw.io XML and supporting text, but it cannot run the local Python helper unless you add an API plugin or custom engine action hosted over HTTPS. For automated validation inside Microsoft 365 Copilot, expose the validator/generator as an API plugin or MCP-backed action and reference it from the declarative agent manifest.

Use tenant admin review, Responsible AI validation, and normal Microsoft 365 app publication workflows before deploying broadly.

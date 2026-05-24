# Icon Registry

The helper uses diagrams.net built-in styles and safe fallback shapes. It does not embed proprietary vendor icons. Common Azure and AWS service names are vendor-aware aliases, but they still resolve to safe built-in fallback shapes unless a licensed local official icon pack is explicitly integrated and documented. Agents may use official vendor icon packs only when licensing permits it and the resulting draw.io file remains portable.

## Built-In Categories

- General: actor, user, process, repository, artifact.
- Application: frontend, API, backend, worker.
- Data: database, cache, queue.
- Cloud and network: cloud, CDN, gateway, WAF, firewall, network.
- Security: identity, secret store, security controls.
- Platform: Kubernetes, container, server.
- DevOps: Terraform, Ansible, build/deploy processes.
- Operations: monitoring, logging, dashboard.

## Vendor-Aware Aliases

Azure aliases include Azure Kubernetes Service/AKS, Azure Front Door, Application Gateway, Key Vault, Azure Database for PostgreSQL, Azure SQL, Azure Monitor, and Log Analytics. AWS aliases include Lambda, S3, DynamoDB, RDS, CloudFront, WAF, IAM, and API Gateway. These aliases improve shape choice and licensing metadata; they do not mean official cloud icons were embedded.

## Fallback Rule

If a precise icon is unavailable, choose the closest safe built-in shape with a clear label. Do not fail diagram generation because a branded icon is unavailable.

## Adding Mappings

Add aliases and style definitions in `src/drawio_generator/icon_registry.py`. Keep styles simple, readable, and compatible with diagrams.net XML. Prefer muted enterprise colors and avoid decorative icon choices that make the diagram harder to scan.

## Local Licensed Vendor Icon Packs

To opt into officially licensed vendor icons, drop a `manifest.json` next to the icons under `stencils/<vendor>/`. The manifest must explicitly attest to the license terms:

```json
{
  "vendor": "azure",
  "license_acknowledged": true,
  "license_notice": "Azure icons licensed under enterprise agreement EA-123",
  "shapes": {
    "azure kubernetes service": "shape=mscae/Kubernetes_Services;html=1;...",
    "key vault": "shape=mscae/Key_Vaults;html=1;..."
  }
}
```

Behavior:

- The resolver only marks an icon `official: true` when a manifest is present, `license_acknowledged` is `true`, and the service name matches a manifest entry.
- Without a manifest, every vendor service falls back to safe diagrams.net built-in shapes and the `license_notice` records that no official icon was embedded.
- Manifests that fail to parse or lack license acknowledgement are silently ignored for that vendor only.

Supported vendor keys today: `azure`, `aws`, `gcp`. Add additional vendors by including a matching `stencils/<vendor>/manifest.json` and corresponding `VENDOR_TERMS` entry in `icon_registry.py`.

For executive architecture pages, prefer icon-like built-in shapes that improve scanning without introducing proprietary icon dependencies:

- Source control: folder/repository.
- Tower, AWX, CI, and orchestration: process/controller.
- Customer targets: server-style infrastructure shapes.
- Databases and queues: cylinder and queue shapes.
- Reports and workbooks: document/note shapes.
- Vaults and secret stores: security-colored lock/vault fallback.
- SFS or external object storage: cloud/object-storage fallback.
- Consumers: actor/user shapes.

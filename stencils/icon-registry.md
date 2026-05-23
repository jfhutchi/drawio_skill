# Icon Registry

The helper uses diagrams.net built-in styles and safe fallback shapes. It does not embed proprietary vendor icons. Agents may use official vendor icon packs only when licensing permits it and the resulting draw.io file remains portable.

## Built-In Categories

- General: actor, user, process, repository, artifact.
- Application: frontend, API, backend, worker.
- Data: database, cache, queue.
- Cloud and network: cloud, CDN, gateway, WAF, firewall, network.
- Security: identity, secret store, security controls.
- Platform: Kubernetes, container, server.
- DevOps: Terraform, Ansible, build/deploy processes.
- Operations: monitoring, logging, dashboard.

## Fallback Rule

If a precise icon is unavailable, choose the closest safe built-in shape with a clear label. Do not fail diagram generation because a branded icon is unavailable.

## Adding Mappings

Add aliases and style definitions in `src/drawio_generator/icon_registry.py`. Keep styles simple, readable, and compatible with diagrams.net XML. Prefer muted enterprise colors and avoid decorative icon choices that make the diagram harder to scan.

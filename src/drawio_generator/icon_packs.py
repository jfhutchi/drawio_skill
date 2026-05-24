"""Local vendor icon pack discovery and resolution.

Vendor icon packs are opt-in. A vendor pack is recognized only when a
``stencils/<vendor>/manifest.json`` file exists and explicitly attests that
the user has the right to use the icons. The manifest format is:

```
{
  "vendor": "azure",
  "license_acknowledged": true,
  "license_notice": "Microsoft Azure icons used under <license terms>",
  "shapes": {
    "azure kubernetes service": "shape=mscae/Kubernetes_Services;...",
    "key vault": "shape=mscae/Key_Vaults;..."
  }
}
```

Without a manifest the helper falls back to safe diagrams.net built-in
shapes and never claims that an official vendor icon was embedded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class IconPack:
    """A locally licensed vendor icon pack."""

    vendor: str
    root: Path
    license_notice: str
    shapes: dict[str, str]

    def lookup(self, key: str) -> str | None:
        return self.shapes.get(key.strip().lower())


def _default_search_roots() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        Path.cwd() / "stencils",
        here.parents[2] / "stencils",
        here.parents[3] / "stencils" if len(here.parents) > 3 else None,
    ]


def _candidate_roots(extra: Iterable[Path] | None) -> list[Path]:
    roots: list[Path] = []
    if extra:
        roots.extend(Path(item) for item in extra)
    for root in _default_search_roots():
        if root is None:
            continue
        if root not in roots:
            roots.append(root)
    return roots


def discover_icon_packs(extra_roots: Iterable[Path] | None = None) -> dict[str, IconPack]:
    """Discover vendor icon packs that explicitly acknowledge licensing.

    Returns a dict keyed by lowercase vendor name. Vendors that lack a
    manifest, fail license acknowledgement, or fail to parse are skipped
    silently for that vendor only. The default fallback registry continues to
    apply for those vendors.
    """

    packs: dict[str, IconPack] = {}
    for root in _candidate_roots(extra_roots):
        if not root.exists() or not root.is_dir():
            continue
        for vendor_dir in sorted(root.iterdir()):
            if not vendor_dir.is_dir():
                continue
            manifest_path = vendor_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            pack = _load_manifest(manifest_path)
            if pack is None:
                continue
            packs.setdefault(pack.vendor, pack)
    return packs


def _load_manifest(path: Path) -> IconPack | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    vendor = str(data.get("vendor", "")).strip().lower()
    if not vendor:
        return None
    if data.get("license_acknowledged") is not True:
        return None
    shapes_raw = data.get("shapes") or {}
    if not isinstance(shapes_raw, dict):
        return None
    shapes: dict[str, str] = {}
    for key, value in shapes_raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        clean_value = value.strip()
        if not clean_value:
            continue
        shapes[key.strip().lower()] = clean_value
    if not shapes:
        return None
    license_notice = str(data.get("license_notice", "")).strip()
    if not license_notice:
        license_notice = f"{vendor.upper()} official icon pack from {path.parent}"
    return IconPack(vendor=vendor, root=path.parent, license_notice=license_notice, shapes=shapes)

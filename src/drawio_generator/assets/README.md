# Vendored preview icons

SVG icon files vendored from the shape libraries bundled with
diagrams.net (app.diagrams.net, fetched 2026-08-12), used solely so
`preview-page-<n>.svg` can show the same glyph artwork the emitted
`.drawio` file references via `image=img/lib/...` styles.

- `azure2/` — Microsoft Azure architecture icons as bundled by
  diagrams.net. Microsoft permits use of these icons in architecture
  diagrams and documentation; do not distort them or use them to
  represent other products. See
  https://learn.microsoft.com/azure/architecture/icons/
- `mscae/` — Microsoft Cloud and Enterprise symbol set as bundled by
  diagrams.net (same usage terms family).

Only icons verified to render in a live diagrams.net instance are
vendored (the set mirrors `_AZURE2_IMAGES` in
`builtin_vendor_shapes.py` plus `mscae/Docker.svg`). The generated
`.drawio` files never embed these bytes — they reference the paths that
ship with every diagrams.net install.

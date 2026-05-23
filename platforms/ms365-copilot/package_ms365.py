#!/usr/bin/env python3
"""Package the Microsoft 365 Copilot declarative agent template."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
APP_PACKAGE = SCRIPT_DIR / "appPackage"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Microsoft 365 Copilot app package ZIP.")
    parser.add_argument("--output", default=str(SCRIPT_DIR / "enterprise-drawio-diagrammer-ms365.zip"))
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(APP_PACKAGE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(APP_PACKAGE).as_posix())
    print(f"Wrote Microsoft 365 Copilot app package: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

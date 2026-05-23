#!/usr/bin/env python3
"""Validate that a .drawio file is valid diagrams.net XML."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from drawio_generator.validators import validate_drawio_xml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a .drawio / diagrams.net XML file for required structure, references, geometry, and secrets."
    )
    parser.add_argument("path", help="Path to a .drawio file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    drawio_path = Path(args.path)
    if not drawio_path.exists():
        return _emit(
            args.json,
            drawio_path,
            valid=False,
            errors=[f"File does not exist: {drawio_path}"],
            warnings=[],
            exit_code=2,
        )
    if drawio_path.is_dir():
        return _emit(
            args.json,
            drawio_path,
            valid=False,
            errors=[f"Path is a directory, expected a .drawio file: {drawio_path}"],
            warnings=[],
            exit_code=2,
        )

    xml_text = drawio_path.read_text(encoding="utf-8", errors="replace")
    issues = validate_drawio_xml(xml_text)
    errors = [issue.message for issue in issues if issue.severity == "error"]
    warnings = [issue.message for issue in issues if issue.severity != "error"]
    return _emit(args.json, drawio_path, valid=not errors, errors=errors, warnings=warnings, exit_code=0 if not errors else 1)


def _emit(json_mode: bool, path: Path, valid: bool, errors: list[str], warnings: list[str], exit_code: int) -> int:
    if json_mode:
        print(
            json.dumps(
                {
                    "path": str(path),
                    "valid": valid,
                    "errors": errors,
                    "warnings": warnings,
                },
                indent=2,
            )
        )
        return exit_code

    status = "VALID" if valid else "INVALID"
    print(f"{status}: {path}")
    for error in errors:
        print(f"ERROR: {error}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

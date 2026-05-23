#!/usr/bin/env python3
"""Install the enterprise-drawio-diagrammer skill into a local skills directory."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


SKILL_NAME = "enterprise-drawio-diagrammer"
SKILL_ROOT = Path(__file__).resolve().parent
EXCLUDED_DIRS = {".git", "__pycache__", "output", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-command installer for the enterprise draw.io diagrammer skill.")
    parser.add_argument("--target-dir", help="Skills directory to install into. Default: CODEX_HOME\\skills or ~/.codex/skills.")
    parser.add_argument("--home", help="Home directory override for tests or portable installs.")
    parser.add_argument("--codex", action="store_true", help="Install to Codex personal skills.")
    parser.add_argument("--agents", action="store_true", help="Install to ~/.agents/skills instead of Codex skills.")
    parser.add_argument("--claude", action="store_true", help="Install to Claude Code personal skills.")
    parser.add_argument("--copilot", action="store_true", help="Install to GitHub Copilot personal agent skills.")
    parser.add_argument("--both", action="store_true", help="Install to both ~/.codex/skills and ~/.agents/skills.")
    parser.add_argument("--all-local", action="store_true", help="Install to local Codex, Claude Code, GitHub Copilot, and ~/.agents skills folders.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without copying files.")
    parser.add_argument("--yes", action="store_true", help="Overwrite an existing install without prompting.")
    args = parser.parse_args(argv)

    targets = _target_dirs(args)
    for target_dir in targets:
        destination = target_dir / SKILL_NAME
        print(f"{'DRY RUN: ' if args.dry_run else ''}Install {SKILL_ROOT} -> {destination}")
        if args.dry_run:
            continue
        _install_to(destination, assume_yes=args.yes)

    if args.dry_run:
        print("DRY RUN complete. No files were copied.")
    else:
        print("Installation complete.")
        print("Restart Codex or reload skills if the new skill is not visible immediately.")
    return 0


def _target_dirs(args: argparse.Namespace) -> list[Path]:
    home = Path(args.home).expanduser() if args.home else Path.home()
    if args.target_dir:
        return [Path(args.target_dir).expanduser()]
    if args.all_local:
        return [
            _codex_skills_dir(home),
            home / ".agents" / "skills",
            home / ".claude" / "skills",
            home / ".copilot" / "skills",
        ]
    if args.both:
        return [_codex_skills_dir(home), home / ".agents" / "skills"]
    selected: list[Path] = []
    if args.codex:
        selected.append(_codex_skills_dir(home))
    if args.agents:
        selected.append(home / ".agents" / "skills")
    if args.claude:
        selected.append(home / ".claude" / "skills")
    if args.copilot:
        selected.append(home / ".copilot" / "skills")
    if selected:
        return selected
    return [_codex_skills_dir(home)]


def _codex_skills_dir(home: Path) -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return home / ".codex" / "skills"


def _install_to(destination: Path, assume_yes: bool) -> None:
    if destination.resolve() == SKILL_ROOT.resolve():
        raise SystemExit("Refusing to install onto the source directory.")

    if destination.exists():
        if not assume_yes and not _confirm_overwrite(destination):
            print(f"Skipped existing install: {destination}")
            return
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_ROOT, destination, ignore=_ignore_install_files)


def _confirm_overwrite(destination: Path) -> bool:
    if not sys.stdin.isatty():
        return False
    response = input(f"{destination} already exists. Overwrite it? [y/N] ").strip().lower()
    return response in {"y", "yes"}


def _ignore_install_files(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(directory) / name
        if path.is_dir() and name in EXCLUDED_DIRS:
            ignored.add(name)
        elif path.suffix in EXCLUDED_SUFFIXES:
            ignored.add(name)
    return ignored


if __name__ == "__main__":
    raise SystemExit(main())

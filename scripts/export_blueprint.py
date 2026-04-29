"""HiveMind blueprint export CLI.

Examples
--------
    # Smoke-test a blueprint without writing anything
    python scripts/export_blueprint.py blueprints/quote-bot.example.yaml --dry-run

    # Export to a directory
    python scripts/export_blueprint.py blueprints/quote-bot.example.yaml \\
        --output dist/quote-bot

    # Export and produce a ZIP next to the output dir
    python scripts/export_blueprint.py blueprints/quote-bot.example.yaml \\
        --output dist/quote-bot --zip

    # List discoverable assets the blueprint can reference
    python scripts/export_blueprint.py --list-assets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/export_blueprint.py …` from the repo root by ensuring
# the repo root is on sys.path before resolving the sibling _export package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Best-effort UTF-8 stdout — Windows consoles default to cp1252 which chokes
# on Chinese skill descriptions. Safe to ignore failures (Python <3.7, etc.).
try:  # pragma: no cover - cosmetic
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from scripts._export import (
    Packager,
    PackagerProgress,
    load_blueprint,
    scan_assets,
)

# ANSI colours — degrade gracefully on Windows older shells (PS 7+ supports them).
_RESET = "\033[0m"
_GREY = "\033[90m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"

_STATUS_COLOR = {
    "start": _BLUE,
    "ok": _GREEN,
    "skip": _GREY,
    "warn": _YELLOW,
    "error": _RED,
}


def _print_progress(ev: PackagerProgress) -> None:
    color = _STATUS_COLOR.get(ev.status, "")
    detail = f" — {ev.detail}" if ev.detail else ""
    print(f"{color}[{ev.status:>5}]{_RESET} {ev.step}{detail}")


def _cmd_export(args: argparse.Namespace) -> int:
    bp_path = Path(args.blueprint)
    if not bp_path.exists():
        print(f"blueprint not found: {bp_path}", file=sys.stderr)
        return 2
    bp = load_blueprint(bp_path)

    if args.dry_run:
        print(f"[dry-run] blueprint OK: {bp.name} v{bp.version} ({bp.customer})")
        print(f"  platform_mode = {bp.platform_mode.value}")
        print(f"  ui_mode       = {bp.ui_mode.value}")
        print(f"  agents        = {[a.id for a in bp.agents]}")
        print(f"  default_agent = {bp.resolved_default_agent_id()}")
        return 0

    if not args.output:
        print("--output is required when not using --dry-run", file=sys.stderr)
        return 2

    output_dir = Path(args.output).resolve()
    pkg = Packager(bp, output_dir, overwrite=args.overwrite)
    pkg.on_progress = _print_progress  # type: ignore[method-assign]

    try:
        result = pkg.run(make_zip=args.zip)
    except FileExistsError as exc:
        print(f"{_RED}[error]{_RESET} {exc}", file=sys.stderr)
        return 1

    print()
    print(f"  output    : {result.output_dir}")
    if result.zip_path:
        print(f"  archive   : {result.zip_path}")
    print(f"  files     : {result.files_written}")
    print(f"  size      : {result.bytes_written / 1024:.1f} KB")
    if result.warnings:
        print(f"  warnings  : {len(result.warnings)}")
        for w in result.warnings:
            print(f"    - {w}")
    return 0


def _cmd_list_assets(args: argparse.Namespace) -> int:
    catalog = scan_assets()
    if args.json:
        print(json.dumps(catalog.model_dump(), ensure_ascii=False, indent=2))
        return 0
    print(f"Skills ({len(catalog.skills)}):")
    for a in catalog.skills:
        print(f"  - {a.id:30s} {a.description[:60]}")
    print(f"\nMCP servers ({len(catalog.mcp_servers)}):")
    for a in catalog.mcp_servers:
        print(f"  - {a.id:30s} {a.description[:60]}")
    print(f"\nAgent templates ({len(catalog.agent_templates)}):")
    for a in catalog.agent_templates:
        print(f"  - {a.id:30s} {a.path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="export_blueprint",
        description="Export a HiveMind blueprint into a deployable delivery package.",
    )
    p.add_argument("blueprint", nargs="?", help="Path to blueprint YAML/JSON")
    p.add_argument("--output", "-o", help="Output directory")
    p.add_argument("--zip", action="store_true", help="Also produce a .zip next to --output")
    p.add_argument(
        "--overwrite", action="store_true", help="Wipe --output if it already exists"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Validate the blueprint and exit"
    )
    p.add_argument(
        "--list-assets",
        action="store_true",
        help="List skills/mcp servers the blueprint can reference, then exit",
    )
    p.add_argument("--json", action="store_true", help="Machine-readable output for --list-assets")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.list_assets:
        return _cmd_list_assets(args)
    if not args.blueprint:
        print("blueprint path is required (or pass --list-assets)", file=sys.stderr)
        return 2
    return _cmd_export(args)


if __name__ == "__main__":
    raise SystemExit(main())

"""
Export FastAPI OpenAPI schema for each PLATFORM_MODE.

Why this exists
---------------
HiveMind ships three deployment SKUs via the ``PLATFORM_MODE`` env var:

    full   = RAG + Agent (default)
    rag    = Knowledge retrieval platform only
    agent  = Agent orchestration platform only

Each mode exposes a different subset of routes (see ``app.api.__init__``).
This script freezes the OpenAPI contract for each mode into a JSON file under
``shared/openapi/``, so that:

* Front-end & external SDK generators have a versioned contract to consume.
* Reviews can ``git diff`` the schema between branches.
* Customers integrating against a specific SKU can pin to one file.

Usage
-----
    # Single mode (current process)
    python -m scripts.export_openapi --mode full
    python -m scripts.export_openapi --mode rag --output shared/openapi/rag.json

    # All three modes (spawns one subprocess per mode for clean isolation)
    python -m scripts.export_openapi --mode all

Run from the ``backend/`` directory (or anywhere PYTHONPATH includes it).
The script does NOT start the application lifespan — it only imports the
FastAPI ``app`` object and calls ``app.openapi()``, so no database / network
dependencies are required.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Modes that map 1:1 to PlatformMode in app.core.config
VALID_MODES = ("full", "rag", "agent")

# Repo root = backend/.. (this file lives at backend/scripts/export_openapi.py)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "shared" / "openapi"


def _default_output_path(mode: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{mode}.json"


def _dump_single_mode(mode: str, output: Path) -> Path:
    """Import the FastAPI app under the given PLATFORM_MODE and dump its OpenAPI schema.

    Must run in a *fresh* Python process for each mode, because ``app.api.__init__``
    decides which routers to mount at import time based on ``settings.PLATFORM_MODE``.
    Re-importing within the same process is brittle (router state, registries, etc.).
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode {mode!r}; expected one of {VALID_MODES}")

    # Set BEFORE importing app.* so the settings singleton picks it up.
    os.environ["PLATFORM_MODE"] = mode

    # Import lazily so the env var above is honoured.
    from app.main import app  # noqa: WPS433 (intentional late import)

    schema = app.openapi()
    # Annotate the schema with the mode it was generated under, for traceability.
    schema.setdefault("info", {})["x-hivemind-platform-mode"] = mode

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    paths = len(schema.get("paths", {}))
    print(f"[export_openapi] mode={mode:<5} paths={paths:<4} -> {output}")
    return output


def _dump_all_modes(output_dir: Path) -> list[Path]:
    """Spawn one subprocess per mode so each gets a clean import graph."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for mode in VALID_MODES:
        out = output_dir / f"{mode}.json"
        cmd = [
            sys.executable,
            "-m",
            "scripts.export_openapi",
            "--mode",
            mode,
            "--output",
            str(out),
        ]
        # cwd = backend/ so that ``-m scripts.export_openapi`` resolves correctly.
        subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])
        written.append(out)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--mode",
        choices=(*VALID_MODES, "all"),
        default="all",
        help="Which PLATFORM_MODE to dump. 'all' spawns one subprocess per mode.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file (single mode) or directory (--mode all). "
             f"Defaults to {DEFAULT_OUTPUT_DIR} / <mode>.json",
    )
    args = parser.parse_args()

    if args.mode == "all":
        out_dir = args.output or DEFAULT_OUTPUT_DIR
        if out_dir.exists() and not out_dir.is_dir():
            parser.error(f"--output must be a directory when --mode all (got {out_dir})")
        _dump_all_modes(out_dir)
    else:
        out_path = args.output or _default_output_path(args.mode)
        if out_path.is_dir():
            out_path = out_path / f"{args.mode}.json"
        _dump_single_mode(args.mode, out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

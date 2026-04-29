"""Export service — wraps ``scripts._export`` for use from the FastAPI layer.

Responsibilities:
- Resolve the repo root (the FastAPI process may run from anywhere).
- Make the ``scripts`` package importable.
- Run packager jobs in a thread pool (the work is sync, mostly file I/O).
- Track jobs in an in-memory registry so SSE/poll endpoints can stream progress.

Job state is intentionally kept in-process — for a single backend container
this is enough; horizontal scaling can later swap the registry for Redis.
"""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
import sys
import threading
import time
import uuid
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from loguru import logger

# Repo root: backend/app/services/export_service.py → parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_export_pkg() -> ModuleType:
    """Load the repo-root ``scripts/_export`` package without colliding with
    ``backend/scripts`` (the two share the name ``scripts`` on sys.path)."""
    pkg_dir = _REPO_ROOT / "scripts" / "_export"
    init_path = pkg_dir / "__init__.py"
    if not init_path.exists():
        raise ImportError(f"hivemind export toolkit not found at {pkg_dir}")
    # Register as a unique top-level module so re-imports don't fight with
    # backend/scripts/ on sys.path.
    spec = importlib.util.spec_from_file_location(
        "hivemind_export",
        init_path,
        submodule_search_locations=[str(pkg_dir)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["hivemind_export"] = module
    # Submodules need REPO_ROOT/scripts on sys.path so their relative imports
    # (``from scripts._export.schema import …``) keep working.
    repo_scripts_root = str(_REPO_ROOT)
    if repo_scripts_root not in sys.path:
        sys.path.append(repo_scripts_root)
    spec.loader.exec_module(module)
    return module


_export_pkg = _load_export_pkg()
Blueprint = _export_pkg.Blueprint
Packager = _export_pkg.Packager
PackagerProgress = _export_pkg.PackagerProgress
scan_assets = _export_pkg.scan_assets


# Where exported packages are written.
# IMPORTANT: must NOT be a path watched by uvicorn --reload, otherwise the
# packager writing fresh *.py files into it will retrigger reload and wipe
# the in-memory job registry mid-export. We default to the system temp dir;
# operators can override via the HIVEMIND_EXPORT_DIR env var to point at a
# nfs/shared volume in production.
import os
import tempfile

EXPORT_OUTPUT_ROOT = Path(
    os.environ.get(
        "HIVEMIND_EXPORT_DIR",
        str(Path(tempfile.gettempdir()) / "hivemind_exports"),
    )
)


@dataclass
class JobEvent:
    ts: float
    step: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ts": self.ts, "step": self.step, "status": self.status, "detail": self.detail}


@dataclass
class ExportJob:
    id: str
    blueprint_name: str
    status: str = "pending"  # pending | running | succeeded | failed
    output_dir: Path | None = None
    zip_path: Path | None = None
    events: list[JobEvent] = field(default_factory=list)
    error: str | None = None
    files_written: int = 0
    bytes_written: int = 0
    warnings: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    # Used by the SSE endpoint to wake up consumers when new events arrive.
    _condition: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "blueprint_name": self.blueprint_name,
            "status": self.status,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "zip_path": str(self.zip_path) if self.zip_path else None,
            "files_written": self.files_written,
            "bytes_written": self.bytes_written,
            "warnings": self.warnings,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "events": [e.to_dict() for e in self.events],
        }


class ExportService:
    """In-memory job registry + packager driver."""

    def __init__(self) -> None:
        self._jobs: dict[str, ExportJob] = {}
        self._lock = threading.Lock()

    # ── Asset discovery ─────────────────────────────────────────────────

    def list_assets(self) -> dict[str, Any]:
        """Snapshot of skills/mcp servers/agent templates available right now."""
        return scan_assets(_REPO_ROOT).model_dump()

    # ── Validation ──────────────────────────────────────────────────────

    def validate_blueprint(self, payload: dict[str, Any]) -> Blueprint:
        """Validate a raw dict via the pydantic schema. Raises ValueError on bad input."""
        return Blueprint.model_validate(payload)

    # ── Job lifecycle ───────────────────────────────────────────────────

    def submit(self, blueprint: Blueprint, *, make_zip: bool = True) -> ExportJob:
        job_id = uuid.uuid4().hex[:12]
        output_dir = EXPORT_OUTPUT_ROOT / f"{blueprint.name}-{job_id}"
        job = ExportJob(
            id=job_id,
            blueprint_name=blueprint.name,
            output_dir=output_dir,
        )
        with self._lock:
            self._jobs[job_id] = job
        # Run in default executor — packager is sync I/O.
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_job(job, blueprint, make_zip=make_zip))
        return job

    def get(self, job_id: str) -> ExportJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> list[ExportJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    # ── Internal ────────────────────────────────────────────────────────

    async def _run_job(self, job: ExportJob, blueprint: Blueprint, *, make_zip: bool) -> None:
        job.status = "running"
        loop = asyncio.get_event_loop()
        # Buffer of (step, status, detail) populated on the worker thread.
        # We pump events into the asyncio job condition from the main loop after
        # each callback to avoid cross-thread asyncio primitives.
        pending: list[PackagerProgress] = []
        pending_lock = threading.Lock()

        def on_progress(ev: PackagerProgress) -> None:
            with pending_lock:
                pending.append(ev)
            # Schedule notify on the main loop. call_soon_threadsafe is safe.
            loop.call_soon_threadsafe(asyncio.create_task, self._drain(job, pending, pending_lock))

        def _do_run() -> None:
            try:
                pkg = Packager(blueprint, job.output_dir, overwrite=True)
                pkg.on_progress = on_progress  # type: ignore[method-assign]
                result = pkg.run(make_zip=make_zip)
                job.files_written = result.files_written
                job.bytes_written = result.bytes_written
                job.warnings = list(result.warnings)
                job.zip_path = result.zip_path
                job.status = "succeeded"
            except Exception as exc:  # noqa: BLE001 — surface any failure to UI
                logger.exception("export job {} failed", job.id)
                job.error = f"{type(exc).__name__}: {exc}"
                job.status = "failed"
            finally:
                job.finished_at = time.time()

        await loop.run_in_executor(None, _do_run)
        # Final drain in case events were queued after the last notify.
        await self._drain(job, pending, pending_lock)
        async with job._condition:
            job._condition.notify_all()

    async def _drain(
        self,
        job: ExportJob,
        pending: list[PackagerProgress],
        pending_lock: threading.Lock,
    ) -> None:
        async with job._condition:
            with pending_lock:
                if not pending:
                    return
                drained = pending[:]
                pending.clear()
            for ev in drained:
                job.events.append(
                    JobEvent(ts=time.time(), step=ev.step, status=ev.status, detail=ev.detail)
                )
            job._condition.notify_all()

    # ── Streaming ───────────────────────────────────────────────────────

    async def stream_events(self, job_id: str) -> Iterable[dict[str, Any]]:
        """Async generator yielding event dicts as they appear, then a terminal event."""
        job = self.get(job_id)
        if job is None:
            yield {"type": "error", "detail": f"unknown job: {job_id}"}
            return
        cursor = 0
        while True:
            async with job._condition:
                # Wait until either new events arrived or job finished.
                while cursor >= len(job.events) and job.status in ("pending", "running"):
                    await job._condition.wait()
                # Drain whatever is buffered.
                new = job.events[cursor:]
                cursor = len(job.events)
            for ev in new:
                yield {"type": "progress", **ev.to_dict()}
            if job.status not in ("pending", "running"):
                yield {
                    "type": "done",
                    "status": job.status,
                    "files_written": job.files_written,
                    "bytes_written": job.bytes_written,
                    "warnings": job.warnings,
                    "error": job.error,
                    "zip_path": str(job.zip_path) if job.zip_path else None,
                }
                return

    # ── Cleanup ─────────────────────────────────────────────────────────

    def delete(self, job_id: str) -> bool:
        """Remove a job and its on-disk artefacts. Returns True if anything was removed."""
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        if job.output_dir and job.output_dir.exists():
            shutil.rmtree(job.output_dir, ignore_errors=True)
        if job.zip_path and job.zip_path.exists():
            try:
                job.zip_path.unlink()
            except OSError:
                pass
        return True

    # ── Download helper ─────────────────────────────────────────────────

    def ensure_zip(self, job: ExportJob) -> Path:
        """Return path to a ZIP for the job, creating one on the fly if needed."""
        if job.zip_path and job.zip_path.exists():
            return job.zip_path
        if not job.output_dir or not job.output_dir.exists():
            raise FileNotFoundError("job has no output directory to zip")
        target = job.output_dir.parent / f"{job.output_dir.name}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in job.output_dir.rglob("*"):
                if entry.is_dir():
                    continue
                zf.write(entry, arcname=str(entry.relative_to(job.output_dir.parent)))
        job.zip_path = target
        return target


# Module-level singleton — endpoints import this directly.
export_service = ExportService()

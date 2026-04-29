"""Export API — UI-driven blueprint export pipeline.

Endpoints
---------
GET   /api/v1/export/assets                  → discoverable skills / mcp / templates
POST  /api/v1/export/blueprints/validate     → pydantic-validate a draft blueprint
POST  /api/v1/export/jobs                    → submit an export job, returns job_id
GET   /api/v1/export/jobs                    → list recent jobs
GET   /api/v1/export/jobs/{job_id}           → poll job status (no streaming)
GET   /api/v1/export/jobs/{job_id}/stream    → SSE progress feed
GET   /api/v1/export/jobs/{job_id}/download  → download the produced .zip
DELETE /api/v1/export/jobs/{job_id}          → remove job + on-disk artefacts
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from app.common.response import ApiResponse
from app.services.export_service import ExportToolkitUnavailable, export_service


def _toolkit_or_503() -> None:
    """Reject the request with 503 when the export toolkit isn't bundled.

    All endpoints in this router need the packager source under
    ``scripts/_export`` — that directory is intentionally absent from exported
    delivery packages, so we surface a clean error instead of leaking the
    underlying ImportError.
    """
    try:
        export_service._require_toolkit()
    except ExportToolkitUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# Every endpoint on this router requires the toolkit; one dependency on the
# router covers them all without sprinkling Depends() on each handler.
router = APIRouter(dependencies=[Depends(_toolkit_or_503)])


# ── Request / response models ───────────────────────────────────────────────


class BlueprintPayload(BaseModel):
    """Untyped wrapper around a raw blueprint dict.

    We accept ``dict`` rather than the full ``Blueprint`` schema directly so
    the OpenAPI surface stays stable when the schema evolves; validation is
    performed inside the service and surfaces detailed pydantic errors.
    """

    blueprint: dict[str, Any] = Field(..., description="Raw blueprint document.")


class JobSubmitPayload(BlueprintPayload):
    make_zip: bool = Field(True, description="Produce a downloadable .zip artefact.")


class ValidationErrorResponse(BaseModel):
    success: bool = False
    message: str = "Invalid blueprint"
    errors: list[dict[str, Any]] = []


# ── Routes ──────────────────────────────────────────────────────────────────


@router.get("/assets", response_model=ApiResponse)
async def list_assets() -> ApiResponse:
    """Return skills / MCP servers / agent templates the wizard can pick from."""
    return ApiResponse.ok(export_service.list_assets())


@router.post("/blueprints/validate")
async def validate_blueprint(payload: BlueprintPayload) -> Any:
    """Run the blueprint through the pydantic schema and report errors."""
    try:
        bp = export_service.validate_blueprint(payload.blueprint)
    except ValidationError as exc:
        return ValidationErrorResponse(errors=exc.errors())
    return ApiResponse.ok(
        {
            "name": bp.name,
            "version": bp.version,
            "platform_mode": bp.platform_mode.value,
            "ui_mode": bp.ui_mode.value,
            "default_agent_id": bp.resolved_default_agent_id(),
        }
    )


@router.post("/jobs", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(payload: JobSubmitPayload) -> ApiResponse:
    """Validate the blueprint and kick off a background export job."""
    try:
        bp = export_service.validate_blueprint(payload.blueprint)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": exc.errors()},
        ) from exc
    job = export_service.submit(bp, make_zip=payload.make_zip)
    logger.info("export job {} submitted (blueprint={})", job.id, bp.name)
    return ApiResponse.created({"job_id": job.id, **job.to_dict()})


@router.get("/jobs", response_model=ApiResponse)
async def list_jobs(limit: int = 50) -> ApiResponse:
    return ApiResponse.ok([j.to_dict() for j in export_service.list_jobs(limit=limit)])


@router.get("/jobs/{job_id}", response_model=ApiResponse)
async def get_job(job_id: str) -> ApiResponse:
    job = export_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return ApiResponse.ok(job.to_dict())


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    """Server-Sent Events stream of job progress."""
    job = export_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_source():
        async for event in export_service.stream_events(job_id):
            payload = json.dumps(event, ensure_ascii=False)
            yield f"event: {event.get('type', 'progress')}\ndata: {payload}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/download")
async def download_job(job_id: str) -> FileResponse:
    job = export_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "succeeded":
        raise HTTPException(
            status_code=409, detail=f"job not ready (status={job.status})"
        )
    try:
        zip_path = export_service.ensure_zip(job)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_path.name,
    )


@router.delete("/jobs/{job_id}", response_model=ApiResponse)
async def delete_job(job_id: str) -> ApiResponse:
    if not export_service.delete(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    return ApiResponse.deleted()

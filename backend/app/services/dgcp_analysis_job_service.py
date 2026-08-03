"""Jobs asincrónicos — análisis DGCP de larga duración (Hermes, checklist, expediente)."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.redis_client import get_redis
from app.db.session import AsyncSessionLocal
from app.models.dgcp_bid_package import DGCPBidPackage
from app.schemas.dgcp_analysis_job import (
    DGCPAnalysisJobAcceptedResponse,
    DGCPAnalysisJobResponse,
    DGCPAnalysisStatusResponse,
)

logger = logging.getLogger(__name__)

MANIFEST_KEY = "analysis_job"
REDIS_PREFIX = "jaios:dgcp:analysis"
REDIS_ACTIVE_PREFIX = "jaios:dgcp:analysis:active"
JOB_TTL_SECONDS = 86_400
ACTIVE_LOCK_TTL_SECONDS = 7_200

STAGE_LABELS: dict[str, str] = {
    "preparing": "Preparando",
    "reading_documents": "Leyendo documentos",
    "hermes": "Análisis Hermes",
    "checklist": "Generando checklist",
    "expediente": "Actualizando expediente",
    "completed": "Completado",
    "error": "Error",
}

STAGE_PROGRESS: dict[str, int] = {
    "preparing": 5,
    "reading_documents": 20,
    "hermes": 45,
    "checklist": 70,
    "expediente": 90,
    "completed": 100,
    "error": 0,
}

ProgressCallback = Callable[[str, str | None, int | None], Awaitable[None]]


class DGCPAnalysisAlreadyRunningError(ValueError):
    """Ya hay un análisis en curso para esta oportunidad."""

    def __init__(self, job_id: uuid.UUID):
        self.job_id = job_id
        super().__init__("analysis_already_running")


class DGCPAnalysisJobService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    @staticmethod
    def _redis_job_key(tenant_id: uuid.UUID, opportunity_id: uuid.UUID, job_id: uuid.UUID) -> str:
        return f"{REDIS_PREFIX}:{tenant_id}:{opportunity_id}:{job_id}"

    @staticmethod
    def _redis_active_key(tenant_id: uuid.UUID, opportunity_id: uuid.UUID) -> str:
        return f"{REDIS_ACTIVE_PREFIX}:{tenant_id}:{opportunity_id}"

    async def start_job(
        self,
        opportunity_id: uuid.UUID,
        *,
        force: bool = False,
    ) -> DGCPAnalysisJobAcceptedResponse:
        active = await self._get_active_job_id(opportunity_id)
        if active:
            existing = await self.get_job(opportunity_id, active)
            if existing and existing.status == "in_progress":
                age_s = (datetime.now(timezone.utc) - existing.updated_at).total_seconds()
                if age_s < 900:
                    raise DGCPAnalysisAlreadyRunningError(active)
                await self.fail_job(
                    opportunity_id,
                    active,
                    "Job anterior expirado — reemplazado por nuevo análisis.",
                )

        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        payload = self._job_payload(
            job_id=job_id,
            opportunity_id=opportunity_id,
            status="in_progress",
            stage="preparing",
            force=force,
            started_at=now,
            updated_at=now,
            message="Iniciando análisis…",
        )
        await self._write_job(opportunity_id, payload)
        await self._set_active_lock(opportunity_id, job_id)
        await self._persist_manifest(opportunity_id, payload)
        return DGCPAnalysisJobAcceptedResponse(
            job_id=job_id,
            opportunity_id=opportunity_id,
            stage="preparing",
        )

    async def get_job(self, opportunity_id: uuid.UUID, job_id: uuid.UUID) -> DGCPAnalysisJobResponse | None:
        raw = await self._read_job(opportunity_id, job_id)
        if not raw:
            raw = await self._read_manifest_job(opportunity_id, job_id)
        if not raw or str(raw.get("job_id")) != str(job_id):
            return None
        return self._to_response(raw)

    async def get_analysis_status(self, opportunity_id: uuid.UUID) -> DGCPAnalysisStatusResponse:
        active_id = await self._get_active_job_id(opportunity_id)
        if not active_id:
            return DGCPAnalysisStatusResponse(opportunity_id=opportunity_id, has_active_job=False, job=None)
        job = await self.get_job(opportunity_id, active_id)
        if not job or job.status != "in_progress":
            return DGCPAnalysisStatusResponse(opportunity_id=opportunity_id, has_active_job=False, job=None)
        return DGCPAnalysisStatusResponse(
            opportunity_id=opportunity_id,
            has_active_job=True,
            job=job,
        )

    async def update_progress(
        self,
        opportunity_id: uuid.UUID,
        job_id: uuid.UUID,
        stage: str,
        message: str | None = None,
        progress_pct: int | None = None,
    ) -> None:
        raw = await self._read_job(opportunity_id, job_id)
        if not raw:
            return
        now = datetime.now(timezone.utc)
        raw["stage"] = stage
        raw["status"] = "error" if stage == "error" else raw.get("status", "in_progress")
        raw["updated_at"] = now.isoformat()
        raw["progress_pct"] = progress_pct if progress_pct is not None else STAGE_PROGRESS.get(stage, raw.get("progress_pct", 0))
        if message:
            raw["message"] = message
        await self._write_job(opportunity_id, raw)

    async def complete_job(
        self,
        opportunity_id: uuid.UUID,
        job_id: uuid.UUID,
        result: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        raw = await self._read_job(opportunity_id, job_id) or {}
        raw.update({
            "job_id": str(job_id),
            "opportunity_id": str(opportunity_id),
            "status": "completed",
            "stage": "completed",
            "progress_pct": 100,
            "updated_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "message": "Análisis completado.",
            "result": result,
            "error": None,
        })
        await self._write_job(opportunity_id, raw)
        await self._persist_manifest(opportunity_id, raw)
        await self._clear_active_lock(opportunity_id, job_id)

    async def fail_job(
        self,
        opportunity_id: uuid.UUID,
        job_id: uuid.UUID,
        error: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        raw = await self._read_job(opportunity_id, job_id) or {}
        raw.update({
            "job_id": str(job_id),
            "opportunity_id": str(opportunity_id),
            "status": "error",
            "stage": "error",
            "progress_pct": STAGE_PROGRESS["error"],
            "updated_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "message": error,
            "error": error,
        })
        await self._write_job(opportunity_id, raw)
        await self._persist_manifest(opportunity_id, raw)
        await self._clear_active_lock(opportunity_id, job_id)

    def spawn_run(
        self,
        opportunity_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        force: bool,
    ) -> None:
        asyncio.create_task(
            self._run_job_background(opportunity_id, job_id, force=force),
            name=f"dgcp-analysis-{job_id}",
        )

    async def _run_job_background(
        self,
        opportunity_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        force: bool,
    ) -> None:
        from app.services.dgcp_bid_package_service import DGCPBidPackageService

        async with AsyncSessionLocal() as db:
            job_svc = DGCPAnalysisJobService(db, self.tenant_id, self.user_id)
            bid_svc = DGCPBidPackageService(db, self.tenant_id, self.user_id)

            async def progress(stage: str, message: str | None = None, pct: int | None = None) -> None:
                await job_svc.update_progress(opportunity_id, job_id, stage, message, pct)

            try:
                result = await bid_svc.analyze(
                    opportunity_id,
                    force=force,
                    progress=progress,
                )
                await job_svc.complete_job(
                    opportunity_id,
                    job_id,
                    result.model_dump(mode="json"),
                )
            except Exception as exc:
                logger.exception("DGCP analysis job %s failed", job_id)
                await job_svc.fail_job(opportunity_id, job_id, str(exc))
            finally:
                try:
                    await db.commit()
                except Exception:
                    await db.rollback()

    async def _write_job(self, opportunity_id: uuid.UUID, payload: dict[str, Any]) -> None:
        job_id = uuid.UUID(str(payload["job_id"]))
        redis = await get_redis()
        key = self._redis_job_key(self.tenant_id, opportunity_id, job_id)
        await redis.set(key, json.dumps(payload, default=str), ex=JOB_TTL_SECONDS)

    async def _read_job(self, opportunity_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any] | None:
        redis = await get_redis()
        key = self._redis_job_key(self.tenant_id, opportunity_id, job_id)
        raw = await redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def _set_active_lock(self, opportunity_id: uuid.UUID, job_id: uuid.UUID) -> None:
        redis = await get_redis()
        key = self._redis_active_key(self.tenant_id, opportunity_id)
        await redis.set(key, str(job_id), ex=ACTIVE_LOCK_TTL_SECONDS)

    async def _get_active_job_id(self, opportunity_id: uuid.UUID) -> uuid.UUID | None:
        redis = await get_redis()
        key = self._redis_active_key(self.tenant_id, opportunity_id)
        raw = await redis.get(key)
        if not raw:
            manifest = await self._read_latest_manifest_job(opportunity_id)
            if manifest and manifest.get("status") == "in_progress":
                return uuid.UUID(str(manifest["job_id"]))
            return None
        return uuid.UUID(raw)

    async def _clear_active_lock(self, opportunity_id: uuid.UUID, job_id: uuid.UUID) -> None:
        redis = await get_redis()
        key = self._redis_active_key(self.tenant_id, opportunity_id)
        current = await redis.get(key)
        if current == str(job_id):
            await redis.delete(key)

    async def _persist_manifest(self, opportunity_id: uuid.UUID, payload: dict[str, Any]) -> None:
        result = await self.db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.tenant_id == self.tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        pkg = result.scalar_one_or_none()
        if not pkg:
            pkg = DGCPBidPackage(
                tenant_id=self.tenant_id,
                opportunity_id=opportunity_id,
            )
            self.db.add(pkg)
        manifest = copy.deepcopy(pkg.manifest or {})
        manifest[MANIFEST_KEY] = payload
        pkg.manifest = manifest
        flag_modified(pkg, "manifest")
        await self.db.flush()

    async def _read_latest_manifest_job(self, opportunity_id: uuid.UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(DGCPBidPackage.manifest).where(
                DGCPBidPackage.tenant_id == self.tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        manifest = result.scalar_one_or_none() or {}
        job = manifest.get(MANIFEST_KEY)
        return job if isinstance(job, dict) else None

    async def _read_manifest_job(self, opportunity_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any] | None:
        job = await self._read_latest_manifest_job(opportunity_id)
        if job and str(job.get("job_id")) == str(job_id):
            return job
        return None

    @staticmethod
    def _job_payload(
        *,
        job_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        status: str,
        stage: str,
        force: bool,
        started_at: datetime,
        updated_at: datetime,
        message: str | None = None,
    ) -> dict[str, Any]:
        return {
            "job_id": str(job_id),
            "opportunity_id": str(opportunity_id),
            "status": status,
            "stage": stage,
            "progress_pct": STAGE_PROGRESS.get(stage, 0),
            "message": message,
            "force": force,
            "started_at": started_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "completed_at": None,
            "error": None,
            "result": None,
        }

    @staticmethod
    def _to_response(raw: dict[str, Any]) -> DGCPAnalysisJobResponse:
        stage = raw.get("stage") or "preparing"
        return DGCPAnalysisJobResponse(
            job_id=uuid.UUID(str(raw["job_id"])),
            opportunity_id=uuid.UUID(str(raw["opportunity_id"])),
            status=raw.get("status", "in_progress"),
            stage=stage,
            stage_label=STAGE_LABELS.get(stage, stage),
            progress_pct=int(raw.get("progress_pct") or STAGE_PROGRESS.get(stage, 0)),
            message=raw.get("message"),
            force=bool(raw.get("force")),
            started_at=datetime.fromisoformat(str(raw["started_at"]).replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(str(raw["updated_at"]).replace("Z", "+00:00")),
            completed_at=(
                datetime.fromisoformat(str(raw["completed_at"]).replace("Z", "+00:00"))
                if raw.get("completed_at")
                else None
            ),
            error=raw.get("error"),
            result=raw.get("result"),
        )

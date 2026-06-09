import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_schedule import DGCPSyncSchedule
from app.models.dgcp_sync_job import DGCPSyncJob
from app.config import settings
from app.services.dgcp_classifier import classify_proceso_async
from app.services.dgcp_scorer import score_proceso
from integrations.dgcp.client import DGCPClient
from integrations.dgcp.config import DGCPConfig
from integrations.dgcp.schemas import DGCPProcesoRecord


class DGCPSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = DGCPClient(
            DGCPConfig(
                base_url=settings.dgcp_api_base_url_resolved,
                api_key=settings.dgcp_api_key,
            )
        )

    async def run_sync(
        self,
        tenant_id: uuid.UUID,
        *,
        trigger: str = "manual",
        max_pages: int = 5,
        page_size: int = 50,
    ) -> DGCPSyncJob:
        job = DGCPSyncJob(tenant_id=tenant_id, trigger=trigger, status="running")
        self.db.add(job)
        await self.db.flush()

        try:
            for page in range(1, max_pages + 1):
                response = await self.client.fetch_procesos(page=page, limit=page_size)
                job.pages_synced = page
                for record in response.content:
                    created = await self._upsert_proceso(tenant_id, record, use_ai=trigger == "manual")
                    if created:
                        job.created_count += 1
                    else:
                        job.updated_count += 1
                if page >= response.pages:
                    break
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            await self._update_schedule_last_run(tenant_id)
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
        finally:
            await self.db.flush()
            await self.db.refresh(job)
        return job

    async def _upsert_proceso(
        self,
        tenant_id: uuid.UUID,
        record: DGCPProcesoRecord,
        *,
        use_ai: bool = False,
    ) -> bool:
        result = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.tenant_id == tenant_id,
                DGCPOpportunity.code == record.codigo_proceso,
            )
        )
        existing = result.scalar_one_or_none()
        classification = await classify_proceso_async(
            record, self.db, tenant_id, use_ai=use_ai
        )
        scoring = score_proceso(record, classification)
        deadline = self._extract_deadline(record)
        now = datetime.now(UTC)

        payload = record.model_dump(mode="json")
        fields = {
            "institution": record.unidad_compra,
            "title": record.titulo.strip(),
            "amount": Decimal(str(record.monto_estimado or 0)),
            "currency": record.divisa or "DOP",
            "probability": scoring.probability,
            "score": scoring.score,
            "priority": scoring.priority,
            "company": classification.company,
            "confidence_score": classification.confidence_score,
            "classification_reason": classification.classification_reason,
            "dgcp_status": record.estado_proceso,
            "modalidad": record.modalidad,
            "objeto_proceso": record.objeto_proceso,
            "deadline": deadline,
            "description": record.descripcion,
            "source_url": record.url,
            "full_info": payload,
            "raw_payload": payload,
            "risks": scoring.risks,
            "ai_recommendations": scoring.recommendations,
            "suggested_action": scoring.suggested_action,
            "justech_potential_amount": scoring.potential_amount,
            "synced_at": now,
            "ocid": f"ocds-6550wx-{record.codigo_proceso}",
        }

        if existing:
            if existing.status in ("won", "lost", "discarded"):
                existing.dgcp_status = record.estado_proceso
                existing.synced_at = now
                existing.raw_payload = payload
                return False
            for key, value in fields.items():
                if key != "status":
                    setattr(existing, key, value)
            return False

        opp = DGCPOpportunity(tenant_id=tenant_id, code=record.codigo_proceso, status="detected", **fields)
        self.db.add(opp)
        return True

    async def get_or_create_schedule(self, tenant_id: uuid.UUID) -> DGCPSyncSchedule:
        result = await self.db.execute(
            select(DGCPSyncSchedule).where(DGCPSyncSchedule.tenant_id == tenant_id)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            return schedule
        schedule = DGCPSyncSchedule(
            tenant_id=tenant_id,
            next_run_at=datetime.now(UTC) + timedelta(hours=6),
        )
        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def _update_schedule_last_run(self, tenant_id: uuid.UUID) -> None:
        schedule = await self.get_or_create_schedule(tenant_id)
        now = datetime.now(UTC)
        schedule.last_run_at = now
        schedule.next_run_at = now + timedelta(hours=schedule.interval_hours)
        await self.db.flush()

    @staticmethod
    def _extract_deadline(record: DGCPProcesoRecord) -> date:
        dt = record.fecha_fin_recepcion_ofertas or record.fecha_apertura_ofertas or record.fecha_publicacion
        if dt:
            return dt.date() if hasattr(dt, "date") else dt
        return date.today() + timedelta(days=30)

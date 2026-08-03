"""Agentes autónomos JAIOS — DGCP, Comercial, Documental, Compras, Ejecutivo."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from agents.core.base_agent import BaseAgent
from agents.core.context import AgentContext
from agents.registry import AgentRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.services.commercial_memory_service import CommercialMemoryService
from app.services.dgcp_intelligence.service import DGCPIntelligenceService
from app.services.dgcp_sync_service import DGCPSyncService
from app.services.document_pending_service import DocumentPendingService

logger = logging.getLogger(__name__)


class BaseJAIOSAgent(BaseAgent):
    """Base para agentes JAIOS."""

    async def validate_input(self, input_data: dict) -> bool:
        return True


@AgentRegistry.register
class DGCPMonitorAgent(BaseJAIOSAgent):
    name = "dgcp"
    description = "Monitorea oportunidades DGCP y genera análisis Premium+"

    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            sync = DGCPSyncService(db)
            job = await sync.run_sync(context.tenant_id, trigger="agent_dgcp", max_pages=3, page_size=50)
            intel = DGCPIntelligenceService(db, context.tenant_id)
            analysis = await intel.analyze_tenant_opportunities(limit=30)
            await db.commit()
            return {
                "sync": {"created": job.created_count, "updated": job.updated_count, "status": job.status},
                "intelligence": analysis,
            }


@AgentRegistry.register
class DocumentalAgent(BaseJAIOSAgent):
    name = "documental"
    description = "Valida vigencia documental y pendientes"

    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            pending = DocumentPendingService(db, context.tenant_id)
            scan = await pending.scan_and_upsert()
            resolved = await pending.auto_resolve()
            await db.commit()
            return {"scan": scan, "auto_resolved": resolved}


@AgentRegistry.register
class CommercialAgent(BaseJAIOSAgent):
    name = "comercial"
    description = "Memoria comercial y cotizaciones"

    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            memory = CommercialMemoryService(db, context.tenant_id)
            sample = await memory.query("laptop", limit=3)
            return {"memory_sample": sample}


@AgentRegistry.register
class PurchasingAgent(BaseJAIOSAgent):
    name = "compras"
    description = "Sugiere proveedores vía listas indexadas"

    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            intel = DGCPIntelligenceService(db, context.tenant_id)
            result = await intel.analyze_tenant_opportunities(limit=10)
            return {"suppliers_analysis": result}


@AgentRegistry.register
class ExecutiveAgent(BaseJAIOSAgent):
    name = "ejecutivo"
    description = "Briefing ejecutivo consolidado"

    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        return {"briefing": "Briefing ejecutivo programado — use Copilot en UI para detalle."}


async def run_agent(name: str, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None) -> dict[str, Any]:
    agent_cls = AgentRegistry.get(name)
    if not agent_cls:
        raise ValueError(f"Agente desconocido: {name}")
    ctx = AgentContext(tenant_id=tenant_id, user_id=user_id)
    agent = agent_cls()
    started = datetime.now(UTC)
    try:
        result = await agent.run({}, ctx)
        return {"agent": name, "status": "completed", "summary": result, "ran_at": started.isoformat()}
    except Exception as exc:
        logger.exception("Agent %s failed tenant=%s", name, tenant_id)
        return {"agent": name, "status": "failed", "summary": {"error": str(exc)}, "ran_at": started.isoformat()}


async def run_all_agents_for_tenant(tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None) -> list[dict]:
    names = ["dgcp", "documental", "comercial", "compras"]
    results = []
    for name in names:
        results.append(await run_agent(name, tenant_id, user_id=user_id))
    return results


async def run_agents_all_tenants() -> list[dict]:
    async with AsyncSessionLocal() as db:
        tenants = list((await db.execute(select(Tenant))).scalars().all())
    out: list[dict] = []
    for tenant in tenants:
        out.extend(await run_all_agents_for_tenant(tenant.id))
    return out

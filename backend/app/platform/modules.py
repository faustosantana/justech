"""Registro oficial de módulos JAIOS y grafo de dependencias."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Literal

ModuleStatus = Literal["delivered", "active", "planned", "future"]


class ModulePhase(IntEnum):
    CORE = 1
    DGCP = 2
    ODOO = 3
    M365 = 4
    WORK = 5
    SEARCH_DOCS = 6
    MEMORY_AGENTS = 7


@dataclass(frozen=True)
class JAIOSModule:
    id: str
    name: str
    phase: ModulePhase
    status: ModuleStatus
    description: str
    depends_on: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    integration_key: str | None = None
    frontend_route: str | None = None


_MODULES: tuple[JAIOSModule, ...] = (
    JAIOSModule(
        id="lottery",
        name="Resultados de Loterías",
        phase=ModulePhase.SEARCH_DOCS,
        status="active",
        description="Histórico de sorteos, comparación, estadísticas y Lotería IA",
        depends_on=("core",),
        provides=("lottery_results", "lottery_statistics", "lottery_chat"),
        frontend_route="/lottery",
    ),

    JAIOSModule(
        id="core",
        name="Core Platform",
        phase=ModulePhase.CORE,
        status="delivered",
        description="Auth, multi-tenant, gateway, LLM router",
        provides=("auth", "tenancy", "audit", "llm"),
    ),
    JAIOSModule(
        id="dgcp",
        name="DGCP Intelligence Center",
        phase=ModulePhase.DGCP,
        status="delivered",
        description="Oportunidades DGCP, sync, clasificación, scoring",
        depends_on=("core",),
        provides=("dgcp_opportunities", "dgcp_classification", "dgcp_sync"),
        integration_key="dgcp",
        frontend_route="/dgcp",
    ),
    JAIOSModule(
        id="odoo",
        name="Odoo Intelligence Center",
        phase=ModulePhase.ODOO,
        status="active",
        description="Consulta segura Odoo: clientes, ventas, facturas, CRM (solo lectura)",
        depends_on=("core",),
        provides=("odoo_customers", "odoo_sales", "odoo_invoices", "odoo_crm"),
        integration_key="odoo",
        frontend_route="/odoo",
    ),
    JAIOSModule(
        id="m365",
        name="Microsoft 365 Intelligence Center",
        phase=ModulePhase.M365,
        status="active",
        description="Outlook, Teams, SharePoint, OneDrive — estructura base (sin Graph real)",
        depends_on=("core",),
        provides=("m365_mail", "m365_calendar", "m365_files", "m365_teams"),
        integration_key="microsoft365",
        frontend_route="/m365",
    ),
    JAIOSModule(
        id="tasks",
        name="Tasks / Pendientes / Asignaciones Center",
        phase=ModulePhase.WORK,
        status="active",
        description="Tareas, pendientes y asignaciones por usuario y equipo",
        depends_on=("core", "odoo"),
        provides=("tasks", "assignments", "pendientes"),
        frontend_route="/tasks",
    ),
    JAIOSModule(
        id="notifications",
        name="Notificaciones",
        phase=ModulePhase.WORK,
        status="active",
        description="Alertas, recordatorios y eventos entre módulos",
        depends_on=("core",),
        provides=("notifications", "alerts", "reminders"),
    ),
    JAIOSModule(
        id="work_hub",
        name="Work Hub",
        phase=ModulePhase.WORK,
        status="active",
        description="Vista unificada de trabajo: tareas, pendientes, prioridades",
        depends_on=("core", "tasks", "notifications"),
        provides=("work_dashboard", "work_queue"),
        frontend_route="/work",
    ),
    JAIOSModule(
        id="enterprise_search",
        name="Enterprise Search",
        phase=ModulePhase.SEARCH_DOCS,
        status="active",
        description="Búsqueda transversal Odoo, DGCP, tareas y notificaciones (estructurada, read-only)",
        depends_on=("core", "odoo", "dgcp", "m365"),
        provides=("search", "unified_query"),
        frontend_route="/search",
    ),
    JAIOSModule(
        id="search_acceleration",
        name="Search Acceleration Engine",
        phase=ModulePhase.SEARCH_DOCS,
        status="active",
        description="Cache Redis, índice search_index, analytics — reduce latencia (sin Qdrant aún)",
        depends_on=("core", "enterprise_search"),
        provides=("search_cache", "search_index", "search_analytics", "semantic_search_stub"),
    ),
    JAIOSModule(
        id="document_repository",
        name="Enterprise Document Repository",
        phase=ModulePhase.SEARCH_DOCS,
        status="active",
        description="Repositorio documental unificado: PDF, Word, Excel, expedientes",
        depends_on=("core", "dgcp", "m365"),
        provides=("documents", "expedientes", "document_versions"),
        frontend_route="/documents",
    ),
    JAIOSModule(
        id="supplier_intelligence",
        name="Supplier Intelligence",
        phase=ModulePhase.SEARCH_DOCS,
        status="future",
        description="Proveedores, SKUs, MPN, disponibilidad, condiciones comerciales",
        depends_on=("core", "odoo"),
        provides=("supplier_catalog", "supplier_quotes"),
        frontend_route="/suppliers",
    ),
    JAIOSModule(
        id="price_intelligence",
        name="Price Intelligence",
        phase=ModulePhase.SEARCH_DOCS,
        status="active",
        description="Comparación de costos, márgenes, fuentes externas y recomendaciones",
        depends_on=("core", "odoo", "supplier_intelligence"),
        provides=("price_comparison", "margin_analysis", "buy_recommendations"),
        frontend_route="/prices",
    ),
    JAIOSModule(
        id="hermes_memory",
        name="Hermes Enterprise Memory",
        phase=ModulePhase.MEMORY_AGENTS,
        status="future",
        description="Memoria empresarial persistente: RAG, contexto histórico, Qdrant",
        depends_on=("core", "enterprise_search"),
        provides=("memory", "context_retrieval", "rag"),
    ),
    JAIOSModule(
        id="multi_agent",
        name="Multi-Agent Operations",
        phase=ModulePhase.MEMORY_AGENTS,
        status="future",
        description="Orquestación de agentes sobre todos los centros de inteligencia",
        depends_on=(
            "core",
            "dgcp",
            "odoo",
            "m365",
            "work_hub",
            "enterprise_search",
            "hermes_memory",
        ),
        provides=("agents", "orchestration", "automations"),
        frontend_route="/agents",
    ),
)

_MODULE_MAP: dict[str, JAIOSModule] = {m.id: m for m in _MODULES}


def list_modules() -> list[JAIOSModule]:
    return list(_MODULES)


def get_module(module_id: str) -> JAIOSModule | None:
    return _MODULE_MAP.get(module_id)


def get_modules_by_phase(phase: ModulePhase) -> list[JAIOSModule]:
    return [m for m in _MODULES if m.phase == phase]


def get_roadmap() -> list[dict]:
    """Serialización del roadmap para APIs o herramientas internas."""
    return [
        {
            "id": m.id,
            "name": m.name,
            "phase": int(m.phase),
            "status": m.status,
            "description": m.description,
            "depends_on": list(m.depends_on),
            "provides": list(m.provides),
            "integration_key": m.integration_key,
            "frontend_route": m.frontend_route,
        }
        for m in _MODULES
    ]


def validate_dependencies() -> list[str]:
    """Valida integridad del grafo; útil en tests de arquitectura."""
    errors: list[str] = []
    known = set(_MODULE_MAP)
    for module in _MODULES:
        for dep in module.depends_on:
            if dep not in known:
                errors.append(f"{module.id}: dependencia desconocida '{dep}'")
    return errors


# Clave JSONB en tenants.settings para habilitación futura por módulo
TENANT_SETTINGS_ENABLED_MODULES_KEY = "enabled_modules"

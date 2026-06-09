"""Formato estructurado unificado para respuestas del Assistant empresarial."""

from __future__ import annotations

from app.schemas.assistant import AssistantLink


def build_business_answer(
    *,
    intent: str,
    source: str,
    summary: str,
    metrics: list[dict[str, str]] | None = None,
    tables: list[dict] | None = None,
    warnings: list[str] | None = None,
    links: list[dict[str, str]] | None = None,
    actions: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "type": "business_answer",
        "intent": intent,
        "source": source,
        "summary": summary,
        "metrics": metrics or [],
        "tables": tables or [],
        "warnings": warnings or [],
        "links": links or [],
        "actions": actions or [],
    }


def from_sales_report(report: dict, *, intent: str, source: str = "odoo") -> dict:
    return build_business_answer(
        intent=intent,
        source=source,
        summary=report.get("summary", ""),
        metrics=report.get("metrics", []),
        tables=report.get("tables", []),
        warnings=report.get("warnings", []),
        actions=report.get("actions", []),
    )


def links_to_dict(links: list[AssistantLink]) -> list[dict[str, str]]:
    return [{"label": lnk.label, "url": lnk.url, "type": lnk.type} for lnk in links]


def not_found_summary(entity: str, source: str, *, kind: str = "registros") -> str:
    source_labels = {
        "odoo": "Odoo",
        "dgcp": "DGCP",
        "tasks": "Tasks",
        "enterprise_search": "las fuentes disponibles",
    }
    label = source_labels.get(source, source)
    if kind == "ventas":
        return f"No encontré ventas de {entity} en el histórico disponible de {label}."
    if kind == "compras":
        return f"No encontré compras de {entity} en el histórico disponible de {label}."
    if kind == "licitaciones":
        return f"No encontré licitaciones relacionadas con {entity} en {label}."
    if kind == "tareas":
        return f"No encontré tareas asignadas a {entity}."
    return f"No encontré registros relacionados con {entity} en {label}."

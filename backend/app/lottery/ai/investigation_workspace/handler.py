"""Execute Investigation Workspace asset actions (no Huawei)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.lottery.ai.investigation_workspace.export_xlsx import export_asset_xlsx
from app.lottery.ai.investigation_workspace.materialize import (
    materialize_same_day_from_query,
)
from app.lottery.ai.investigation_workspace.operations import (
    set_filters,
    set_pagination,
    set_sort,
)
from app.lottery.ai.investigation_workspace.response import (
    format_export_reply,
    format_table_reply,
)
from app.lottery.ai.investigation_workspace.schemas import (
    AssetFilters,
    AssetPagination,
    AssetSort,
    InvestigationAsset,
    WorkspaceActionDecision,
)
from app.lottery.ai.investigation_workspace.store import get_active_asset, save_asset


def _subjects_from(state: Any, investigation: Any | None) -> list[str]:
    subs = list(
        (getattr(investigation, "subjects", None) if investigation else None)
        or getattr(state, "active_pair", None)
        or getattr(state, "active_numbers", None)
        or []
    )
    return [str(s).strip().zfill(2) if str(s).strip().isdigit() else str(s).strip() for s in subs if str(s).strip()][:2]


async def ensure_same_day_asset(
    state: Any,
    *,
    query_service: Any,
    investigation: Any | None = None,
    conversation_id: str | None = None,
) -> InvestigationAsset:
    from app.lottery.ai.conversational_integrity import asset_matches_current

    subjects = _subjects_from(state, investigation)
    relation = (
        (getattr(investigation, "relation", None) if investigation else None)
        or getattr(state, "active_relation", None)
        or "same_day"
    )
    existing = get_active_asset(state)
    # NO REUSE unless subjects + relation (+ scope) match the current intent.
    if (
        existing
        and not existing.is_expired()
        and existing.source_rows
        and asset_matches_current(
            existing,
            subjects=subjects,
            relation=relation,
            scope=getattr(existing, "scope", None) or "official_seven",
        )
    ):
        return existing
    if len(subjects) < 2:
        raise ValueError("Se necesitan dos números activos para materializar la tabla.")
    inv_id = getattr(investigation, "investigation_id", None) if investigation else None
    asset = await materialize_same_day_from_query(
        query_service,
        subjects=subjects,
        lotteries=None,
        investigation_id=inv_id,
        conversation_id=conversation_id,
        limit_dates=500,
    )
    return save_asset(state, asset)


async def execute_workspace_action(
    state: Any,
    decision: WorkspaceActionDecision,
    *,
    query_service: Any,
    investigation: Any | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Apply show/filter/sort/export; returns reply + structured payload."""
    action = decision.action
    asset = get_active_asset(state)

    if action in {
        "show_results",
        "show_dates",
        "filter_results",
        "sort_results",
        "export_results",
        "paginate_results",
    }:
        from app.lottery.ai.conversational_integrity import asset_matches_current

        want_subjects = _subjects_from(state, investigation)
        want_relation = (
            (getattr(investigation, "relation", None) if investigation else None)
            or getattr(state, "active_relation", None)
            or "same_day"
        )
        reusable = (
            asset is not None
            and not asset.is_expired()
            and bool(asset.source_rows)
            and asset_matches_current(
                asset,
                subjects=want_subjects,
                relation=want_relation,
                scope=getattr(asset, "scope", None) or "official_seven",
            )
        )
        if not reusable:
            asset = await ensure_same_day_asset(
                state,
                query_service=query_service,
                investigation=investigation,
                conversation_id=conversation_id,
            )
        else:
            # Re-bind active (same subjects/relation/scope)
            save_asset(state, asset)

    if asset is None:
        return {
            "content": (
                "No hay una tabla de investigación activa. "
                "Pregunta primero por dos números (p. ej. 35 y 14) y luego pide ver resultados."
            ),
            "structured_content": None,
            "tool_payload": {"workspace_action": decision.to_trace(), "ok": False},
        }

    if action == "filter_results":
        filters = (
            AssetFilters()
            if decision.reason_code == "clear_filters"
            else decision.filters
        )
        asset = set_filters(asset, filters)
        save_asset(state, asset)
        intro = (
            f"Filtré la tabla"
            + (f" a «{decision.filters.lottery}»" if decision.filters.lottery else "")
            + f": {asset.row_count} fila(s)."
        )
        return _table_result(asset, decision, intro=intro)

    if action == "sort_results":
        sort = decision.sort or AssetSort(field="fecha", direction="desc")
        asset = set_sort(asset, sort)
        save_asset(state, asset)
        intro = (
            f"Ordené por {sort.field} ({sort.direction}). "
            f"{asset.row_count} fila(s)."
        )
        return _table_result(asset, decision, intro=intro)

    if action == "paginate_results":
        pag = decision.pagination or AssetPagination()
        if decision.reason_code == "paginate_first_n":
            asset.pagination.page_size = max(1, min(int(pag.page_size or 20), 100))
            asset.pagination.page = 1
            from app.lottery.ai.investigation_workspace.operations import recompute_view

            asset = recompute_view(asset)
        elif decision.reason_code == "paginate_next":
            # advance page or enlarge page_size when "próximos N"
            if pag.page_size and pag.page_size != asset.pagination.page_size:
                asset.pagination.page_size = pag.page_size
                asset.pagination.page = 1
            else:
                asset.pagination.page = asset.pagination.page + 1
            from app.lottery.ai.investigation_workspace.operations import recompute_view

            asset = recompute_view(asset)
        else:
            asset = set_pagination(asset, pag)
        save_asset(state, asset)
        return _table_result(asset, decision)

    if action == "export_results":
        path, filename, _content = export_asset_xlsx(asset)
        storage_name = path.name
        download_url = f"/api/v1/lottery/workspace/exports/{storage_name}/download"
        asset.export_path = str(path)
        asset.export_filename = filename
        asset.download_url = download_url
        asset.asset_type = "result_table"  # keep table type; export is side effect
        save_asset(state, asset)
        return {
            "content": format_export_reply(asset),
            "structured_content": {
                "type": "investigation_workspace_export",
                "asset": asset.ui_payload(),
                "download_url": download_url,
                "filename": filename,
                "storage_name": storage_name,
                "row_count": asset.row_count,
            },
            "tool_payload": {
                "workspace_action": decision.to_trace(),
                "ok": True,
                "asset_id": asset.asset_id,
                "download_url": download_url,
                "export_path": str(path),
                "filename": filename,
            },
        }

    if action == "summarize_asset":
        # MVP: local summary only (no Huawei)
        intro = (
            f"Resumen de «{asset.title}»: {asset.row_count} fila(s) "
            f"(fuente {len(asset.source_rows)}). "
            f"Filtros: {asset.filters.model_dump(exclude_none=True) or 'ninguno'}. "
            f"Orden: {asset.sort.model_dump()}."
        )
        return _table_result(asset, decision, intro=intro)

    # show_dates / show_results / open_asset default
    if action == "show_dates":
        intro = (
            f"Fechas de coincidencia same-day ({' y '.join(asset.subjects)}): "
            f"{asset.row_count} fila(s)."
        )
    else:
        intro = (
            f"Tabla de coincidencias same-day ({' y '.join(asset.subjects)}): "
            f"{asset.row_count} fila(s)."
        )
    return _table_result(asset, decision, intro=intro)


def _table_result(
    asset: InvestigationAsset,
    decision: WorkspaceActionDecision,
    *,
    intro: str | None = None,
) -> dict[str, Any]:
    return {
        "content": format_table_reply(asset, intro=intro),
        "structured_content": {
            "type": "investigation_workspace_table",
            "asset": asset.ui_payload(),
        },
        "tool_payload": {
            "workspace_action": decision.to_trace(),
            "ok": True,
            "asset_id": asset.asset_id,
            "row_count": asset.row_count,
        },
    }


def resolve_export_file(storage_name: str) -> Path | None:
    """Safe resolve of workspace export under lottery_exports_path."""
    from app.config import settings

    name = Path(storage_name).name
    if not name.startswith("ws_") or not name.endswith(".xlsx"):
        return None
    if ".." in name or "/" in storage_name or "\\" in storage_name:
        return None
    root = Path(settings.lottery_exports_path).resolve()
    path = (root / name).resolve()
    if not str(path).startswith(str(root)):
        return None
    if not path.is_file():
        return None
    return path

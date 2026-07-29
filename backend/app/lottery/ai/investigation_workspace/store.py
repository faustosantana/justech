"""Workspace store helpers on ConversationState / session context."""

from __future__ import annotations

from typing import Any

from app.lottery.ai.investigation_workspace.schemas import InvestigationAsset


def get_assets_map(state: Any) -> dict[str, dict[str, Any]]:
    raw = getattr(state, "workspace_assets", None)
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def set_assets_map(state: Any, assets: dict[str, dict[str, Any]]) -> None:
    state.workspace_assets = assets


def get_active_asset(state: Any) -> InvestigationAsset | None:
    aid = getattr(state, "active_asset_id", None)
    assets = get_assets_map(state)
    if aid and aid in assets:
        return InvestigationAsset.from_store(assets.get(aid))
    # fallback: latest
    if assets:
        # pick most recently updated
        best = None
        best_ts = ""
        for data in assets.values():
            ts = str((data or {}).get("updated_at") or "")
            if ts >= best_ts:
                best_ts = ts
                best = data
        return InvestigationAsset.from_store(best)
    return None


def clear_assets(state: Any) -> None:
    """Drop operable tables when starting an explicit new investigation."""
    state.workspace_assets = {}
    state.active_asset_id = None


def save_asset(state: Any, asset: InvestigationAsset) -> InvestigationAsset:
    asset.touch()
    assets = get_assets_map(state)
    assets[asset.asset_id] = asset.to_store()
    set_assets_map(state, assets)
    state.active_asset_id = asset.asset_id
    return asset

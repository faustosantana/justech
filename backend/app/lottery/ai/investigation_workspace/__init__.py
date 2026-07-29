"""Investigation Workspace 1.0 — operable assets (show/filter/sort/export).

Does NOT modify Mathematical Motor, Prompt Maestro, cert200, or Huawei credentials.
"""

from __future__ import annotations

from app.lottery.ai.investigation_workspace.export_xlsx import export_asset_xlsx
from app.lottery.ai.investigation_workspace.handler import (
    execute_workspace_action,
    resolve_export_file,
)
from app.lottery.ai.investigation_workspace.materialize import (
    materialize_same_day_from_query,
    materialize_same_day_table,
)
from app.lottery.ai.investigation_workspace.operations import (
    recompute_view,
    set_filters,
    set_pagination,
    set_sort,
)
from app.lottery.ai.investigation_workspace.response import (
    format_export_reply,
    format_table_reply,
)
from app.lottery.ai.investigation_workspace.schemas import (
    InvestigationAsset,
    WorkspaceActionDecision,
)
from app.lottery.ai.investigation_workspace.speech_acts import WorkspaceSpeechActDetector
from app.lottery.ai.investigation_workspace.store import (
    get_active_asset,
    save_asset,
)

__all__ = [
    "InvestigationAsset",
    "WorkspaceActionDecision",
    "WorkspaceSpeechActDetector",
    "execute_workspace_action",
    "export_asset_xlsx",
    "format_export_reply",
    "format_table_reply",
    "get_active_asset",
    "materialize_same_day_from_query",
    "materialize_same_day_table",
    "recompute_view",
    "resolve_export_file",
    "save_asset",
    "set_filters",
    "set_pagination",
    "set_sort",
]

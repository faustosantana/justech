"""Optional DB loader for active Reasoning Studio versions."""

from __future__ import annotations

from typing import Any

from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7 import REASONING_STUDIO_NAME


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "version_id": str(row.id),
        "version": row.version,
        "semantic_version": row.version,
        "status": row.status,
        "body": row.body,
        "blocks": row.blocks or {},
        "checksum": row.checksum,
        "name": getattr(row, "name", None),
        "tags": getattr(row, "tags", None),
    }


async def load_active_reasoning_studio_async(db: Any) -> dict[str, Any] | None:
    """Async load pinned or active Reasoning Studio version for runtime."""
    from sqlalchemy import select

    from app.config import settings
    from app.models.lottery import LotteryAiPromptVersion

    if db is None:
        return None

    pinned = str(getattr(settings, "lottery_analyst_prompt_studio_version_id", "") or "").strip()
    try:
        if pinned:
            try:
                import uuid as _uuid

                pid = _uuid.UUID(pinned)
            except ValueError:
                return None
            row = await db.get(LotteryAiPromptVersion, pid)
            return _row_to_dict(row) if row else None

        q = (
            select(LotteryAiPromptVersion)
            .where(LotteryAiPromptVersion.status == "active")
            .where(LotteryAiPromptVersion.name == REASONING_STUDIO_NAME)
            .limit(1)
        )
        row = (await db.execute(q)).scalar_one_or_none()
        if row is None:
            q2 = (
                select(LotteryAiPromptVersion)
                .where(LotteryAiPromptVersion.status == "active")
                .limit(8)
            )
            for cand in (await db.execute(q2)).scalars().all():
                tags = cand.tags or []
                if isinstance(tags, list) and "reasoning_runtime" in tags:
                    row = cand
                    break
        return _row_to_dict(row) if row else None
    except Exception:  # noqa: BLE001
        return None


def load_active_reasoning_studio_row(db: Any | None = None) -> dict[str, Any] | None:
    """Sync helper (tests / scripts). Prefer async loader in request path."""
    from app.config import settings

    pinned = str(getattr(settings, "lottery_analyst_prompt_studio_version_id", "") or "").strip()
    if db is None:
        return None

    try:
        from sqlalchemy import select

        from app.models.lottery import LotteryAiPromptVersion

        if pinned:
            row = db.get(LotteryAiPromptVersion, pinned) if hasattr(db, "get") else None
            if row is None:
                q = select(LotteryAiPromptVersion).where(LotteryAiPromptVersion.id == pinned)
                row = db.execute(q).scalar_one_or_none()
        else:
            q = (
                select(LotteryAiPromptVersion)
                .where(LotteryAiPromptVersion.status == "active")
                .where(LotteryAiPromptVersion.name == REASONING_STUDIO_NAME)
                .limit(1)
            )
            row = db.execute(q).scalar_one_or_none()
            if row is None:
                q2 = (
                    select(LotteryAiPromptVersion)
                    .where(LotteryAiPromptVersion.status == "active")
                    .limit(5)
                )
                for cand in db.execute(q2).scalars().all():
                    tags = cand.tags or []
                    if isinstance(tags, list) and "reasoning_runtime" in tags:
                        row = cand
                        break
        if row is None:
            return None
        return _row_to_dict(row)
    except Exception:  # noqa: BLE001
        return None

"""Validación de acceso por empresa en preguntas del Assistant."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.services.company_scope_filter import CompanyScopeFilter

COMPANY_PHRASES: list[tuple[str, str]] = [
    ("just office", "Just Office SRL"),
    ("justech", "Justech SRL"),
    ("plugsafe", "PlugSafe SRL"),
    ("plug safe", "PlugSafe SRL"),
    ("omni solutions", "Omni Solutions SRL"),
    ("omni", "Omni Solutions SRL"),
]


async def assistant_company_access_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    question: str,
) -> str | None:
    lowered = question.lower()
    scope_filter = CompanyScopeFilter(db, tenant_id, user_id)
    for phrase, label in COMPANY_PHRASES:
        if phrase not in lowered:
            continue
        if phrase == "justech" and "just office" in lowered:
            continue
        if phrase == "omni" and "omni solutions" in lowered:
            continue
        try:
            await scope_filter.assert_company_name_allowed(label)
        except AuthorizationError as exc:
            return exc.message
    return None

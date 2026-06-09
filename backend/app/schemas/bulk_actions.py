"""Schemas — acciones masivas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class BulkActionResult(BaseModel):
    action: str
    affected: int
    message: str
    export_csv: str | None = None


class DocumentBulkRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)
    action: str = Field(pattern="^(archive|mark_review|export|create_task)$")


class TaskBulkRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)
    action: str = Field(pattern="^(status|priority|assign|archive)$")
    status: str | None = None
    priority: str | None = None
    assigned_to_id: uuid.UUID | None = None


class DraftBulkRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)
    action: str = Field(pattern="^(discard|export|status|assign|create_task)$")
    status: str | None = None
    assigned_user_id: uuid.UUID | None = None

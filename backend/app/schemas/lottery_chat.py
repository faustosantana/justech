"""Schemas API chat Lotería IA."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str | None = None


class ChatSessionRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str | None
    context: dict[str, Any] = Field(default_factory=dict)
    last_message_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    tool_name: str | None = None
    tool_payload: dict[str, Any] | None = None
    created_at: datetime | None = None


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
    total: int


class ChatSendResponse(BaseModel):
    message: dict[str, Any]
    user_message_id: str
    context: dict[str, Any]
    active_context: dict[str, Any] | None = None
    suggestions: list[str] = Field(default_factory=list)
    synthesis_fallback: bool = False
    latency_ms: int = 0
    runtime_trace: dict[str, Any] | None = None
    research: dict[str, Any] | None = None
    # Present only when LOTTERY_FORENSIC_TRACE_ENABLED=true (not shown in normal UI)
    forensic: dict[str, Any] | None = None


class SavedQueryResponse(BaseModel):
    id: UUID
    name: str
    payload: dict[str, Any]
    description: str | None = None
    query_type: str | None = None
    is_favorite: bool = False
    run_count: int = 0
    last_run_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SavedQueryListResponse(BaseModel):
    items: list[SavedQueryResponse]
    total: int


class SavedQueryRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)

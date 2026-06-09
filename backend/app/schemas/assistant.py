from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    current_module: str | None = None
    current_company_context: int | None = None
    current_record_id: str | None = None
    record_type: str | None = None
    conversation_id: str | None = None
    debug_context: bool = False


class AssistantLink(BaseModel):
    label: str
    url: str
    type: str


class AssistantCard(BaseModel):
    title: str
    subtitle: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    link: str | None = None


class AssistantAction(BaseModel):
    label: str
    type: str
    url: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None


class AssistantQueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    query_type: str = "general"
    cards: list[AssistantCard] = Field(default_factory=list)
    links: list[AssistantLink] = Field(default_factory=list)
    actions: list[AssistantAction] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    structured_data: dict[str, Any] | None = None
    read_only_notice: str | None = None
    resolved_question: str | None = None
    conversation_context: dict[str, Any] | None = None
    was_follow_up: bool = False

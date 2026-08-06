"""Schemas — integración Hermes ↔ JAIOS."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HermesAnalysisResult(BaseModel):
    summary: str = ""
    detected_type: str = "unknown"
    priority: str = "media"
    recommendation: str = "revisar"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    items_detected: list[dict[str, Any]] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    risks: list[dict[str, str]] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HermesTenderContext(BaseModel):
    process_code: str = ""
    title: str = ""
    institution: str = ""
    description: str | None = None
    objeto_proceso: str | None = None
    amount: str | None = None
    deadline: str | None = None
    documents_text: str | None = None
    requirements: list[dict[str, Any]] = Field(default_factory=list)


class HermesEmailRfqContext(BaseModel):
    subject: str = ""
    body: str = ""
    from_address: str | None = None


class HermesKnowledgeContext(BaseModel):
    query: str
    hits: list[dict[str, Any]] = Field(default_factory=list)
    limit: int = 10

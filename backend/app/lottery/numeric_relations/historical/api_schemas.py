"""Schemas Pydantic — APIs históricas NR (J-3). `/analyze` v1 intacto."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode, SessionBucket


class LotteryScopeBody(BaseModel):
    primary_lottery_ids: list[UUID]
    confirming_lottery_ids: list[UUID] | None = None
    follow_up_lottery_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def defaults_visible(self) -> "LotteryScopeBody":
        # Default explícito: confirming = primary; follow-up = primary
        if self.confirming_lottery_ids is None:
            self.confirming_lottery_ids = list(self.primary_lottery_ids)
        if self.follow_up_lottery_ids is None:
            self.follow_up_lottery_ids = list(self.primary_lottery_ids)
        if not self.primary_lottery_ids:
            raise ValueError("primary_lottery_ids required")
        return self


class ConfirmationWindowBody(BaseModel):
    mode: ConfirmationWindowMode = ConfirmationWindowMode.SAME_DRAW
    timezone: str = "America/Santo_Domingo"
    hours_after: int | None = None
    next_k: int | None = None
    session: SessionBucket | None = None


class HistoricalSearchBody(BaseModel):
    observed_number: int = Field(..., ge=1, le=100)
    scope: LotteryScopeBody
    confirmation_window: ConfirmationWindowBody = Field(default_factory=ConfirmationWindowBody)
    date_from: date | None = None
    date_to: date | None = None
    candidate: int | None = Field(None, ge=1, le=100)
    confirmer: int | None = Field(None, ge=1, le=100)
    max_horizon: int = Field(10, ge=1, le=50)
    include_pairs_triples: bool = True
    min_sample: int | None = Field(None, ge=0)


class PatternDetailBody(BaseModel):
    observed_number: int = Field(..., ge=1, le=100)
    candidate: int = Field(..., ge=1, le=100)
    confirmer: int | None = Field(None, ge=1, le=100)
    confirmers: list[int] | None = None  # combination set
    scope: LotteryScopeBody
    confirmation_window: ConfirmationWindowBody = Field(default_factory=ConfirmationWindowBody)
    date_from: date | None = None
    date_to: date | None = None
    max_horizon: int = Field(10, ge=1, le=50)


class CompareBody(BaseModel):
    observed_number: int = Field(..., ge=1, le=100)
    scope: LotteryScopeBody
    confirmation_window: ConfirmationWindowBody = Field(default_factory=ConfirmationWindowBody)
    date_from: date | None = None
    date_to: date | None = None
    candidates: list[int] = Field(default_factory=list)
    confirmers: list[int] = Field(default_factory=list)
    compare_mode: Literal["candidates", "confirmers", "combinations", "lotteries"] = "candidates"
    max_horizon: int = Field(10, ge=1, le=50)

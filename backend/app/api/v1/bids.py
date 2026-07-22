"""Versioned Bids API — discovery in JAIOS, management handoff to Odoo Bid Center."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.bid_contract import (
    AnalysisRequest,
    BidOpportunityV1,
    InterestRequest,
    InterestResponse,
    InterestStatus,
    StatusUpdateRequest,
    WorkflowStatus,
    compute_content_hash,
)
from app.services.bid_center import get_bid_center_client
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bids", tags=["bids"])

# In-memory analysis cache for DEV when no async workers
_ANALYSIS: dict[str, dict[str, Any]] = {}
_STATUS_OVERRIDES: dict[str, dict[str, Any]] = {}


class BidListResponse(BaseModel):
    items: list[BidOpportunityV1]
    total: int
    page: int
    page_size: int


class HealthOdooResponse(BaseModel):
    ok: bool
    status: str
    detail: dict[str, Any] | None = None


def _opp_to_contract(opp: DGCPOpportunity) -> BidOpportunityV1:
    override = _STATUS_OVERRIDES.get(str(opp.id), {})
    interest = InterestStatus_from_dgcp(opp.status)
    workflow = WorkflowStatus_from_dgcp(opp.status)
    if override.get("workflow_status"):
        workflow = WorkflowStatus(override["workflow_status"])
    if override.get("interest_status"):
        interest_val = InterestStatus(override["interest_status"])
    else:
        interest_val = interest
    payload = {
        "schema_version": "1.0.0",
        "source_system": "jaios",
        "external_id": str(opp.id),
        "jaios_tender_id": str(opp.id),
        "odoo_tender_id": override.get("odoo_tender_id"),
        "source_portal": "dgcp",
        "source_url": opp.source_url,
        "process_number": opp.code,
        "title": opp.title,
        "object": opp.objeto_proceso or opp.description,
        "institution_name": opp.institution,
        "submission_deadline": opp.deadline.isoformat() if opp.deadline else None,
        "estimated_budget": float(opp.amount or 0),
        "currency": opp.currency or "DOP",
        "category": opp.company,
        "procurement_method": opp.modalidad,
        "summary": (opp.description or "")[:2000],
        "compatibility_score": float(opp.score or opp.confidence_score or 0),
        "compatibility_reasons": list(opp.ai_recommendations or [])[:10]
        if isinstance(opp.ai_recommendations, list)
        else [],
        "risk_level": "high" if (opp.priority or "") == "high" else "medium",
        "detected_requirements": [],
        "documents": [],
        "source_status": opp.dgcp_status,
        "workflow_status": workflow,
        "interest_status": interest_val,
        "sync_version": 1,
        "created_at": getattr(opp, "created_at", None),
        "updated_at": getattr(opp, "updated_at", None),
        "last_synced_at": override.get("last_synced_at"),
    }
    payload["content_hash"] = compute_content_hash(payload)
    return BidOpportunityV1.model_validate(payload)


def InterestStatus_from_dgcp(status: str) -> InterestStatus:
    if status in ("interested", "in_review", "preparing", "submitted", "won"):
        return InterestStatus.interested
    if status in ("discarded", "lost", "cancelled"):
        return InterestStatus.discarded
    return InterestStatus.none


def WorkflowStatus_from_dgcp(status: str) -> WorkflowStatus:
    mapping = {
        "detected": WorkflowStatus.discovered,
        "new": WorkflowStatus.discovered,
        "reviewed": WorkflowStatus.reviewed,
        "interested": WorkflowStatus.interested,
        "in_review": WorkflowStatus.evaluating,
        "go": WorkflowStatus.go,
        "no_go": WorkflowStatus.no_go,
        "preparing": WorkflowStatus.preparing,
        "submitted": WorkflowStatus.submitted,
        "won": WorkflowStatus.won,
        "awarded": WorkflowStatus.won,
        "lost": WorkflowStatus.lost,
        "discarded": WorkflowStatus.archived,
        "cancelled": WorkflowStatus.cancelled,
    }
    return mapping.get(status, WorkflowStatus.discovered)


async def _get_opp(db: AsyncSession, jaios_tender_id: str) -> DGCPOpportunity:
    try:
        oid = uuid.UUID(jaios_tender_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_jaios_tender_id") from exc
    opp = await db.get(DGCPOpportunity, oid)
    if not opp:
        raise HTTPException(status_code=404, detail="not_found")
    return opp


@router.get("", response_model=BidListResponse)
async def list_bids(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    institution: str | None = None,
    category: str | None = None,
    workflow_status: str | None = None,
    min_compatibility: float | None = None,
    updated_since: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DGCPOpportunity)
    if institution:
        stmt = stmt.where(DGCPOpportunity.institution.ilike(f"%{institution}%"))
    if category:
        stmt = stmt.where(DGCPOpportunity.company == category)
    if updated_since and hasattr(DGCPOpportunity, "updated_at"):
        stmt = stmt.where(DGCPOpportunity.updated_at >= updated_since)
    stmt = stmt.order_by(DGCPOpportunity.deadline.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [_opp_to_contract(r) for r in rows]
    if min_compatibility is not None:
        items = [i for i in items if (i.compatibility_score or 0) >= min_compatibility]
    if workflow_status:
        items = [i for i in items if i.workflow_status.value == workflow_status]
    return BidListResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/changes")
async def bid_changes(
    updated_since: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DGCPOpportunity).order_by(DGCPOpportunity.updated_at.desc()).limit(limit)
    if updated_since:
        stmt = stmt.where(DGCPOpportunity.updated_at >= updated_since)
    rows = (await db.execute(stmt)).scalars().all()
    items = [_opp_to_contract(r) for r in rows]
    next_cursor = items[-1].updated_at.isoformat() if items and items[-1].updated_at else cursor
    return {"items": items, "next_cursor": next_cursor, "count": len(items)}


@router.get("/{jaios_tender_id}", response_model=BidOpportunityV1)
async def get_bid(jaios_tender_id: str, db: AsyncSession = Depends(get_db)):
    opp = await _get_opp(db, jaios_tender_id)
    return _opp_to_contract(opp)


@router.post("/{jaios_tender_id}/interest", response_model=InterestResponse)
async def show_interest(
    jaios_tender_id: str,
    body: InterestRequest,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    opp = await _get_opp(db, jaios_tender_id)
    # Local status first
    if opp.status not in ("interested", "in_review", "preparing", "submitted", "won"):
        opp.status = "interested"
        await db.commit()
        await db.refresh(opp)

    contract = _opp_to_contract(opp)
    client = get_bid_center_client()
    key = idempotency_key or body.idempotency_key or f"interest:{jaios_tender_id}"

    if not client.enabled:
        # Config disabled — return local-only result (DEV / mocks)
        return InterestResponse(
            ok=True,
            idempotent=False,
            jaios_tender_id=jaios_tender_id,
            odoo_tender_id=None,
            odoo_url=None,
            workflow_status=WorkflowStatus.interested.value,
            detail="bid_center_disabled",
        )

    try:
        result = client.show_interest(
            jaios_tender_id,
            idempotency_key=key,
            body={
                **contract.model_dump(mode="json"),
                "origin": body.origin,
                "idempotency_key": key,
            },
        )
        odoo_id = result.get("odoo_tender_id")
        _STATUS_OVERRIDES[jaios_tender_id] = {
            "odoo_tender_id": odoo_id,
            "workflow_status": "evaluating",
            "interest_status": "interested",
            "last_synced_at": datetime.now(timezone.utc),
            "odoo_url": result.get("odoo_url"),
            "user_name": result.get("user_name"),
        }
        return InterestResponse(
            ok=True,
            idempotent=bool(result.get("idempotent")),
            jaios_tender_id=jaios_tender_id,
            odoo_tender_id=odoo_id,
            odoo_tender_reference=result.get("odoo_tender_reference"),
            odoo_url=result.get("odoo_url"),
            workflow_status=result.get("workflow_status") or "evaluating",
            user_name=result.get("user_name"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("interest → odoo failed")
        raise HTTPException(status_code=502, detail=f"odoo_interest_failed:{exc}") from exc


@router.post("/{jaios_tender_id}/analyze")
async def analyze_bid(jaios_tender_id: str, body: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    opp = await _get_opp(db, jaios_tender_id)
    result = {
        "ok": True,
        "jaios_tender_id": jaios_tender_id,
        "status": "completed",
        "provider": "jaios",
        "model": getattr(settings, "llm_default_provider", "rules"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": opp.description or opp.title,
        "compatibility_score": float(opp.score or 0),
        "requirements": list(opp.ai_recommendations or []) if isinstance(opp.ai_recommendations, list) else [],
        "risks": list(opp.risks or []) if isinstance(opp.risks, list) else [],
        "questions": [],
        "documents": [],
        "correlation_id": body.correlation_id,
    }
    _ANALYSIS[jaios_tender_id] = result
    client = get_bid_center_client()
    if client.enabled:
        try:
            client.push_analysis(jaios_tender_id, result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("push_analysis failed: %s", exc)
    return result


@router.get("/{jaios_tender_id}/analysis")
async def get_analysis(jaios_tender_id: str, db: AsyncSession = Depends(get_db)):
    await _get_opp(db, jaios_tender_id)
    data = _ANALYSIS.get(jaios_tender_id)
    if not data:
        return {"ok": False, "status": "missing", "jaios_tender_id": jaios_tender_id}
    return data


@router.post("/{jaios_tender_id}/status")
async def update_status(jaios_tender_id: str, body: StatusUpdateRequest, db: AsyncSession = Depends(get_db)):
    opp = await _get_opp(db, jaios_tender_id)
    _STATUS_OVERRIDES[jaios_tender_id] = {
        **_STATUS_OVERRIDES.get(jaios_tender_id, {}),
        "workflow_status": body.workflow_status.value,
        "interest_status": body.interest_status.value if body.interest_status else None,
        "odoo_tender_id": body.odoo_tender_id,
        "user_name": body.user_name,
        "last_synced_at": datetime.now(timezone.utc),
    }
    # Mirror subset into DGCP status when meaningful
    reverse = {
        WorkflowStatus.interested: "interested",
        WorkflowStatus.evaluating: "in_review",
        WorkflowStatus.go: "preparing",
        WorkflowStatus.no_go: "discarded",
        WorkflowStatus.preparing: "preparing",
        WorkflowStatus.submitted: "submitted",
        WorkflowStatus.won: "won",
        WorkflowStatus.lost: "lost",
        WorkflowStatus.cancelled: "cancelled",
        WorkflowStatus.archived: "discarded",
    }
    if body.workflow_status in reverse:
        opp.status = reverse[body.workflow_status]
        await db.commit()
    return {"ok": True, "jaios_tender_id": jaios_tender_id, "workflow_status": body.workflow_status.value}


@router.post("/_internal/sync-marker")
async def odoo_sync_marker(payload: dict[str, Any] | None = None):
    """Internal marker — prefer /integrations/odoo/sync."""
    client = get_bid_center_client()
    return {
        "ok": True,
        "mode": (payload or {}).get("mode", "manual"),
        "bid_center": client.health(),
        "at": datetime.now(timezone.utc).isoformat(),
    }


integrations_router = APIRouter(prefix="/integrations/odoo", tags=["integrations-odoo-bids"])


@integrations_router.get("/health", response_model=HealthOdooResponse)
async def integrations_odoo_health():
    client = get_bid_center_client()
    h = client.health()
    return HealthOdooResponse(ok=bool(h.get("ok")), status=str(h.get("status")), detail=h)


@integrations_router.post("/sync")
async def integrations_odoo_sync(payload: dict[str, Any] | None = None):
    return await odoo_sync_marker(payload)

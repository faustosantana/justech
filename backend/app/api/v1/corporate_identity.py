"""API — Identidad corporativa (firma / sello)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import CurrentUser, DbSession, TenantCtx, require_tenant_context
from app.core.content_disposition import build_content_disposition
from app.schemas.corporate_identity import (
    CorporateIdentityAssetResponse,
    CorporateIdentityOverviewResponse,
    CorporateIdentityUploadResponse,
)
from app.services.corporate_identity_service import CorporateIdentityService

router = APIRouter(prefix="/corporate-identity", tags=["Corporate Identity"])


def _svc(db, user) -> CorporateIdentityService:
    ctx = require_tenant_context()
    return CorporateIdentityService(db, ctx.tenant_id, user_id=user.id)


@router.get("", response_model=CorporateIdentityOverviewResponse)
async def corporate_identity_overview(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company_key: str | None = None,
) -> CorporateIdentityOverviewResponse:
    return await _svc(db, user).get_overview(company_key=company_key)


@router.get("/signatures", response_model=list[CorporateIdentityAssetResponse])
async def list_signatures(db: DbSession, user: CurrentUser, _: TenantCtx) -> list[CorporateIdentityAssetResponse]:
    return await _svc(db, user).list_signatures()


@router.get("/stamps", response_model=list[CorporateIdentityAssetResponse])
async def list_stamps(db: DbSession, user: CurrentUser, _: TenantCtx) -> list[CorporateIdentityAssetResponse]:
    return await _svc(db, user).list_stamps()


@router.get("/company/{company_key}", response_model=CorporateIdentityOverviewResponse)
async def company_identity(
    company_key: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> CorporateIdentityOverviewResponse:
    try:
        return await _svc(db, user).get_company_assets(company_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload-signature", response_model=CorporateIdentityUploadResponse)
async def upload_signature(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    file: UploadFile = File(...),
) -> CorporateIdentityUploadResponse:
    content = await file.read()
    try:
        return await _svc(db, user).upload_asset(
            asset_type="signature",
            filename=file.filename or "firma_fausto.png",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload-stamp", response_model=CorporateIdentityUploadResponse)
async def upload_stamp(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company_key: str = Query(...),
    file: UploadFile = File(...),
) -> CorporateIdentityUploadResponse:
    content = await file.read()
    try:
        return await _svc(db, user).upload_asset(
            asset_type="stamp",
            filename=file.filename or "sello.png",
            content=content,
            company_key=company_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/assets/{asset_id}/file")
async def get_asset_file(
    asset_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> Response:
    try:
        data, filename, mime = await _svc(db, user).get_asset_file(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": build_content_disposition(filename)},
    )


@router.get("/assets/file")
async def get_asset_file_by_name(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    asset_type: str = Query(...),
    filename: str = Query(...),
    company_key: str | None = None,
) -> Response:
    svc = _svc(db, user)
    if asset_type == "signature":
        path, _, status = await svc.resolve_signature_path(filename)
    else:
        path, _, status = await svc.resolve_stamp_path(company_key or "justech", filename=filename)
    if not path or status == "faltante":
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    data = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "application/octet-stream"
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": build_content_disposition(path.name)},
    )

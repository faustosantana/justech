"""Tests — Content-Disposition UTF-8 (Sprint 0.1 / C1)."""

from __future__ import annotations

import io
import uuid
from urllib.parse import unquote

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.content_disposition import ascii_filename_fallback, build_content_disposition
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.knowledge import KnowledgeAsset


def _assert_latin1_header(value: str) -> None:
    value.encode("latin-1")


@pytest.mark.parametrize(
    ("filename", "mime"),
    [
        ("Certificación Matías.pdf", "application/pdf"),
        ("Informe Niño.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("Presupuesto Año.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
)
def test_build_content_disposition_unicode_filenames(filename: str, mime: str):
    del mime
    for disposition in ("inline", "attachment"):
        header = build_content_disposition(disposition, filename)
        assert header.startswith(f"{disposition}; ")
        assert 'filename="' in header
        assert "filename*=UTF-8''" in header
        encoded_name = header.split("filename*=UTF-8''", 1)[1]
        assert unquote(encoded_name) == filename
        _assert_latin1_header(header)


def test_ascii_filename_fallback_preserves_extension():
    assert ascii_filename_fallback("Certificación Matías.pdf").endswith(".pdf")
    assert ascii_filename_fallback("Niño.docx").endswith(".docx")
    assert ascii_filename_fallback("Año.xlsx").endswith(".xlsx")


async def _login_headers() -> dict[str, str] | None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@justech.do",
                "password": "JaiosAdmin2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            return None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "content", "mime"),
    [
        (
            "Certificación Matías.pdf",
            b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n",
            "application/pdf",
        ),
        (
            "Informe Niño.docx",
            b"PK\x03\x04docx-placeholder",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "Presupuesto Año.xlsx",
            b"PK\x03\x04xlsx-placeholder",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    ],
)
async def test_document_download_unicode_filename(
    filename: str,
    content: bytes,
    mime: str,
):
    headers = await _login_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        upload = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": (filename, io.BytesIO(content), mime)},
            data={"title": f"Título {filename}"},
        )
        assert upload.status_code == 200, upload.text
        doc_id = upload.json()["id"]

        inline = await client.get(
            f"/api/v1/documents/{doc_id}/download",
            headers=headers,
            params={"disposition": "inline"},
        )
        assert inline.status_code == 200, inline.text
        assert inline.content == content
        assert inline.headers.get("content-type", "").startswith(mime.split("/")[0])
        cd = inline.headers["content-disposition"]
        _assert_latin1_header(cd)
        assert unquote(cd.split("filename*=UTF-8''", 1)[1]) == filename

        attachment = await client.get(
            f"/api/v1/documents/{doc_id}/download",
            headers=headers,
            params={"disposition": "attachment"},
        )
        assert attachment.status_code == 200
        assert attachment.content == content
        _assert_latin1_header(attachment.headers["content-disposition"])
        assert attachment.headers["content-disposition"].startswith("attachment;")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "content", "mime"),
    [
        (
            "Certificación Matías.pdf",
            b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n",
            "application/pdf",
        ),
        (
            "Informe Niño.docx",
            b"PK\x03\x04docx-placeholder",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "Presupuesto Año.xlsx",
            b"PK\x03\x04xlsx-placeholder",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    ],
)
async def test_knowledge_file_unicode_filename(
    filename: str,
    content: bytes,
    mime: str,
):
    del content
    headers = await _login_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/api/v1/knowledge/health", headers=headers)
        if health.status_code != 200 or not health.json().get("source_available"):
            pytest.skip("JustechAI source not mounted")

        sync = await client.post("/api/v1/knowledge/sync", headers=headers)
        assert sync.status_code == 200, sync.text

        assets = await client.get("/api/v1/knowledge/assets?limit=1", headers=headers)
        assert assets.status_code == 200
        items = assets.json().get("items") or []
        if not items:
            pytest.skip("Sin activos knowledge para probar descarga")
        asset_id = uuid.UUID(items[0]["id"])

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(KnowledgeAsset).where(KnowledgeAsset.id == asset_id))
            asset = result.scalar_one()
            asset.filename = filename
            asset.mime_type = mime
            await session.commit()

        response = await client.get(
            f"/api/v1/knowledge/assets/{asset_id}/file",
            headers=headers,
            params={"disposition": "inline"},
        )
        assert response.status_code == 200, response.text
        assert len(response.content) > 0
        cd = response.headers["content-disposition"]
        _assert_latin1_header(cd)
        assert cd.startswith("inline;")
        assert unquote(cd.split("filename*=UTF-8''", 1)[1]) == filename

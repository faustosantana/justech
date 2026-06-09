"""Tests — acceso autenticado a archivos de knowledge."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_knowledge_file_requires_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/knowledge/assets/{uuid.uuid4()}/file")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_document_download_requires_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/documents/{uuid.uuid4()}/download")
        assert response.status_code == 401

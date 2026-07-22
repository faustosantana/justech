"""Caché local de bytes de plantillas M365 — evita depender de URLs expiradas."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

_CACHE_ROOT = Path(getattr(settings, "documents_storage_path", "/var/jaios/documents")) / "m365_template_cache"

# Plantillas stub locales conocidas son < 50 KB; oficiales SNCC suelen ser > 70 KB
STUB_SIZE_THRESHOLD = 50_000


@dataclass(frozen=True)
class TemplateCacheStatus:
    m365_file_id: str
    cached: bool
    size_bytes: int
    path: str
    likely_stub: bool
    expected_size_bytes: int | None = None

    def to_dict(self) -> dict:
        return {
            "m365_file_id": self.m365_file_id,
            "cached": self.cached,
            "size_bytes": self.size_bytes,
            "path": self.path,
            "likely_stub": self.likely_stub,
            "expected_size_bytes": self.expected_size_bytes,
        }


def cache_path(m365_file_id: uuid.UUID) -> Path:
    return _CACHE_ROOT / f"{m365_file_id}.docx"


def read_cached_bytes(m365_file_id: uuid.UUID | None) -> bytes | None:
    if not m365_file_id:
        return None
    path = cache_path(m365_file_id)
    if path.is_file() and path.stat().st_size > 0:
        return path.read_bytes()
    return None


def write_cached_bytes(m365_file_id: uuid.UUID, content: bytes) -> Path:
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    path = cache_path(m365_file_id)
    path.write_bytes(content)
    return path


def is_likely_stub(content: bytes, *, expected_size: int | None = None) -> bool:
    if len(content) < STUB_SIZE_THRESHOLD:
        return True
    if expected_size and expected_size > STUB_SIZE_THRESHOLD:
        if len(content) < int(expected_size * 0.6):
            return True
    # Stubs generados por template_factory contienen texto simplificado
    sample = content[:8000].lower()
    if b"plantilla base jaios" in sample or b"[[pendiente]]" in sample and len(content) < 80_000:
        return True
    return False


def cache_status(
    m365_file_id: uuid.UUID,
    *,
    expected_size: int | None = None,
) -> TemplateCacheStatus:
    path = cache_path(m365_file_id)
    if path.is_file():
        size = path.stat().st_size
        return TemplateCacheStatus(
            m365_file_id=str(m365_file_id),
            cached=True,
            size_bytes=size,
            path=str(path),
            likely_stub=is_likely_stub(path.read_bytes(), expected_size=expected_size),
            expected_size_bytes=expected_size,
        )
    return TemplateCacheStatus(
        m365_file_id=str(m365_file_id),
        cached=False,
        size_bytes=0,
        path=str(path),
        likely_stub=False,
        expected_size_bytes=expected_size,
    )


def list_cached_ids() -> list[uuid.UUID]:
    if not _CACHE_ROOT.is_dir():
        return []
    out: list[uuid.UUID] = []
    for p in _CACHE_ROOT.glob("*.docx"):
        try:
            out.append(uuid.UUID(p.stem))
        except ValueError:
            continue
    return out

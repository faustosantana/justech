"""Almacenamiento por licitación — DGCP Process Repository (separado de Corporate Knowledge)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import settings


class DGCPProcessStorageService:
    """Archivos del proceso DGCP bajo ``{expediente_storage_path}/{tenant}/DGCP/{code}/``."""

    def __init__(self, tenant_id: uuid.UUID):
        self.tenant_id = tenant_id
        self.base = Path(settings.expediente_storage_path) / str(tenant_id) / "DGCP"

    @staticmethod
    def sanitize_code(opportunity_code: str) -> str:
        cleaned = re.sub(r"[^\w\-]+", "_", (opportunity_code or "proceso").strip())
        return cleaned or "proceso"

    def opportunity_dir(self, opportunity_code: str) -> Path:
        path = self.base / self.sanitize_code(opportunity_code)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def slugify(title: str, *, max_len: int = 80) -> str:
        slug = re.sub(r"[^\w\-]+", "_", title.strip().lower()).strip("_")
        return (slug[:max_len] or "documento").rstrip("_")

    def write_text(self, opportunity_code: str, filename: str, content: str) -> str:
        target = self.opportunity_dir(opportunity_code) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target.name

    def write_bytes(self, opportunity_code: str, filename: str, content: bytes) -> str:
        target = self.opportunity_dir(opportunity_code) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target.name

    def read_bytes(self, opportunity_code: str, filename: str) -> bytes:
        target = self.opportunity_dir(opportunity_code) / filename
        if not target.is_file():
            raise FileNotFoundError(f"Archivo DGCP no encontrado: {filename}")
        resolved = target.resolve()
        root = self.opportunity_dir(opportunity_code).resolve()
        if not str(resolved).startswith(str(root)):
            raise ValueError("Ruta fuera del repositorio DGCP")
        return resolved.read_bytes()

    def relative_uri(self, opportunity_code: str, filename: str) -> str:
        return f"DGCP/{self.sanitize_code(opportunity_code)}/{filename}"

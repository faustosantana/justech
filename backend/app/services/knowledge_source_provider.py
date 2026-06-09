"""Proveedor de fuente externa — read-only (Fase 7.2)."""

from __future__ import annotations

import hashlib
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".csv", ".json", ".rtf", ".odt"}


@dataclass
class SourceFileInfo:
    relative_path: str
    filename: str
    absolute_path: Path
    folder_category: str
    file_size: int
    mime_type: str | None
    modified_at: datetime
    content_hash: str


class KnowledgeSourceProvider(ABC):
    provider_name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def root_path(self) -> str: ...

    @abstractmethod
    def list_files(self, folders: list[str]) -> list[SourceFileInfo]: ...

    @abstractmethod
    def read_bytes(self, relative_path: str) -> bytes: ...


class FilesystemKnowledgeSourceProvider(KnowledgeSourceProvider):
    provider_name = "filesystem"

    def __init__(self, root: str | None = None):
        self._root = Path(root or settings.knowledge_source_path)

    def is_available(self) -> bool:
        return self._root.exists() and self._root.is_dir()

    def root_path(self) -> str:
        return str(self._root)

    def list_files(self, folders: list[str]) -> list[SourceFileInfo]:
        if not self.is_available():
            return []
        results: list[SourceFileInfo] = []
        for folder in folders:
            base = self._root / folder
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                if path.name.startswith("."):
                    continue
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                rel = path.relative_to(self._root).as_posix()
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                content_hash = self._hash_file(path)
                mime, _ = mimetypes.guess_type(path.name)
                results.append(
                    SourceFileInfo(
                        relative_path=rel,
                        filename=path.name,
                        absolute_path=path,
                        folder_category=folder,
                        file_size=stat.st_size,
                        mime_type=mime,
                        modified_at=modified,
                        content_hash=content_hash,
                    )
                )
        return results

    def read_bytes(self, relative_path: str) -> bytes:
        target = (self._root / relative_path).resolve()
        root = self._root.resolve()
        if not str(target).startswith(str(root)):
            raise ValueError("Ruta fuera del repositorio fuente")
        return target.read_bytes()

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        h.update(str(path.stat().st_size).encode())
        h.update(str(path.stat().st_mtime).encode())
        h.update(path.name.encode())
        return h.hexdigest()[:32]


def get_knowledge_source_provider() -> KnowledgeSourceProvider:
    return FilesystemKnowledgeSourceProvider()

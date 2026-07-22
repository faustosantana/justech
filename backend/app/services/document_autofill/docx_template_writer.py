"""Relleno de plantillas DOCX — delega al motor genérico."""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path

from app.services.document_autofill.generic_docx_fill_engine import (
    MISSING_MARKER,
    detect_docx_fields,
    fill_docx_bytes_generic,
)


def extract_docx_aliases(template_bytes: bytes) -> list[str]:
    """Extrae aliases Word (w:alias) preservando texto original."""
    aliases: list[str] = []
    seen: set[str] = set()
    with zipfile.ZipFile(BytesIO(template_bytes)) as zf:
        for name in zf.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            text = zf.read(name).decode("utf-8", errors="ignore")
            for alias in re.findall(r'w:alias w:val="([^"]+)"', text):
                if alias not in seen:
                    seen.add(alias)
                    aliases.append(alias)
    return aliases


def fill_docx_bytes(
    template_bytes: bytes,
    values: dict[str, str],
    *,
    alias_values: dict[str, str] | None = None,
) -> bytes:
    """Copia la plantilla oficial y rellena campos sin alterar diseño."""
    filled, _stats = fill_docx_bytes_generic(template_bytes, values, alias_values=alias_values)
    return filled


def fill_docx_file(template_path: Path, values: dict[str, str], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filled = fill_docx_bytes(template_path.read_bytes(), values)
    output_path.write_bytes(filled)
    return output_path


__all__ = [
    "MISSING_MARKER",
    "detect_docx_fields",
    "extract_docx_aliases",
    "fill_docx_bytes",
    "fill_docx_file",
]

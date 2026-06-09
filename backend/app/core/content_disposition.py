"""HTTP Content-Disposition — RFC 5987, safe for latin-1 header transports."""

from __future__ import annotations

import unicodedata
from pathlib import Path
from urllib.parse import quote


def ascii_filename_fallback(filename: str) -> str:
    """ASCII-only fallback for legacy ``filename=`` (HTTP/1.x latin-1)."""
    clean = filename.replace("\\", "_").replace('"', "")
    normalized = unicodedata.normalize("NFKD", clean)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_name or ascii_name in (".", ".."):
        suffix = Path(clean).suffix
        ascii_name = f"download{suffix}" if suffix else "download"
    return ascii_name


def build_content_disposition(disposition: str, filename: str) -> str:
    """
    Build Content-Disposition encodable in latin-1.

    Uses ASCII ``filename=`` plus RFC 5987 ``filename*=UTF-8''…`` for the real name.
    """
    disposition = disposition if disposition in ("inline", "attachment") else "inline"
    clean = filename.replace('"', "")
    fallback = ascii_filename_fallback(clean)
    encoded = quote(clean, safe="")
    return f'{disposition}; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'

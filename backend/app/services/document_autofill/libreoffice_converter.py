"""Conversión DOCX → PDF con LibreOffice headless (fidelidad de layout)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_convert_lock = threading.Lock()
_soffice_path: str | None = None


def _resolve_soffice() -> str | None:
    global _soffice_path
    if _soffice_path is not None:
        return _soffice_path or None
    configured = getattr(settings, "libreoffice_path", None) or os.environ.get("LIBREOFFICE_PATH")
    if configured and Path(configured).is_file():
        _soffice_path = configured
        return configured
    found = shutil.which("soffice") or shutil.which("libreoffice")
    _soffice_path = found or ""
    return found


def is_libreoffice_available() -> bool:
    return _resolve_soffice() is not None


def docx_bytes_to_pdf_libreoffice(docx_bytes: bytes, *, timeout: float | None = None) -> bytes:
    """Convierte DOCX a PDF usando soffice --headless."""
    soffice = _resolve_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) no está instalado")

    max_wait = timeout or float(getattr(settings, "libreoffice_convert_timeout", 120))

    with _convert_lock:
        with tempfile.TemporaryDirectory(prefix="jaios-lo-") as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "document.docx"
            input_path.write_bytes(docx_bytes)
            profile_dir = tmp_path / "profile"
            profile_dir.mkdir()
            profile_uri = profile_dir.as_uri()

            cmd = [
                soffice,
                f"-env:UserInstallation={profile_uri}",
                "--headless",
                "--norestore",
                "--nolockcheck",
                "--nodefault",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_path),
                str(input_path),
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=max_wait,
                    check=False,
                    env={**os.environ, "HOME": str(tmp_path)},
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"LibreOffice excedió timeout ({max_wait}s)") from exc

            if proc.returncode != 0:
                stderr = (proc.stderr or b"").decode("utf-8", errors="replace")[:500]
                raise RuntimeError(f"LibreOffice falló (code={proc.returncode}): {stderr}")

            pdf_path = tmp_path / "document.pdf"
            if not pdf_path.is_file():
                pdfs = list(tmp_path.glob("*.pdf"))
                if not pdfs:
                    raise RuntimeError("LibreOffice no generó archivo PDF")
                pdf_path = pdfs[0]

            pdf_bytes = pdf_path.read_bytes()
            if not pdf_bytes.startswith(b"%PDF"):
                raise RuntimeError("Salida LibreOffice no es PDF válido")
            return pdf_bytes

"""Overlay de firma y sello sobre PDF — copia controlada."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def _coords(position: str, page_w: float, page_h: float, img_w: float, img_h: float, margin: float) -> tuple[float, float]:
    if position == "bottom_right":
        return page_w - img_w - margin, margin
    if position == "bottom_left":
        return margin, margin
    if position == "top_right":
        return page_w - img_w - margin, page_h - img_h - margin
    if position == "top_left":
        return margin, page_h - img_h - margin
    return page_w - img_w - margin, margin


def apply_signature_and_stamp(
    pdf_bytes: bytes,
    *,
    signature_path: Path | None,
    stamp_path: Path | None,
    placement: dict | None = None,
) -> bytes:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    placement = placement or {}
    sig_cfg = placement.get("signature") or {"position": "bottom_right", "width": 180, "margin": 36}
    stamp_cfg = placement.get("stamp") or {"position": "bottom_left", "width": 150, "margin": 36}

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        media = page.mediabox
        width = float(media.width)
        height = float(media.height)
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))

        if stamp_path and stamp_path.is_file():
            sw = float(stamp_cfg.get("width", 150))
            sh = sw * 0.75
            margin = float(stamp_cfg.get("margin", 36))
            sx, sy = _coords(stamp_cfg.get("position", "bottom_left"), width, height, sw, sh, margin)
            c.drawImage(str(stamp_path), sx, sy, width=sw, height=sh, preserveAspectRatio=True, mask="auto")

        if signature_path and signature_path.is_file():
            sig_w = float(sig_cfg.get("width", 180))
            sig_h = sig_w * 0.35
            margin = float(sig_cfg.get("margin", 36))
            sx, sy = _coords(sig_cfg.get("position", "bottom_right"), width, height, sig_w, sig_h, margin)
            c.drawImage(str(signature_path), sx, sy, width=sig_w, height=sig_h, preserveAspectRatio=True, mask="auto")

        c.save()
        packet.seek(0)
        overlay = PdfReader(packet)
        if overlay.pages:
            page.merge_page(overlay.pages[0])
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def text_to_pdf_bytes(title: str, lines: list[str]) -> bytes:
    """PDF mínimo para formularios SNCC sin plantilla DOCX disponible."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, title[:90])
    y -= 28
    c.setFont("Helvetica", 10)
    for line in lines:
        if y < 72:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 10)
        c.drawString(72, y, line[:110])
        y -= 14
    c.save()
    return buf.getvalue()

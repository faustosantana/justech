"""Escritura de campos en PDF — AcroForm y overlay de texto."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

MISSING_MARKER = "[[PENDIENTE]]"


def fill_pdf_acroform(template_bytes: bytes, values: dict[str, str]) -> bytes:
    reader = PdfReader(BytesIO(template_bytes))
    fields = reader.get_fields()
    if not fields:
        return template_bytes
    writer = PdfWriter()
    writer.append(reader)
    update_map: dict[str, str] = {}
    for field_name in fields:
        key = field_name.lower().replace(" ", "_")
        val = values.get(key) or values.get(field_name)
        if val:
            update_map[field_name] = str(val)
        else:
            update_map[field_name] = f"{MISSING_MARKER} {field_name}"
    try:
        for page in writer.pages:
            writer.update_page_form_field_values(page, update_map)
    except Exception:
        return template_bytes
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def overlay_text_on_pdf(
    template_bytes: bytes,
    overlays: list[tuple[float, float, str, int]],
) -> bytes:
    """Overlay text at x,y points (bottom-left origin per page 0)."""
    reader = PdfReader(BytesIO(template_bytes))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        packet = BytesIO()
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        c = canvas.Canvas(packet, pagesize=(w, h))
        c.setFont("Helvetica", 10)
        for page_idx, x, y, text, size in [(o[3], o[0], o[1], o[2], o[3]) if len(o) > 3 else (0, *o) for o in overlays]:
            if page_idx != i:
                continue
            c.setFont("Helvetica", size if isinstance(size, int) else 10)
            c.drawString(x, y, text[:200])
        c.save()
        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def fill_pdf_file(template_path: Path, values: dict[str, str], output_path: Path) -> Path:
    raw = template_path.read_bytes()
    reader = PdfReader(BytesIO(raw))
    if reader.get_fields():
        filled = fill_pdf_acroform(raw, values)
    else:
        filled = raw
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(filled)
    return output_path

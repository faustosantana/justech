"""PDF mínimo de cotización — copia de lectura generada desde datos Odoo (sale.order)."""

from __future__ import annotations

from decimal import Decimal

from app.schemas.odoo import OdooQuotationDetailResponse


def _esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def _money(value: Decimal | float | int | str) -> str:
    try:
        return f"{Decimal(str(value)):,.2f}"
    except Exception:
        return str(value)


def build_quotation_pdf(detail: OdooQuotationDetailResponse) -> bytes:
    """Genera PDF legible con cabecera y líneas de la cotización Odoo."""
    lines: list[str] = [
        f"Cotizacion Odoo: {detail.name}",
        f"Cliente: {detail.partner_name}",
        f"Fecha: {detail.date_order or '-'}",
        f"Vendedor: {detail.salesperson_name or '-'}",
        f"Empresa: {detail.company_name or '-'}",
        f"Estado: {detail.state}",
        f"Valida hasta: {detail.validity_date or '-'}",
        "",
        f"TOTAL: {_money(detail.amount_total)} {detail.currency}",
        "",
        "Lineas:",
    ]
    for idx, line in enumerate(detail.lines, start=1):
        lines.append(
            f"{idx}. {line.product_name} | {line.quantity} x {_money(line.price_unit)} "
            f"= {_money(line.subtotal)} {detail.currency}"
        )
        if line.taxes:
            lines.append(f"   Impuestos: {', '.join(line.taxes)}")
    lines.extend(["", "Copia generada por JAIOS desde Odoo (solo lectura)."])

    y_start = 780
    content_parts = ["BT", "/F1 10 Tf", f"40 {y_start} Td"]
    for i, line in enumerate(lines):
        if i > 0:
            content_parts.append("0 -13 Td")
        content_parts.append(f"({_esc(line[:120])}) Tj")
    content_parts.append("ET")
    stream = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return bytes(pdf)

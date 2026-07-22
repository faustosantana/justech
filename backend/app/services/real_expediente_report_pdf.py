"""Generación de reporte_preparacion.pdf para expediente real DGCP."""

from __future__ import annotations

from io import BytesIO
from typing import Any


def build_preparation_report_pdf(manifest: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    _, height = letter
    y = height - 0.75 * inch

    def line(text: str, *, bold: bool = False, size: int = 10) -> None:
        nonlocal y
        if y < inch:
            c.showPage()
            y = height - 0.75 * inch
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(0.75 * inch, y, str(text)[:105])
        y -= 14

    def section(title: str) -> None:
        nonlocal y
        y -= 6
        line(title, bold=True, size=12)

    line("JAIOS — Reporte de Preparación de Expediente DGCP", bold=True, size=14)
    line(f"Proceso: {manifest.get('process_code', '—')}")
    line(f"Nombre: {manifest.get('process_name', '—')}")
    line(f"Empresa: {manifest.get('company_name', '—')}")
    line(f"Unidad compradora: {manifest.get('buyer', '—')}")
    line(f"Generado: {manifest.get('generated_at', '—')}")
    line(f"Usuario: {manifest.get('generated_by', '—')}")
    line(f"Estado: {manifest.get('status', '—')}")
    if manifest.get("audit_hash"):
        line(f"Hash auditoría: {manifest.get('audit_hash')}")

    section("Resumen ejecutivo")
    line(f"Preparación: {manifest.get('preparation_percentage', 0)}%")
    summary = manifest.get("checklist_summary") or {}
    line(f"Total requisitos: {summary.get('total', 0)}")
    line(f"Cumplidos: {summary.get('compliant', 0)}")
    line(f"Faltantes: {len(manifest.get('missing') or [])}")
    line(f"Vencidos: {len(manifest.get('expired') or [])}")
    line(f"Requieren revisión: {len(manifest.get('requires_review') or [])}")
    line(f"Listos para subir: {len(manifest.get('ready_to_upload') or [])}")

    section("Checklist")
    for req in (manifest.get("requirements") or [])[:45]:
        line(
            f"• {req.get('name', '—')} | {req.get('status', '—')} | "
            f"{req.get('folder', '—')} | {'OK' if req.get('ready_to_upload') else 'No'}"
        )

    legal = [r for r in (manifest.get("requirements") or []) if str(r.get("folder", "")).startswith("01_")]
    if legal:
        section("Documentos legales")
        for req in legal[:15]:
            line(f"• {req.get('name', '—')} — {req.get('status', '—')}")

    forms = [r for r in (manifest.get("requirements") or []) if str(r.get("folder", "")).startswith("02_")]
    if forms:
        section("Formularios")
        for req in forms[:15]:
            signed = "PDF" if req.get("assigned_file", "").lower().endswith(".pdf") else "pendiente"
            line(f"• {req.get('name', '—')} — {signed}")

    economic = [r for r in (manifest.get("requirements") or []) if str(r.get("folder", "")).startswith("04_")]
    if economic:
        section("Oferta económica")
        for req in economic[:8]:
            line(f"• {req.get('name', '—')} — {req.get('status', '—')}")

    fabricante = [r for r in (manifest.get("requirements") or []) if str(r.get("folder", "")).startswith("06_")]
    section("Cartas fabricante")
    if fabricante:
        for req in fabricante[:8]:
            line(f"• {req.get('name', '—')} — {req.get('status', '—')}")
    else:
        line("• Sin cartas registradas")

    if manifest.get("missing"):
        section("Documentos faltantes")
        for m in manifest["missing"][:15]:
            line(f"• {m.get('name', m)}")

    if manifest.get("expired"):
        section("Documentos vencidos")
        for e in manifest["expired"][:15]:
            line(f"• {e.get('name', e)}")

    if manifest.get("warnings"):
        section("Alertas")
        for w in manifest["warnings"][:20]:
            line(f"⚠ {w}")

    section("Conclusión")
    status = manifest.get("status", "—")
    if status in ("listo_para_subir", "paquete_dgcp_preparado"):
        conclusion = "listo_para_subir"
    elif status in ("generado_con_observaciones", "listo_para_revision"):
        conclusion = "listo_para_revision"
    else:
        conclusion = "incompleto"
    line(f"Estado final: {conclusion}")
    line("Preparado por JAIOS — revisión pendiente por usuario antes de subir al portal DGCP.")

    c.save()
    return buf.getvalue()

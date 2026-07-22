"""Genera matriz de compatibilidad de autollenado para todas las plantillas M365."""

from __future__ import annotations

import asyncio
import csv
import sys
import uuid
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts.seed import ADMIN_EMAIL
from app.services.document_autofill.dgcp_autofill_batch_service import DgcpAutofillBatchService

# Validación obligatoria Fausto — muestras representativas (matcher explícito evita colisiones)
VALIDATION_SAMPLES: dict[str, Callable] = {
    "SNCC.F033": lambda r: r.form_type == "SNCC.F033",
    "SNCC.F034": lambda r: r.form_type == "SNCC.F034",
    "SNCC.F042": lambda r: r.form_type == "SNCC.F042",
    "SNCC.F047": lambda r: r.form_type == "SNCC.F047",
    "SNCC.F009": lambda r: r.form_type == "SNCC.F009",
    "SNCC.F010": lambda r: r.form_type == "SNCC.F010",
    "CARTA": lambda r: r.form_type == "SNCC.D058" or "disponibilidad" in r.template_name.lower(),
    "DECLARACION": lambda r: r.detected_type == "declaracion" or r.form_type.startswith("DECLARACION."),
}

OPP_ID = uuid.UUID("ae07d012-4b67-4622-8507-bff9060c632b")


def _support_level(result) -> str:
    if result.status == "FAILED" or result.errors:
        return "no_soportada"
    if result.completion_status in ("READY_FOR_SIGNATURE", "DRAFT_OK"):
        if result.aliases_critical_pending > 0:
            return "parcialmente_soportada"
        return "soportada"
    if result.completion_status == "BLOCKED":
        return "parcialmente_soportada"
    return "parcialmente_soportada"


def _pass_fail(result) -> str:
    if result.status == "FAILED":
        return "FAIL"
    if not result.docx_generated or not result.pdf_generated:
        return "FAIL"
    if result.source not in ("m365", "m365_cache", "pending"):
        return "FAIL"
    if result.completion_status == "READY_FOR_SIGNATURE":
        return "PASS"
    if result.completion_status == "DRAFT_OK" and result.aliases_critical_pending == 0:
        return "PASS"
    return "PARTIAL"


async def main() -> int:
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "justech"))).scalar_one()
        admin = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one()
        opp = await db.get(DGCPOpportunity, OPP_ID)
        if not opp:
            print(f"Expediente {OPP_ID} no encontrado", file=sys.stderr)
            return 1

        batch = DgcpAutofillBatchService(db, tenant.id, user_id=admin.id)
        results = await batch.run_all(opp, user_email=admin.email)

        out_dir = batch.output_root
        matrix_path = out_dir / "COMPATIBILITY_MATRIX.csv"
        md_path = out_dir / "COMPATIBILITY_MATRIX.md"

        with matrix_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "plantilla",
                    "form_type",
                    "categoria",
                    "soporte",
                    "pass_fail",
                    "plantilla_oficial",
                    "docx_generado",
                    "pdf_generado",
                    "campos_detectados",
                    "campos_completados",
                    "campos_criticos_pendientes",
                    "campos_no_criticos_pendientes",
                    "campos_no_mapeados",
                    "formato_preservado",
                    "motor_pdf",
                    "razon",
                    "accion_requerida",
                ]
            )
            for r in results:
                support = _support_level(r)
                pf = _pass_fail(r)
                reason = r.partial_reason or ("; ".join(r.errors) if r.errors else "")
                action = ""
                if r.aliases_critical_pending:
                    action = "Completar campos críticos o mapear aliases"
                elif r.non_critical_pending_aliases:
                    action = "Opcional: completar campos no críticos"
                if r.status == "FAILED":
                    action = "Verificar caché M365 / OAuth / bootstrap"
                writer.writerow(
                    [
                        r.template_name,
                        r.form_type,
                        r.detected_type,
                        support,
                        pf,
                        "si" if r.source in ("m365", "m365_cache") else "no",
                        "si" if r.docx_generated else "no",
                        "si" if r.pdf_generated else "no",
                        r.aliases_detected,
                        r.aliases_mapped,
                        r.aliases_critical_pending,
                        r.aliases_non_critical_pending,
                        len(r.fields_pending),
                        "si" if r.original_intact else "no",
                        r.pdf_engine,
                        reason,
                        action,
                    ]
                )

        lines = [
            "# Matriz de compatibilidad — Autollenado plantillas M365",
            f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
            f"**Expediente prueba:** {opp.code}",
            "",
            "## Resumen",
            f"- Total plantillas: {len(results)}",
            f"- PASS: {sum(1 for r in results if _pass_fail(r) == 'PASS')}",
            f"- PARTIAL: {sum(1 for r in results if _pass_fail(r) == 'PARTIAL')}",
            f"- FAIL: {sum(1 for r in results if _pass_fail(r) == 'FAIL')}",
            "",
            "## Validación obligatoria (muestras)",
            "",
            "| Formulario | Plantilla oficial | DOCX | PDF | Campos llenos | Faltantes | Formato | PASS/FAIL |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for sample, matcher in VALIDATION_SAMPLES.items():
            matches = [r for r in results if matcher(r)]
            if not matches:
                note = "Sin plantilla en biblioteca" if sample == "DECLARACION" else "NO INDEXADA"
                lines.append(f"| {sample} | — | — | — | — | — | — | **{note}** |")
                continue
            r = matches[0]
            lines.append(
                f"| {sample} | {r.template_name[:40]} | "
                f"{'✅' if r.docx_generated else '❌'} | "
                f"{'✅' if r.pdf_generated else '❌'} | "
                f"{r.aliases_mapped} | "
                f"{r.aliases_critical_pending + r.aliases_non_critical_pending} | "
                f"{'✅' if r.original_intact else '❌'} | "
                f"**{_pass_fail(r)}** |"
            )

        lines.extend(["", f"CSV completo: `{matrix_path}`", ""])
        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(md_path.read_text(encoding="utf-8"))
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

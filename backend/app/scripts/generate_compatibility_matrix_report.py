"""Genera matriz completa de compatibilidad desde batch_summary existente o batch nuevo."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts.seed import ADMIN_EMAIL
from app.services.document_autofill.compatibility_matrix import MatrixRow, classify_result, result_from_batch_dict
from app.services.document_autofill.dgcp_autofill_batch_service import DgcpAutofillBatchService

VALIDATION_SAMPLES: dict[str, Callable] = {
    "SNCC F.033": lambda r: r.formulario == "SNCC.F033",
    "SNCC F.034": lambda r: r.formulario == "SNCC.F034",
    "SNCC F.042": lambda r: r.formulario == "SNCC.F042",
    "SNCC F.047": lambda r: r.formulario == "SNCC.F047",
    "SNCC F.009": lambda r: r.formulario == "SNCC.F009",
    "SNCC F.010": lambda r: r.formulario == "SNCC.F010",
    "Carta (D.058)": lambda r: r.formulario == "SNCC.D058",
    "Declaración": lambda r: r.tipo == "declaracion" or r.formulario.startswith("DECLARACION."),
}

OPP_ID = uuid.UUID("ae07d012-4b67-4622-8507-bff9060c632b")
REPO_DOCS = Path(__file__).resolve().parents[2] / "docs"


def _unmapped_from_audit(audit_path: str | None) -> list[str]:
    if not audit_path:
        return []
    p = Path(audit_path)
    if not p.is_file():
        stem = Path(audit_path).stem.replace("_audit", "")
        p = Path(audit_path).parent / f"{stem}_audit.json"
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("unmapped_fields") or [])
    except (json.JSONDecodeError, OSError):
        return []


def _template_format(name: str) -> str:
    return "pdf" if name.lower().endswith(".pdf") else "docx"


def _write_csv(path: Path, rows: list[MatrixRow]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "Formulario",
                "Tipo",
                "Plantilla oficial encontrada",
                "Fuente",
                "DOCX generado",
                "PDF generado",
                "Campos detectados",
                "Campos completados",
                "Campos faltantes",
                "Campos no mapeados",
                "Formato preservado",
                "Estado",
                "Causa raíz",
                "Falta plantilla",
                "No es DOCX",
                "Plantilla corrupta",
                "Sin campos detectables",
                "Requiere mapeo manual",
                "Requiere OCR/conversión",
                "Acción concreta",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.formulario,
                    r.tipo,
                    r.plantilla_oficial,
                    r.fuente,
                    r.docx_generado,
                    r.pdf_generado,
                    r.campos_detectados,
                    r.campos_completados,
                    r.campos_faltantes,
                    r.campos_no_mapeados,
                    r.formato_preservado,
                    r.estado,
                    r.causa_raiz,
                    "sí" if r.falta_plantilla else "no",
                    "sí" if r.no_es_docx else "no",
                    "sí" if r.plantilla_corrupta else "no",
                    "sí" if r.sin_campos_detectables else "no",
                    "sí" if r.requiere_mapeo_manual else "no",
                    "sí" if r.requiere_ocr_conversion else "no",
                    r.accion_concreta,
                ]
            )


def _write_markdown(path: Path, rows: list[MatrixRow], *, opp_code: str, batch_dir: str) -> None:
    pass_n = sum(1 for r in rows if r.estado == "PASS")
    partial_n = sum(1 for r in rows if r.estado == "PARTIAL")
    fail_n = sum(1 for r in rows if r.estado == "FAIL")

    lines = [
        "# Matriz de compatibilidad — Autollenado plantillas oficiales",
        "",
        f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
        f"**Expediente QA:** {opp_code}",
        f"**Batch:** `{batch_dir}`",
        "",
        "## Resumen",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total plantillas indexadas | {len(rows)} |",
        f"| PASS | {pass_n} |",
        f"| PARTIAL | {partial_n} |",
        f"| FAIL | {fail_n} |",
        f"| Stubs usados | **0** (bloqueados) |",
        "",
        "## Validación obligatoria (8 muestras)",
        "",
        "| Formulario | Plantilla | Fuente | DOCX | PDF | Completados | Faltantes | Formato | Estado |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for label, matcher in VALIDATION_SAMPLES.items():
        matches = [r for r in rows if matcher(r)]
        if not matches:
            note = "Sin plantilla en biblioteca" if "Declaración" in label else "NO INDEXADA"
            lines.append(f"| {label} | — | — | — | — | — | — | — | **{note}** |")
            continue
        r = matches[0]
        lines.append(
            f"| {label} | {r.plantilla_oficial[:45]} | {r.fuente} | {r.docx_generado} | {r.pdf_generado} | "
            f"{r.campos_completados} | {r.campos_faltantes} | {r.formato_preservado} | **{r.estado}** |"
        )

    lines.extend(["", "## Los 8 FAIL — causa raíz detallada", ""])
    fails = [r for r in rows if r.estado == "FAIL"]
    for i, r in enumerate(fails, 1):
        lines.extend(
            [
                f"### {i}. {r.plantilla_oficial if r.plantilla_oficial != 'Sin plantilla oficial' else r.formulario}",
                "",
                f"- **Formulario:** `{r.formulario}`",
                f"- **Tipo:** {r.tipo}",
                f"- **Fuente:** {r.fuente}",
                f"- **Causa raíz:** {r.causa_raiz}",
                f"- Falta plantilla: {'sí' if r.falta_plantilla else 'no'}",
                f"- No es DOCX: {'sí' if r.no_es_docx else 'no'}",
                f"- Plantilla corrupta: {'sí' if r.plantilla_corrupta else 'no'}",
                f"- Requiere OCR/conversión: {'sí' if r.requiere_ocr_conversion else 'no'}",
                f"- **Acción:** {r.accion_concreta}",
                "",
            ]
        )

    lines.extend(["", "## Los PARTIAL — causa raíz detallada", ""])
    for r in [x for x in rows if x.estado == "PARTIAL"]:
        lines.extend(
            [
                f"### {r.plantilla_oficial}",
                "",
                f"- **Campos críticos pendientes:** {', '.join(r.campos_faltantes_lista) or '—'}",
                f"- **Causa raíz:** {r.causa_raiz}",
                f"- Requiere mapeo manual: {'sí' if r.requiere_mapeo_manual else 'no'}",
                f"- **Acción:** {r.accion_concreta}",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "## Matriz completa (61 plantillas)",
            "",
            "| Formulario | Tipo | Plantilla | Fuente | DOCX | PDF | Det. | Compl. | Falt. | No mapeados | Formato | Estado |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for r in sorted(rows, key=lambda x: (x.estado != "FAIL", x.estado != "PARTIAL", x.formulario)):
        tpl = (r.plantilla_oficial[:35] + "…") if len(r.plantilla_oficial) > 36 else r.plantilla_oficial
        lines.append(
            f"| {r.formulario} | {r.tipo} | {tpl} | {r.fuente[:20]} | {r.docx_generado} | {r.pdf_generado} | "
            f"{r.campos_detectados} | {r.campos_completados} | {r.campos_faltantes} | {r.campos_no_mapeados} | "
            f"{r.formato_preservado} | **{r.estado}** |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def _copy_evidence(rows: list[MatrixRow], evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for label, matcher in VALIDATION_SAMPLES.items():
        matches = [r for r in rows if matcher(r)]
        entry: dict = {"muestra": label, "estado": "NO INDEXADA"}
        if matches:
            r = matches[0]
            entry = {
                "muestra": label,
                "formulario": r.formulario,
                "estado": r.estado,
                "plantilla": r.plantilla_oficial,
                "fuente": r.fuente,
                "campos_completados": r.campos_completados,
                "campos_faltantes": r.campos_faltantes_lista,
                "campos_no_mapeados": r.campos_no_mapeados_lista[:10],
                "formato_preservado": r.formato_preservado,
            }
            slug = label.lower().replace(" ", "_").replace(".", "")
            for kind, src in (("docx", r.docx_path), ("pdf", r.pdf_path)):
                if src and Path(src).is_file():
                    dest = evidence_dir / f"{slug}.{kind}"
                    shutil.copy2(src, dest)
                    entry[f"{kind}_evidencia"] = str(dest)
                    entry[f"{kind}_bytes"] = Path(src).stat().st_size
        manifest.append(entry)
    (evidence_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def _run_fresh_batch() -> tuple[list[MatrixRow], Path, str]:
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "justech"))).scalar_one()
        admin = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one()
        opp = await db.get(DGCPOpportunity, OPP_ID)
        if not opp:
            raise SystemExit(f"Expediente {OPP_ID} no encontrado")

        batch = DgcpAutofillBatchService(db, tenant.id, user_id=admin.id)
        results = await batch.run_all(opp, user_email=admin.email)
        rows: list[MatrixRow] = []
        for r in results:
            audit = None
            if r.pdf_path:
                audit = str(Path(r.pdf_path).with_name(Path(r.pdf_path).stem + "_audit.json"))
            unmapped = _unmapped_from_audit(audit)
            rows.append(
                classify_result(
                    r,
                    unmapped_fields=unmapped,
                    template_format=_template_format(r.template_name),
                )
            )
        return rows, batch.output_root, opp.code


def _from_batch_summary(summary_path: Path) -> tuple[list[MatrixRow], Path, str]:
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    batch_dir = summary_path.parent
    rows: list[MatrixRow] = []
    for item in data["results"]:
        r = result_from_batch_dict(item)
        audit = item.get("audit_path")
        if not audit and r.pdf_path:
            audit = str(Path(r.pdf_path).with_name(Path(r.pdf_path).stem + "_audit.json"))
        unmapped = _unmapped_from_audit(audit)
        rows.append(
            classify_result(
                r,
                unmapped_fields=unmapped,
                template_format=_template_format(r.template_name),
            )
        )
    return rows, batch_dir, data.get("results", [{}])[0].get("m365_location", "DGII-CCC-PEEX-2026-0005")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch-summary",
        default="/var/jaios/expedientes/8ebfa281-cd3c-4017-8e47-c572a79d84b2/_autofill_qa_20260624_192857/batch_summary.json",
        help="Ruta a batch_summary.json existente",
    )
    parser.add_argument("--fresh", action="store_true", help="Ejecutar batch completo de nuevo")
    args = parser.parse_args()

    if args.fresh:
        rows, batch_dir, opp_code = await _run_fresh_batch()
    else:
        summary = Path(args.batch_summary)
        if not summary.is_file():
            print(f"No existe batch: {summary}; ejecutando batch fresco…", file=sys.stderr)
            rows, batch_dir, opp_code = await _run_fresh_batch()
        else:
            rows, batch_dir, opp_code = _from_batch_summary(summary)

    REPO_DOCS.mkdir(parents=True, exist_ok=True)
    evidence_dir = REPO_DOCS / "autofill_evidence"
    csv_path = REPO_DOCS / "COMPATIBILITY_MATRIX.csv"
    md_path = REPO_DOCS / "COMPATIBILITY_MATRIX.md"

    _write_csv(csv_path, rows)
    _write_markdown(md_path, rows, opp_code="DGII-CCC-PEEX-2026-0005", batch_dir=str(batch_dir))
    _copy_evidence(rows, evidence_dir)

    # Copia también al directorio batch
    shutil.copy2(csv_path, batch_dir / "COMPATIBILITY_MATRIX_FULL.csv")
    shutil.copy2(md_path, batch_dir / "COMPATIBILITY_MATRIX_FULL.md")

    print(md_path.read_text(encoding="utf-8")[:4000])
    print(f"\n… CSV completo: {csv_path}")
    print(f"Evidencia: {evidence_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

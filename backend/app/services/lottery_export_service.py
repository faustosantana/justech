"""Exportaciones seguras CSV / XLSX / PDF — sin LLM, sin raw_payload."""

from __future__ import annotations

import csv
import io
import re
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import forbidden, not_found
from app.models.lottery import LotteryAuditLog, LotteryExport
from app.schemas.lottery_product import LotteryExportRequest, LotteryExportResponse
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_product_service import DISCLAIMER, LotteryProductService
from app.services.lottery_query_service import LotteryQueryService


FORMULA_PREFIX = tuple("=+@-\t\r")


def _safe_cell(value: Any) -> str:
    s = "" if value is None else str(value)
    if s and s[0] in FORMULA_PREFIX:
        return "'" + s
    return s


def _slug_filename(*parts: str, ext: str) -> str:
    raw = "-".join(p for p in parts if p)
    raw = raw.lower()
    raw = re.sub(r"[áàäâ]", "a", raw)
    raw = re.sub(r"[éèëê]", "e", raw)
    raw = re.sub(r"[íìïî]", "i", raw)
    raw = re.sub(r"[óòöô]", "o", raw)
    raw = re.sub(r"[úùüû]", "u", raw)
    raw = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-")
    raw = raw[:120] or "export"
    return f"{raw}.{ext}"


def _exports_dir() -> Path:
    root = Path(settings.lottery_exports_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_storage_path(storage_name: str) -> Path:
    root = _exports_dir()
    name = Path(storage_name).name
    if name != storage_name or ".." in storage_name or "/" in storage_name or "\\" in storage_name:
        raise forbidden("Nombre de archivo inválido")
    path = (root / name).resolve()
    if not str(path).startswith(str(root)):
        raise forbidden("Ruta de exportación inválida")
    return path


class LotteryExportService:
    def __init__(self, db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.query = LotteryQueryService(db)
        self.product = LotteryProductService(db, tenant_id=tenant_id, user_id=user_id)

    async def create(self, req: LotteryExportRequest) -> LotteryExportResponse:
        t0 = time.perf_counter()
        rows, meta = await self._collect_rows(req)
        limit = self._row_limit(req.format)
        if len(rows) > limit:
            raise LotteryQueryError(
                "RANGE_TOO_LARGE",
                f"La exportación supera el máximo de {limit} filas para {req.format}. Reduce el rango.",
                details={"row_count": len(rows), "limit": limit},
            )

        title = req.title or f"Exportación {req.query_type}"
        ext = req.format
        filename = _slug_filename("resultados", req.query_type, title, ext=ext)
        storage_name = f"{uuid.uuid4().hex}.{ext}"
        mime = {
            "csv": "text/csv; charset=utf-8",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
        }[req.format]

        if req.format == "csv":
            content = self._build_csv(rows, meta, req)
        elif req.format == "xlsx":
            content = self._build_xlsx(rows, meta, req, title)
        else:
            content = self._build_pdf(rows, meta, req, title)

        max_bytes = settings.lottery_export_max_file_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise LotteryQueryError(
                "RANGE_TOO_LARGE",
                f"Archivo supera {settings.lottery_export_max_file_size_mb} MB.",
            )

        path = _safe_storage_path(storage_name)
        path.write_bytes(content)
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.lottery_export_expiration_minutes)
        row = LotteryExport(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            query_type=req.query_type,
            format=req.format,
            status="ready",
            filename=filename,
            storage_name=storage_name,
            mime_type=mime,
            size_bytes=len(content),
            row_count=len(rows),
            parameters={"query_parameters": req.query_parameters, "title": title},
            expires_at=expires,
        )
        self.db.add(row)
        self.db.add(
            LotteryAuditLog(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                action="export",
                tool_name=f"export_{req.format}",
                parameters={"query_type": req.query_type, "filename": filename, "rows": len(rows)},
                result_count=len(rows),
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        )
        await self.product.record_recent(
            query_type=f"export_{req.format}",
            title=filename,
            parameters={"query_type": req.query_type},
        )
        await self.db.flush()
        return LotteryExportResponse(
            export_id=row.id,
            status=row.status,
            filename=row.filename,
            mime_type=row.mime_type,
            size=row.size_bytes,
            row_count=row.row_count,
            expires_at=row.expires_at,
            download_url=f"/api/v1/lottery/exports/{row.id}/download",
        )

    async def get(self, export_id: uuid.UUID) -> LotteryExport:
        row = await self.db.get(LotteryExport, export_id)
        if not row or row.tenant_id != self.tenant_id or row.user_id != self.user_id:
            raise not_found("Exportación no encontrada")
        return row

    async def download(self, export_id: uuid.UUID) -> tuple[LotteryExport, bytes]:
        row = await self.get(export_id)
        if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            row.status = "expired"
            await self.db.flush()
            raise forbidden("Exportación expirada")
        path = _safe_storage_path(row.storage_name)
        if not path.exists():
            raise not_found("Archivo de exportación no disponible")
        return row, path.read_bytes()

    async def delete(self, export_id: uuid.UUID) -> None:
        row = await self.get(export_id)
        path = _safe_storage_path(row.storage_name)
        if path.exists():
            path.unlink()
        await self.db.delete(row)
        await self.db.flush()

    async def cleanup_expired(self) -> int:
        """Invocable manualmente — sin scheduler."""
        from sqlalchemy import select

        now = datetime.now(timezone.utc)
        q = await self.db.execute(select(LotteryExport).where(LotteryExport.expires_at < now))
        n = 0
        for row in q.scalars().all():
            try:
                p = _safe_storage_path(row.storage_name)
                if p.exists():
                    p.unlink()
            except Exception:  # noqa: BLE001
                pass
            row.status = "expired"
            n += 1
        await self.db.flush()
        return n

    def _row_limit(self, fmt: str) -> int:
        return {
            "csv": settings.lottery_export_max_rows_csv,
            "xlsx": settings.lottery_export_max_rows_xlsx,
            "pdf": settings.lottery_export_max_rows_pdf,
        }[fmt]

    async def _collect_rows(self, req: LotteryExportRequest) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        p = req.query_parameters
        meta: dict[str, Any] = {"query_type": req.query_type, "filters": p}

        def _parse_date(key: str, default: date | None = None) -> date:
            v = p.get(key)
            if not v:
                if default:
                    return default
                raise LotteryQueryError("DATE_INVALID", f"Falta {key}")
            return date.fromisoformat(str(v)) if not isinstance(v, date) else v

        if req.query_type == "by_date":
            res = await self.query.by_date(str(p["lottery"]), _parse_date("date"))
            rows = self._draws_to_rows(res.draws, lottery=str(p["lottery"]))
            meta["lottery"] = str(p["lottery"])
            meta["date"] = str(p.get("date"))
            return rows, meta

        if req.query_type == "range":
            res = await self.query.range(
                str(p["lottery"]),
                _parse_date("from") if p.get("from") else _parse_date("from_date"),
                _parse_date("to") if p.get("to") else _parse_date("to_date"),
                page=1,
                page_size=min(int(p.get("page_size", 500)), 500),
            )
            rows = self._draws_to_rows(res.draws, lottery=str(p["lottery"]))
            return rows, meta

        if req.query_type == "frequencies":
            res = await self.query.frequencies(
                str(p["lottery"]),
                _parse_date("from") if p.get("from") else _parse_date("from_date"),
                _parse_date("to") if p.get("to") else _parse_date("to_date"),
                limit=int(p.get("limit", 50)),
            )
            rows = [
                {"number": i.number, "count": i.count, "percentage": i.percentage}
                for i in res.items
            ]
            return rows, meta

        if req.query_type == "repetitions":
            res = await self.query.repetitions(
                str(p["lottery"]),
                _parse_date("from") if p.get("from") else _parse_date("from_date"),
                _parse_date("to") if p.get("to") else _parse_date("to_date"),
                min_count=int(p.get("min_count", 2)),
            )
            rows = [
                {
                    "number": i.number,
                    "count": i.count,
                    "first_date": str(i.first_date),
                    "last_date": str(i.last_date),
                    "dates": ",".join(str(d) for d in i.dates),
                }
                for i in res.items
            ]
            return rows, meta

        if req.query_type == "next_occurrences":
            res = await self.query.next_occurrences(
                str(p["lottery"]),
                str(p["number"]),
                _parse_date("after_date"),
                limit=int(p.get("limit", 20)),
            )
            rows = [
                {
                    "draw_date": str(i.draw_date),
                    "position": i.position_label,
                    "number": i.number_value,
                    "type": i.number_type,
                }
                for i in res.items
            ]
            return rows, meta

        if req.query_type == "compare":
            res = await self.query.compare(
                list(p["lotteries"]),
                _parse_date("from") if p.get("from") else _parse_date("from_date"),
                _parse_date("to") if p.get("to") else _parse_date("to_date"),
                p.get("mode", "repeated_numbers"),
                limit=int(p.get("limit", 100)),
            )
            items = (res.data or {}).get("items") or []
            rows = [
                {
                    "number": it.get("number"),
                    "lotteries": ",".join(it.get("lotteries") or []),
                    "total": it.get("total"),
                    "dates": ",".join(str(d) for d in (it.get("dates") or [])),
                }
                for it in items
            ]
            return rows, meta

        if req.query_type == "by_number":
            res = await self.query.by_number(
                str(p["lottery"]),
                str(p["number"]),
                from_date=_parse_date("from") if p.get("from") or p.get("from_date") else None,
                to_date=_parse_date("to") if p.get("to") or p.get("to_date") else None,
                page_size=min(int(p.get("page_size", 200)), 500),
            )
            rows = [
                {
                    "draw_date": str(o.draw_date),
                    "position": o.position_label,
                    "number": o.number_value,
                    "type": o.number_type,
                }
                for o in res.occurrences
            ]
            return rows, meta

        # saved_query / cross — flatten parameters dump
        rows = [{"key": k, "value": str(v)} for k, v in p.items()]
        return rows, meta

    def _draws_to_rows(self, draws: list[Any], *, lottery: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for d in draws:
            data = d.model_dump(mode="json") if hasattr(d, "model_dump") else d
            nums = data.get("numbers") or []
            rows.append(
                {
                    "lottery": lottery,
                    "draw_date": data.get("draw_date"),
                    "draw_time": data.get("draw_time"),
                    "game": data.get("game_name"),
                    "source_reference": data.get("source_reference"),
                    "numbers": " ".join(
                        str(n.get("number_raw") or n.get("number_value") or "") for n in nums
                    ),
                    **{
                        f"pos_{n.get('position')}": n.get("number_raw") or n.get("number_value")
                        for n in nums
                    },
                }
            )
        return rows

    def _build_csv(self, rows: list[dict[str, Any]], meta: dict, req: LotteryExportRequest) -> bytes:
        buf = io.StringIO()
        # UTF-8 BOM for Excel
        buf.write("\ufeff")
        if req.include_metadata:
            buf.write(f"# query_type={meta.get('query_type')}\n")
            buf.write(f"# generated_at={datetime.now(timezone.utc).isoformat()}\n")
        if req.include_disclaimer:
            buf.write(f"# {DISCLAIMER}\n")
        if not rows:
            buf.write("message\n")
            buf.write("sin_resultados\n")
            return buf.getvalue().encode("utf-8")
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _safe_cell(row.get(k)) for k in fieldnames})
        return buf.getvalue().encode("utf-8")

    def _build_xlsx(
        self, rows: list[dict[str, Any]], meta: dict, req: LotteryExportRequest, title: str
    ) -> bytes:
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        summary = wb.active
        summary.title = "Resumen"
        summary["A1"] = "JAIOS — Resultados de Loterías"
        summary["A1"].font = Font(bold=True, size=14)
        summary["A2"] = title
        summary["A3"] = f"Tipo: {meta.get('query_type')}"
        summary["A4"] = f"Generado: {datetime.now(timezone.utc).isoformat()}"
        summary["A5"] = f"Filas: {len(rows)}"
        if req.include_disclaimer:
            summary["A7"] = DISCLAIMER

        data = wb.create_sheet("Datos")
        if rows:
            headers = list(rows[0].keys())
            data.append(headers)
            for row in rows:
                data.append([_safe_cell(row.get(h)) for h in headers])
            data.auto_filter.ref = data.dimensions
            data.freeze_panes = "A2"
            for col in data.columns:
                data.column_dimensions[col[0].column_letter].width = 16
        else:
            data.append(["sin_resultados"])

        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    def _build_pdf(
        self, rows: list[dict[str, Any]], meta: dict, req: LotteryExportRequest, title: str
    ) -> bytes:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        _, height = letter
        y = height - 0.7 * inch

        def line(text: str, *, bold: bool = False, size: int = 10) -> None:
            nonlocal y
            if y < inch:
                c.showPage()
                y = height - 0.7 * inch
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(0.7 * inch, y, str(text)[:100])
            y -= 13

        line("JAIOS — Resultados de Loterías", bold=True, size=14)
        line(title, bold=True, size=11)
        line(f"Tipo: {meta.get('query_type')}")
        line(f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        line(f"Registros: {len(rows)}")
        y -= 6
        for row in rows[: settings.lottery_export_max_rows_pdf]:
            if "numbers" in row:
                line(f"{row.get('draw_date')}  {row.get('numbers')}  ref={row.get('source_reference') or '—'}")
            else:
                line(" | ".join(f"{k}={v}" for k, v in list(row.items())[:5]))
        y -= 8
        if req.include_disclaimer:
            line(DISCLAIMER, size=8)
        c.save()
        return buf.getvalue()

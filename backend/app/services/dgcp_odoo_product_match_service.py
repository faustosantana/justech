"""Match líneas DGCP ↔ product.product Odoo (MATCHED / REVIEW_REQUIRED / UNMATCHED).

No crea productos. No inventa. Solo sugiere con confianza.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.dgcp_opportunity import DGCPOpportunity

logger = logging.getLogger(__name__)

MATCH_KEY = "odoo_product_matches"
STATUS_MATCHED = "MATCHED"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_UNMATCHED = "UNMATCHED"

# Umbrales
CONF_EXACT_REF = 0.98
CONF_EXACT_NAME = 0.92
CONF_NAME_BRAND = 0.88
CONF_SIMILAR_HIGH = 0.85  # mínimo para MATCHED automático por similitud
CONF_REVIEW_MIN = 0.55


def _as_int_id(value: Any) -> int:
    if isinstance(value, list):
        value = value[0]
    if isinstance(value, dict) and "id" in value:
        value = value["id"]
    return int(value)


def _norm(text: str | None) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


class DGCPOdooProductMatchService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def _client(self):
        from app.services.odoo_service import OdooService

        return await OdooService(self.db, self.tenant_id, user_id=self.user_id)._bare_client()

    def extract_lines(self, opportunity: DGCPOpportunity) -> list[dict[str, Any]]:
        """Extrae líneas estructuradas desde Hermes / fichas / full_info. Conserva texto original."""
        lines: list[dict[str, Any]] = []
        info = opportunity.full_info or {}

        # 1) Explicit structured lines (UAT / UI)
        for i, raw in enumerate(info.get("dgcp_line_items") or [], start=1):
            if not isinstance(raw, dict):
                continue
            lines.append(self._normalize_line(raw, default_no=i))

        # 2) Hermes items_detected via bid package (best-effort sync load)
        try:
            from sqlalchemy import select
            from app.models.dgcp_bid_package import DGCPBidPackage

            # note: caller may not await — keep sync extraction from opportunity only here
        except Exception:
            pass

        hermes_items = info.get("hermes_items_detected") or []
        if not hermes_items and isinstance(info.get("hermes_document_analysis"), dict):
            hermes_items = info["hermes_document_analysis"].get("items_detected") or []
        for i, raw in enumerate(hermes_items, start=1):
            if isinstance(raw, dict):
                lines.append(
                    self._normalize_line(
                        {
                            "line_number": raw.get("line_number") or i,
                            "description": raw.get("name") or raw.get("label") or raw.get("description"),
                            "quantity": raw.get("quantity") or raw.get("qty") or 1,
                            "uom": raw.get("uom") or raw.get("unit"),
                            "brand": raw.get("brand") or raw.get("marca"),
                            "model": raw.get("model") or raw.get("modelo"),
                            "reference": raw.get("sku") or raw.get("reference") or raw.get("default_code"),
                            "specs": raw.get("specs") or raw.get("notes"),
                            "estimated_price": raw.get("price") or raw.get("unit_price"),
                            "currency": raw.get("currency") or opportunity.currency,
                            "original_text": raw.get("original_text")
                            or raw.get("name")
                            or raw.get("label"),
                        },
                        default_no=i,
                    )
                )

        # 3) Suggested products block
        for i, raw in enumerate(info.get("suggested_products") or [], start=1):
            if isinstance(raw, dict):
                lines.append(
                    self._normalize_line(
                        {
                            "description": raw.get("product_name") or raw.get("name"),
                            "quantity": raw.get("quantity") or 1,
                            "reference": raw.get("sku"),
                            "estimated_price": raw.get("unit_price") or raw.get("price"),
                            "original_text": raw.get("product_name") or raw.get("name"),
                        },
                        default_no=len(lines) + 1,
                    )
                )

        # Dedupe by description+ref
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for ln in lines:
            key = f"{_norm(ln.get('reference'))}|{_norm(ln.get('description'))}"
            if not ln.get("description") and not ln.get("reference"):
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(ln)
        for idx, ln in enumerate(out, start=1):
            ln["line_number"] = ln.get("line_number") or idx
        return out

    async def extract_lines_async(self, opportunity: DGCPOpportunity) -> list[dict[str, Any]]:
        lines = self.extract_lines(opportunity)
        if lines:
            return lines
        # Enrich from bid package hermes
        try:
            from sqlalchemy import select
            from app.models.dgcp_bid_package import DGCPBidPackage

            pkg = (
                await self.db.execute(
                    select(DGCPBidPackage).where(
                        DGCPBidPackage.opportunity_id == opportunity.id,
                        DGCPBidPackage.tenant_id == self.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if not pkg:
                return lines
            hermes = (pkg.manifest or {}).get("hermes_document_analysis") or {}
            items = hermes.get("items_detected") or []
            sheets = ((pkg.payload or {}).get("technical_sheets") or {}).get("items") or []
            for i, raw in enumerate(items, start=1):
                if isinstance(raw, dict):
                    lines.append(
                        self._normalize_line(
                            {
                                "description": raw.get("name") or raw.get("label"),
                                "quantity": raw.get("quantity") or 1,
                                "reference": raw.get("sku") or raw.get("reference"),
                                "brand": raw.get("brand"),
                                "model": raw.get("model"),
                                "specs": raw.get("notes"),
                                "original_text": raw.get("name") or raw.get("label"),
                            },
                            default_no=i,
                        )
                    )
            for i, item in enumerate(sheets, start=len(lines) + 1):
                offered = (item or {}).get("offered_product") or {}
                name = (
                    offered.get("name")
                    or offered.get("product_name")
                    or item.get("title")
                    or item.get("requirement")
                )
                if name:
                    lines.append(
                        self._normalize_line(
                            {
                                "description": name,
                                "quantity": offered.get("quantity") or item.get("quantity") or 1,
                                "reference": offered.get("sku") or offered.get("default_code"),
                                "estimated_price": offered.get("unit_price") or offered.get("price"),
                                "original_text": name,
                            },
                            default_no=i,
                        )
                    )
        except Exception:
            logger.debug("extract from bid package failed", exc_info=True)
        return lines

    @staticmethod
    def _normalize_line(raw: dict[str, Any], *, default_no: int) -> dict[str, Any]:
        return {
            "line_number": int(raw.get("line_number") or default_no),
            "description": (raw.get("description") or "")[:500],
            "quantity": float(raw.get("quantity") or 1),
            "uom": raw.get("uom") or "",
            "specs": (raw.get("specs") or "")[:1000],
            "brand": (raw.get("brand") or "")[:120],
            "model": (raw.get("model") or "")[:120],
            "reference": (raw.get("reference") or "")[:120],
            "estimated_price": float(raw.get("estimated_price") or 0) or None,
            "currency": raw.get("currency") or "DOP",
            "lot": raw.get("lot") or "",
            "original_text": (raw.get("original_text") or raw.get("description") or "")[:1000],
        }

    async def match_line(self, client, line: dict[str, Any]) -> dict[str, Any]:
        """Busca candidatos Odoo. MATCHED solo con umbral alto / exactitud."""
        ref = (line.get("reference") or "").strip()
        model = (line.get("model") or "").strip()
        brand = (line.get("brand") or "").strip()
        desc = (line.get("description") or "").strip()
        candidates: list[dict[str, Any]] = []

        async def _search(domain: list, method: str, conf: float) -> None:
            rows = await client.search_read(
                "product.product",
                domain + [("sale_ok", "=", True)],
                ["id", "name", "default_code", "barcode", "list_price", "display_name"],
                limit=5,
            )
            for r in rows:
                candidates.append(
                    {
                        "product_id": _as_int_id(r["id"]),
                        "name": r.get("display_name") or r.get("name"),
                        "default_code": r.get("default_code") or "",
                        "barcode": r.get("barcode") or "",
                        "list_price": float(r.get("list_price") or 0),
                        "confidence": conf,
                        "method": method,
                    }
                )

        if ref:
            await _search([("default_code", "=", ref)], "exact_reference", CONF_EXACT_REF)
            if not candidates:
                await _search([("barcode", "=", ref)], "exact_barcode", CONF_EXACT_REF)

        if model and not any(c["confidence"] >= CONF_EXACT_REF for c in candidates):
            await _search([("default_code", "=ilike", model)], "exact_model_code", CONF_EXACT_REF)
            await _search([("name", "=ilike", model)], "exact_model_name", CONF_EXACT_NAME)

        if desc and not any(c["confidence"] >= CONF_EXACT_NAME for c in candidates):
            await _search([("name", "=ilike", desc[:80])], "exact_name", CONF_EXACT_NAME)

        if brand and desc and not any(c["confidence"] >= CONF_NAME_BRAND for c in candidates):
            needle = f"%{brand}%{desc[:40]}%"
            await _search([("name", "ilike", f"{brand}")], "brand_name", CONF_NAME_BRAND - 0.05)
            # tighten: name contains brand and a token from desc
            tokens = [t for t in re.split(r"\W+", desc) if len(t) >= 4][:2]
            for tok in tokens:
                await _search(
                    ["&", ("name", "ilike", brand), ("name", "ilike", tok)],
                    "name_brand",
                    CONF_NAME_BRAND,
                )

        if desc and not candidates:
            tokens = [t for t in re.split(r"\W+", desc) if len(t) >= 5][:3]
            if len(tokens) == 1:
                await _search([("name", "ilike", tokens[0])], "token_similarity", CONF_SIMILAR_HIGH - 0.05)
            elif len(tokens) >= 2:
                domain: list[Any] = ["&", ("name", "ilike", tokens[0]), ("name", "ilike", tokens[1])]
                await _search(domain, "token_similarity", CONF_SIMILAR_HIGH - 0.05)

        # Dedupe by product_id keeping highest confidence
        by_id: dict[int, dict[str, Any]] = {}
        for c in candidates:
            pid = c["product_id"]
            if pid not in by_id or c["confidence"] > by_id[pid]["confidence"]:
                by_id[pid] = c
        ranked = sorted(by_id.values(), key=lambda x: x["confidence"], reverse=True)

        status = STATUS_UNMATCHED
        suggested = None
        if len(ranked) == 1 and ranked[0]["confidence"] >= CONF_SIMILAR_HIGH:
            status = STATUS_MATCHED
            suggested = ranked[0]
        elif len(ranked) == 1 and ranked[0]["confidence"] >= CONF_REVIEW_MIN:
            status = STATUS_REVIEW
            suggested = ranked[0]
        elif len(ranked) > 1:
            status = STATUS_REVIEW
            suggested = ranked[0] if ranked[0]["confidence"] >= CONF_REVIEW_MIN else None
        elif ranked and ranked[0]["confidence"] >= CONF_REVIEW_MIN:
            status = STATUS_REVIEW
            suggested = ranked[0]

        return {
            **line,
            "status": status,
            "confidence": suggested["confidence"] if suggested else 0.0,
            "match_method": suggested["method"] if suggested else None,
            "suggested_product_id": suggested["product_id"] if suggested else None,
            "suggested_product_name": suggested["name"] if suggested else None,
            "suggested_default_code": suggested["default_code"] if suggested else None,
            "candidates": ranked[:5],
            "approved": False,
            "approved_by": None,
            "approved_at": None,
        }

    async def run_match(self, opportunity: DGCPOpportunity) -> dict[str, Any]:
        client = await self._client()
        if not client.is_configured:
            return {"ok": False, "error": "odoo_not_configured", "lines": []}

        lines = await self.extract_lines_async(opportunity)
        results = []
        for line in lines:
            try:
                results.append(await self.match_line(client, line))
            except Exception as exc:
                logger.warning("match_line failed: %s", exc)
                results.append({**line, "status": STATUS_UNMATCHED, "error": str(exc), "candidates": []})

        blob = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lines": results,
            "summary": {
                "total": len(results),
                "matched": sum(1 for r in results if r.get("status") == STATUS_MATCHED),
                "review_required": sum(1 for r in results if r.get("status") == STATUS_REVIEW),
                "unmatched": sum(1 for r in results if r.get("status") == STATUS_UNMATCHED),
            },
        }
        info = dict(opportunity.full_info or {})
        info[MATCH_KEY] = blob
        opportunity.full_info = info
        flag_modified(opportunity, "full_info")
        return {"ok": True, **blob}

    def approve_line(
        self,
        opportunity: DGCPOpportunity,
        *,
        line_number: int,
        product_id: int | None = None,
        approve: bool = True,
        user_id: uuid.UUID | None = None,
        user_name: str | None = None,
    ) -> dict[str, Any]:
        info = dict(opportunity.full_info or {})
        blob = dict(info.get(MATCH_KEY) or {})
        lines = list(blob.get("lines") or [])
        found = None
        for ln in lines:
            if int(ln.get("line_number") or 0) == int(line_number):
                found = ln
                break
        if not found:
            return {"ok": False, "error": "line_not_found"}
        if approve:
            if product_id:
                cand = next(
                    (c for c in (found.get("candidates") or []) if c.get("product_id") == product_id),
                    None,
                )
                found["suggested_product_id"] = product_id
                if cand:
                    found["suggested_product_name"] = cand.get("name")
                    found["suggested_default_code"] = cand.get("default_code")
                    found["confidence"] = cand.get("confidence") or found.get("confidence")
                    found["match_method"] = cand.get("method") or "user_selected"
                found["status"] = STATUS_MATCHED
            elif not found.get("suggested_product_id"):
                return {"ok": False, "error": "no_product_to_approve"}
            else:
                found["status"] = STATUS_MATCHED
            found["approved"] = True
            found["approved_by"] = str(user_id or self.user_id)
            found["approved_name"] = user_name
            found["approved_at"] = datetime.now(timezone.utc).isoformat()
        else:
            found["approved"] = False
            found["approved_by"] = None
            found["approved_at"] = None
            if found.get("status") == STATUS_MATCHED and len(found.get("candidates") or []) > 1:
                found["status"] = STATUS_REVIEW
        blob["lines"] = lines
        blob["summary"] = {
            "total": len(lines),
            "matched": sum(1 for r in lines if r.get("status") == STATUS_MATCHED),
            "review_required": sum(1 for r in lines if r.get("status") == STATUS_REVIEW),
            "unmatched": sum(1 for r in lines if r.get("status") == STATUS_UNMATCHED),
            "approved": sum(1 for r in lines if r.get("approved")),
        }
        info[MATCH_KEY] = blob
        opportunity.full_info = info
        try:
            flag_modified(opportunity, "full_info")
        except Exception:
            pass
        return {"ok": True, "line": found, "summary": blob["summary"]}

    def approved_matched_lines(self, opportunity: DGCPOpportunity) -> list[dict[str, Any]]:
        blob = (opportunity.full_info or {}).get(MATCH_KEY) or {}
        out = []
        for ln in blob.get("lines") or []:
            if ln.get("status") == STATUS_MATCHED and ln.get("approved") and ln.get("suggested_product_id"):
                out.append(ln)
            # Auto-include high-confidence MATCHED without explicit reject
            elif (
                ln.get("status") == STATUS_MATCHED
                and ln.get("suggested_product_id")
                and float(ln.get("confidence") or 0) >= CONF_EXACT_NAME
                and ln.get("approved") is not False
            ):
                # Require explicit approve for quotation per mandate
                continue
        return out

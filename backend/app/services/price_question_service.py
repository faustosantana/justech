"""Consultas de precios para el Assistant — usa BD indexada, no Excel."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantLink, AssistantQueryResponse
from app.services.business_answer_builder import build_business_answer, links_to_dict
from app.services.price_intelligence_service import PriceIntelligenceService, PriceSearchFilters
from app.services.price_normalizer import detect_brand, parse_ram_gb, parse_storage


class PriceQuestionService:
    PRICE_SIGNALS = (
        "precio", "precios", "lista de precios", "listas de precios",
        "me sale mejor", "más barata", "mas barata", "más barato", "mas barato",
        "proveedor tiene mejor", "quien me sale", "quién me sale",
        "cuál proveedor", "cual proveedor", "comparar", "alternativas",
        "cotizar", "cotización", "cotizacion",
    )
    PRODUCT_HINTS = ("laptop", "notebook", "monitor", "desktop", "computadora", "portátil", "portatil")

    @classmethod
    def is_price_question(cls, question: str) -> bool:
        lowered = question.lower()
        if any(
            sig in lowered
            for sig in (
                "hemos vendido", "vendimos", "clientes compraron", "le hemos vendido",
                "nos vendió", "nos vendio", "hemos comprado", "le compramos",
                "licitaciones", "licitación", "licitacion",
            )
        ):
            return False
        if any(sig in lowered for sig in cls.PRICE_SIGNALS):
            return True
        if any(p in lowered for p in cls.PRODUCT_HINTS):
            return any(
                k in lowered
                for k in ("precio", "lista", "me sale", "barat", "stock", "disponible", "proveedor", "cotiz", "busca")
            )
        return False

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.svc = PriceIntelligenceService(db, tenant_id)

    async def answer(self, question: str) -> AssistantQueryResponse:
        filters = self._parse_question(question)
        compare_mode = any(
            k in question.lower()
            for k in ("me sale mejor", "más barata", "mas barata", "más barato", "mas barato", "comparar", "alternativas")
        )

        if "lista" in question.lower() and any(k in question.lower() for k in ("tenemos", "hay", "cuáles", "cuales")):
            return await self._answer_supplier_lists(question, filters)

        if compare_mode:
            result = await self.svc.compare(filters, question=question)
            return self._compare_response(question, result)

        search = await self.svc.search(filters)
        if not search.items:
            return AssistantQueryResponse(
                question=question,
                answer=(
                    "No encontré productos indexados para esa consulta. "
                    "Verifica que las listas estén en 03_PROVEEDORES y ejecuta make prices-sync."
                ),
                sources=["price_intelligence"],
                query_type="price_query",
            )

        top = search.items[:8]
        rows = []
        for p in top:
            price_val = p.preferred_price or p.price
            date_l = p.source_file_date.strftime("%d/%m/%Y") if p.source_file_date else "—"
            rows.append([
                p.supplier or "—",
                (p.description or p.sku or "—")[:80],
                f"{p.currency} {price_val}" if price_val else "—",
                p.stock if p.stock is not None else "—",
                f"{p.source_filename} ({date_l})",
            ])
        best_price = top[0].preferred_price or top[0].price
        best_date = top[0].source_file_date.strftime("%d/%m/%Y") if top[0].source_file_date else "sin fecha"
        structured = build_business_answer(
            intent="price_query",
            source="price_intelligence",
            summary=(
                f"Encontré {search.total} producto(s) en listas comerciales indexadas. "
                f"Mejor precio: {top[0].currency} {best_price} ({top[0].supplier}). "
                f"Lista del {best_date} — {top[0].source_filename} / {top[0].source_sheet} fila {top[0].source_row}."
            ),
            tables=[{
                "title": "Alternativas",
                "columns": ["Proveedor", "Producto", "Precio", "Stock", "Fuente"],
                "rows": rows,
            }],
        )
        links = [
            AssistantLink(label="Inteligencia de Precios", url="/prices", type="module"),
        ]
        structured["links"] = links_to_dict(links)
        if search.items[0].source_filename:
            structured["source_file"] = search.items[0].source_filename

        return AssistantQueryResponse(
            question=question,
            answer=structured["summary"],
            sources=["price_intelligence"],
            query_type="price_query",
            structured_data=structured,
            links=links,
        )

    async def _answer_supplier_lists(self, question: str, filters: PriceSearchFilters) -> AssistantQueryResponse:
        brand = filters.brand or detect_brand(question)
        if not brand:
            return AssistantQueryResponse(
                question=question,
                answer="Indica el proveedor o marca (ej. Dell, Lenovo) para listar archivos indexados.",
                sources=["price_intelligence"],
                query_type="price_query",
            )
        files = await self.svc.list_supplier_files(brand)
        if not files:
            return AssistantQueryResponse(
                question=question,
                answer=f"No hay listas de precios indexadas de {brand}. Ejecuta make prices-sync.",
                sources=["price_intelligence"],
                query_type="price_query",
            )
        lines = [
            f"• {f.filename} — {f.total_records} productos ({f.file_modified_at.strftime('%d/%m/%Y') if f.file_modified_at else 'sin fecha'})"
            for f in files
        ]
        summary = f"Listas de precios indexadas de {brand}:\n" + "\n".join(lines)
        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["price_intelligence"],
            query_type="price_query",
        )

    def _compare_response(self, question: str, result) -> AssistantQueryResponse:
        best = result.best_product
        rows = []
        if best:
            bp = best.preferred_price or best.price
            bdate = best.source_file_date.strftime("%d/%m/%Y") if best.source_file_date else "—"
            rows.append([
                best.supplier or "—",
                (best.description or best.sku or "—")[:80],
                f"{best.currency} {bp}" if bp else "—",
                best.stock if best.stock is not None else "—",
                f"{best.source_filename} / {best.source_sheet} fila {best.source_row} ({bdate})",
            ])
        for alt in result.alternatives:
            ap = alt.preferred_price or alt.price
            adate = alt.file_date.strftime("%d/%m/%Y") if alt.file_date else "—"
            rows.append([
                alt.supplier or "—",
                (alt.description or alt.sku or "—")[:80],
                f"{alt.currency} {ap}" if ap else "—",
                alt.stock if alt.stock is not None else "—",
                f"{alt.source_filename} / {alt.source_sheet} ({adate})",
            ])

        structured = build_business_answer(
            intent="price_compare",
            source="price_intelligence",
            summary=result.summary,
            tables=[{
                "title": "Comparación de proveedores",
                "columns": ["Proveedor", "Producto", "Precio", "Stock", "Fuente"],
                "rows": rows,
            }],
            warnings=result.warnings,
        )
        links = [AssistantLink(label="Comparar en Inteligencia de Precios", url="/prices", type="module")]
        structured["links"] = links_to_dict(links)
        if best:
            structured["best_option"] = {
                "supplier": best.supplier,
                "price": str(best.preferred_price or best.price),
                "currency": best.currency,
                "source": best.source_filename,
            }

        return AssistantQueryResponse(
            question=question,
            answer=result.summary,
            sources=["price_intelligence"],
            query_type="price_compare",
            structured_data=structured,
            links=links,
        )

    def _parse_question(self, question: str) -> PriceSearchFilters:
        lowered = question.lower()
        filters = PriceSearchFilters(limit=25)

        brand = detect_brand(question)
        if brand:
            filters.brand = brand

        if "laptop" in lowered or "notebook" in lowered:
            filters.product_type = "laptop"
            if not filters.q:
                filters.q = "laptop"
        elif "monitor" in lowered:
            filters.category = "monitor"
        elif any(k in lowered for k in ("desktop", "escritorio", "computadora")):
            filters.category = "desktop"

        ram = parse_ram_gb(question)
        if ram:
            filters.ram_gb = ram

        storage_gb, _ = parse_storage(question)
        if storage_gb:
            filters.storage_gb = storage_gb

        proc_match = re.search(r"\bi[3579]\s*-?\s*\d+\w*\b", lowered)
        if proc_match:
            filters.processor = proc_match.group(0).upper()

        if any(k in lowered for k in ("disponible", "con stock", "en stock")):
            filters.stock_disponible = True

        if "dell" in lowered and not filters.brand:
            filters.brand = "Dell"
        if "lenovo" in lowered and not filters.brand:
            filters.brand = "Lenovo"

        price_match = re.search(r"(\d+)\s*(?:usd|us\$|\$)", lowered)
        if price_match:
            filters.price_max = Decimal(price_match.group(1))

        return filters

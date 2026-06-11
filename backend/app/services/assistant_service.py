"""JAIOS Assistant — motor de consultas empresariales (read-only)."""

from __future__ import annotations

import re
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.router import AssistantRouter, AssistantSource
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.assistant import AssistantCard, AssistantLink, AssistantQueryRequest, AssistantQueryResponse
from app.schemas.dgcp import OpportunityStatus
from app.schemas.odoo import OdooInvoiceResponse, OdooSaleHistoryItem
from app.services.dgcp_service import DGCPService
from app.models.user import User
from app.services.m365_service import M365Service
from app.services.odoo_detail_service import OdooDetailService
from app.services.odoo_query_service import OdooQueryService
from app.services.odoo_service import OdooService
from app.services.business_answer_builder import build_business_answer, links_to_dict, not_found_summary
from app.services.assistant_conversation_context import ConversationContextStore
from app.services.conversation_follow_up_resolver import resolve_follow_up
from app.services.assistant_context_policy import (
    is_customer_record_question,
    is_dgcp_record_question,
    is_invoice_record_question,
    is_product_record_question,
)
from app.services.business_intent_router import BusinessIntent, BusinessIntentRouter
from app.services.business_terms import detect_product_in_text
from app.services.business_entity_normalizer import normalize_product
from app.services.corporate_knowledge_question_service import CorporateKnowledgeQuestionService
from app.services.dgcp_requirements_question_service import DgcpRequirementsQuestionService
from app.services.document_question_service import DocumentQuestionService
from app.services.dgcp_question_service import DgcpQuestionService
from app.services.enterprise_search_service import EnterpriseSearchService
from app.services.purchase_question_service import PurchaseQuestionService
from app.services.price_question_service import PriceQuestionService
from app.services.routing_service import RoutingService
from app.services.sales_question_service import SalesQuestionService
from app.services.task_service import TaskService
from app.services.tasks_question_service import TasksQuestionService
from app.config import settings
from app.services.persistent_conversation_store import PersistentConversationStore
from app.services.assistant_synthesis_service import AssistantSynthesisService
from app.services.semantic_resolver_engine import SemanticResolverEngine, SemanticResolution
from app.services.hermes_retrieval_service import HermesRetrievalService

READ_ONLY_NOTICE = "No puedo modificar Odoo. Esta integración está en modo solo lectura."
M365_NOT_CONNECTED = (
    "Microsoft 365 todavía no está conectado. "
    "Cuando esté conectado podré buscar correos y adjuntos."
)

WRITE_PATTERNS = (
    "modificar", "modifica", "crear", "crea", "eliminar", "elimina", "borrar",
    "actualizar", "actualiza", "confirmar", "validar", "cancelar", "escribir",
    "write", "create", "delete", "update", "unlink", "action_confirm",
    "action_post", "button_validate",
)


class AssistantService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.odoo = OdooService(db, tenant_id, user_id=user_id)
        self.odoo_query = OdooQueryService(db, tenant_id, user_id=user_id)
        self.odoo_detail = OdooDetailService(self.odoo)
        self.dgcp = DGCPService(db)
        self.m365 = M365Service(db, tenant_id, user_id=user_id)
        self.tasks = TaskService(db, tenant_id, user_id=user_id)
        self.routing = RoutingService(db, tenant_id)

    async def query(self, payload: AssistantQueryRequest) -> AssistantQueryResponse:
        persistent = PersistentConversationStore(self.db, self.tenant_id, self.user_id)
        if settings.assistant_persist_conversations and payload.conversation_id:
            conv = await persistent.load_context(payload.conversation_id)
        else:
            conv = ConversationContextStore.get(
                self.tenant_id, self.user_id, payload.conversation_id
            )
        original_question = payload.question.strip()
        if ConversationContextStore.should_reset(original_question):
            conv.reset()
            if settings.assistant_persist_conversations and payload.conversation_id:
                await persistent.reset_conversation(payload.conversation_id)
        resolution = resolve_follow_up(original_question, conv)
        semantic = await SemanticResolverEngine(self.db, self.tenant_id).resolve(
            resolution.question if resolution.was_follow_up else original_question
        )
        routed_question = semantic.rewritten or resolution.question
        effective_payload = payload.model_copy(update={"question": routed_question})
        result = await self._execute_query(effective_payload, conv, resolution, semantic)
        scope_label = None
        if self.user_id:
            from app.services.global_company_context_service import GlobalCompanyContextService

            global_ctx = await GlobalCompanyContextService(
                self.db, self.tenant_id, self.user_id
            ).get_context()
            scope_label = global_ctx.scope_label
        result = await self._finalize_response(
            effective_payload, result, conv, resolution, original_question, scope_label, persistent
        )
        if settings.assistant_persist_conversations:
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
        return result

    async def _finalize_response(
        self,
        payload: AssistantQueryRequest,
        result: AssistantQueryResponse,
        conv,
        resolution,
        original_question: str,
        scope_label: str | None = None,
        persistent: PersistentConversationStore | None = None,
    ) -> AssistantQueryResponse:
        ConversationContextStore.update_from_response(
            conv,
            query_type=result.query_type,
            data=result.data,
            record_type=payload.record_type,
            record_id=payload.current_record_id,
        )
        if result.query_type == "sales_query" and result.data:
            ConversationContextStore.update_from_sales(
                conv,
                product_label=result.data.get("product_label"),
                product_terms=result.data.get("search_terms"),
                customer_label=result.data.get("customer_label"),
                intent=result.data.get("intent"),
                year_filter=result.data.get("year_filter"),
            )
        if payload.record_type in ("dgcp", "dgcp_opportunity") and payload.current_record_id:
            conv.current_bid_id = payload.current_record_id
        if scope_label:
            conv.current_company_scope = scope_label
        ConversationContextStore.save(
            self.tenant_id, self.user_id, payload.conversation_id, conv
        )
        synthesizer = AssistantSynthesisService(self.db, self.tenant_id)
        facts = dict(result.data or {})
        if result.structured_data and isinstance(result.structured_data, dict):
            facts["structured"] = result.structured_data
        result.answer = await synthesizer.synthesize_answer(
            question=original_question,
            template_answer=result.answer,
            query_type=result.query_type,
            sources=result.sources,
            facts=facts,
            conversation_context=conv.to_debug_dict(),
        )
        if persistent and settings.assistant_persist_conversations and payload.conversation_id:
            try:
                await persistent.save_context(
                    payload.conversation_id,
                    conv,
                    module_context=payload.current_module,
                    company_context_id=payload.current_company_context,
                )
                await persistent.append_exchange(
                    payload.conversation_id,
                    user_question=original_question,
                    assistant_response=result,
                )
            except Exception:
                pass
        result.was_follow_up = resolution.was_follow_up
        if resolution.was_follow_up:
            result.resolved_question = resolution.question
            ctx_note = conv.to_debug_dict()
            if payload.debug_context:
                result.conversation_context = ctx_note
            elif result.structured_data and isinstance(result.structured_data, dict):
                warnings = list(result.structured_data.get("warnings") or [])
                active = ctx_note.get("producto") or ctx_note.get("cliente")
                if active:
                    warnings.insert(0, f"Contexto activo: producto/cliente = {active}")
                result.structured_data["warnings"] = warnings[:5]
        elif payload.debug_context:
            result.conversation_context = conv.to_debug_dict()
        if scope_label:
            if result.structured_data and isinstance(result.structured_data, dict):
                warnings = list(result.structured_data.get("warnings") or [])
                if scope_label not in warnings:
                    warnings.insert(0, scope_label)
                result.structured_data["warnings"] = warnings[:5]
            else:
                result.structured_data = {"type": "business_answer", "warnings": [scope_label]}
            result.data = dict(result.data or {})
            result.data["company_scope"] = scope_label
        result.question = original_question
        return result

    async def _execute_query(
        self,
        payload: AssistantQueryRequest,
        conv,
        resolution,
        semantic: SemanticResolution | None = None,
    ) -> AssistantQueryResponse:
        q = payload.question.strip()
        if not q:
            return AssistantQueryResponse(
                question=q,
                answer="Escribe una pregunta sobre clientes, facturas, productos, DGCP u oportunidades.",
                sources=["jaios"],
                query_type="empty",
            )

        from app.services.company_access_guard import assistant_company_access_message

        denied = await assistant_company_access_message(
            self.db, self.tenant_id, self.user_id, q
        )
        if denied:
            return AssistantQueryResponse(
                question=q,
                answer=denied,
                sources=["jaios"],
                query_type="company_access_denied",
            )

        lowered = q.lower()
        sources = AssistantRouter.detect_sources(q, payload.current_module)
        source_labels = [AssistantRouter.source_label(s) for s in sources if s not in AssistantRouter.FUTURE_SOURCES]

        is_task_create = "tarea" in lowered and any(k in lowered for k in ("crea", "crear", "asigna", "asignar"))
        if any(p in lowered for p in WRITE_PATTERNS) and not is_task_create:
            return AssistantQueryResponse(
                question=q,
                answer=READ_ONLY_NOTICE,
                sources=["jaios"],
                query_type="write_blocked",
                read_only_notice=READ_ONLY_NOTICE,
            )

        if is_task_create:
            work_result = await self._answer_work(q, lowered, payload)
            if work_result:
                return work_result

        classified = BusinessIntentRouter.classify(q)

        dgcp_result = await self._try_dgcp_record_answer(q, payload, source_labels)
        if dgcp_result is not None:
            return dgcp_result

        if SalesQuestionService.has_sales_signal(q) or (
            resolution.was_follow_up and conv.current_product
        ):
            sales_svc = SalesQuestionService(self.db, self.tenant_id, self.user_id)
            sales_result = await sales_svc.answer(
                q, source_labels=source_labels, conversation_context=conv
            )
            if sales_result is not None:
                return sales_result

        if PriceQuestionService.is_price_question(q) or classified.intent == BusinessIntent.PRICE:
            if classified.sub_intent == "search" and classified.product_label:
                sales_svc = SalesQuestionService(self.db, self.tenant_id, self.user_id)
                product_result = await sales_svc.answer_product_lookup(
                    q, source_labels=source_labels
                )
                if product_result is not None:
                    return product_result
            result = await PriceQuestionService(self.db, self.tenant_id).answer(q)
            if (
                classified.sub_intent == "search"
                and classified.product_label
                and "No encontré productos indexados" in result.answer
            ):
                sales_svc = SalesQuestionService(self.db, self.tenant_id, self.user_id)
                product_result = await sales_svc.answer_product_lookup(
                    q, source_labels=source_labels
                )
                if product_result is not None:
                    return product_result
            result.sources = list(dict.fromkeys(["price_intelligence"] + source_labels + result.sources))
            return result

        product_label, product_terms = detect_product_in_text(q)
        if product_label and classified.intent == BusinessIntent.NONE:
            sales_svc = SalesQuestionService(self.db, self.tenant_id, self.user_id)
            disambig = await sales_svc.answer_product_disambiguation(
                q, source_labels=source_labels, conversation_context=conv
            )
            if disambig is not None:
                return disambig
            sales_result = await sales_svc.answer(
                q, source_labels=source_labels, conversation_context=conv
            )
            if sales_result is not None and (sales_result.data or {}).get("lines", 1) != 0:
                if sales_result.query_type != "sales_query" or "No encontré" not in sales_result.answer:
                    return sales_result
            price_result = await PriceQuestionService(self.db, self.tenant_id).answer(q)
            if price_result and "No encontré productos indexados" not in price_result.answer:
                price_result.sources = list(dict.fromkeys(["price_intelligence"] + source_labels + price_result.sources))
                return price_result
            if sales_result is not None:
                return sales_result

        if classified.intent == BusinessIntent.ENTERPRISE_SEARCH and classified.search_term:
            return await self._answer_enterprise_search(classified.search_term, source_labels)

        if classified.intent == BusinessIntent.DOCUMENT:
            result = await DocumentQuestionService(
                self.db, self.tenant_id, self.user_id
            ).answer(
                q,
                sub_intent=classified.sub_intent,
                search_term=classified.search_term,
            )
            result.sources = list(dict.fromkeys(["documents"] + source_labels + result.sources))
            return result

        if CorporateKnowledgeQuestionService.is_knowledge_question(q):
            result_data = await CorporateKnowledgeQuestionService(
                self.db, self.tenant_id
            ).answer(q)
            return AssistantQueryResponse(
                question=q,
                answer=result_data["answer"],
                sources=list(dict.fromkeys(["knowledge_repository"] + source_labels)),
                query_type=result_data["query_type"],
            )

        if classified.intent == BusinessIntent.SALES:
            sales_svc = SalesQuestionService(self.db, self.tenant_id, self.user_id)
            sales_result = await sales_svc.answer(
                q, source_labels=source_labels, conversation_context=conv
            )
            if sales_result is not None:
                return sales_result

        if classified.intent in (BusinessIntent.PURCHASE, BusinessIntent.SUPPLIER):
            from app.services.supplier_question_service import SupplierQuestionService

            supplier_result = await SupplierQuestionService(
                self.db, self.tenant_id, self.user_id
            ).answer(q, classified)
            if supplier_result is not None:
                return supplier_result
            result = await PurchaseQuestionService(self.db, self.tenant_id, self.user_id).answer(q, classified)
            if result:
                return result

        if classified.intent == BusinessIntent.CUSTOMER_FINANCE:
            return await self._answer_customer_debt(q, source_labels, classified.customer_label)

        if classified.intent == BusinessIntent.TASKS:
            return await TasksQuestionService(self.db, self.tenant_id, self.user_id).answer(q, classified)

        if classified.intent == BusinessIntent.DGCP:
            result = await DgcpQuestionService(self.db, self.tenant_id).answer(q, classified)
            result.sources = list(dict.fromkeys(source_labels + result.sources))
            return result

        if classified.intent == BusinessIntent.M365:
            from app.services.m365_assistant_service import M365AssistantService

            return await M365AssistantService(self.db, self.tenant_id, self.user_id).answer(q)

        # Contexto de registro — solo si la pregunta aplica al registro activo
        if payload.record_type == "invoice" and payload.current_record_id:
            if is_invoice_record_question(q, classified):
                return await self._answer_invoice_context(q, int(payload.current_record_id), source_labels)

        if payload.record_type == "customer" and payload.current_record_id:
            if is_customer_record_question(q, classified):
                return await self._answer_customer_context(q, int(payload.current_record_id), source_labels)

        if payload.record_type == "product" and payload.current_record_id:
            if is_product_record_question(q, classified):
                return await self._answer_product_context(q, int(payload.current_record_id), source_labels)

        odoo_health = await self.odoo.health()
        if odoo_health.connected and AssistantSource.ODOO in sources:
            odoo_res = await self.odoo_query.answer(q)
            if odoo_res.query_type not in ("help", "empty"):
                cards: list[AssistantCard] = []
                links: list[AssistantLink] = []
                if odoo_res.data:
                    if odoo_res.query_type in ("last_price", "sold_price", "average_price"):
                        partner = odoo_res.data.get("partner_name")
                        if partner:
                            links.append(AssistantLink(label=partner, url="/odoo", type="customer"))
                    if "invoices" in odoo_res.data:
                        for inv in odoo_res.data.get("invoices", [])[:5]:
                            if isinstance(inv, dict) and inv.get("id"):
                                links.append(
                                    AssistantLink(
                                        label=inv.get("name", "Factura"),
                                        url=f"/odoo/invoices/{inv['id']}",
                                        type="invoice",
                                    )
                                )
                return AssistantQueryResponse(
                    question=q,
                    answer=odoo_res.answer,
                    sources=["odoo"] if "odoo" not in source_labels else source_labels,
                    query_type=odoo_res.query_type,
                    cards=cards,
                    links=links,
                    data=odoo_res.data,
                )

        if any(k in lowered for k in ("productos se vendieron más", "más vendidos", "top productos")):
            return await self._answer_top_products(source_labels)

        if classified.has_clear_entity:
            entity = (
                classified.product_label
                or classified.customer_label
                or classified.supplier_label
                or classified.assignee_label
                or classified.search_term
                or "la consulta"
            )
            source = "odoo" if classified.intent in (
                BusinessIntent.SALES,
                BusinessIntent.PURCHASE,
                BusinessIntent.CUSTOMER_FINANCE,
                BusinessIntent.SUPPLIER,
            ) else "enterprise_search"
            return AssistantQueryResponse(
                question=q,
                answer=not_found_summary(entity, source),
                sources=source_labels,
                query_type=classified.intent.value if classified.intent != BusinessIntent.NONE else "not_found",
            )

        if not odoo_health.connected:
            if classified.intent == BusinessIntent.DGCP or any(
                k in lowered for k in ("dgcp", "licit", "licitar", "licitación", "licitacion")
            ):
                dgcp_only = await self._answer_dgcp(q)
                if dgcp_only:
                    return dgcp_only
            return AssistantQueryResponse(
                question=q,
                answer=(
                    "Odoo no está conectado. Conecta Odoo en Configuración para consultas de ventas, "
                    "compras y facturas. Puedo ayudarte con documentos, tareas, precios o búsqueda empresarial."
                ),
                sources=source_labels,
                query_type="not_connected",
            )

        if classified.intent not in (BusinessIntent.NONE, BusinessIntent.M365):
            fallback = await self._fallback_retrieval_chain(q, source_labels, semantic)
            if fallback is not None:
                return fallback
            return AssistantQueryResponse(
                question=q,
                answer=(
                    "Busqué en Odoo, documentos e índice empresarial con sinónimos y entidades equivalentes, "
                    f"pero no confirmé resultados para «{q}».\n\n"
                    "Prueba: «¿Qué le hemos vendido a Banco Ademi?», «papel 350», "
                    "«¿Qué licitaciones activas hay?» o «¿Qué tareas vencidas tengo?»"
                ),
                sources=source_labels + ["hermes_retrieval"],
                query_type=classified.intent.value,
            )

        fallback = await self._fallback_retrieval_chain(q, source_labels, semantic)
        if fallback is not None:
            return fallback

        return AssistantQueryResponse(
            question=q,
            answer=(
                "Necesito más información para responder con precisión. "
                "Indica producto, cliente, licitación o documento. "
                "Ejemplo: «¿Cuántos rollos de papel 350 hemos vendido?»"
            ),
            sources=source_labels,
            query_type="ambiguous",
        )

    async def _answer_customer_debt(
        self,
        q: str,
        sources: list[str],
        customer_label: str | None = None,
    ) -> AssistantQueryResponse:
        partner = customer_label or self._extract_name(
            q,
            r"(?:debe|adeuda|deuda de|nos debe)\s+(?:el cliente\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 .&-]+)",
        ) or self._extract_name(q, r"(?:cliente)\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 .&-]+)")
        if not partner:
            return AssistantQueryResponse(
                question=q,
                answer="Indica el nombre del cliente. Ejemplo: ¿Cuánto nos debe Banco Ademi?",
                sources=sources,
                query_type="customer_finance_query",
            )
        customers = await self.odoo.list_customers(search=partner, limit=1)
        if not customers.items:
            return AssistantQueryResponse(
                question=q,
                answer=f"No encontré el cliente '{partner}'.",
                sources=["odoo"],
                query_type="customer_debt",
            )
        cid = customers.items[0].id
        detail = await self.odoo_detail.get_customer_detail(cid)
        cards = []
        links = [AssistantLink(label=detail.name, url=f"/odoo/customers/{cid}", type="customer")]
        for inv in detail.overdue_invoices[:5]:
            cards.append(
                AssistantCard(
                    title=inv.name,
                    subtitle="Factura vencida",
                    fields={
                        "Pendiente": str(inv.amount_residual),
                        "Vence": inv.due_date or "—",
                    },
                    link=f"/odoo/invoices/{inv.id}",
                )
            )
            links.append(AssistantLink(label=inv.name, url=f"/odoo/invoices/{inv.id}", type="invoice"))

        answer = (
            f"{detail.name} debe {detail.total_due} en facturas abiertas "
            f"({detail.total_overdue} vencidas)."
        )
        structured = build_business_answer(
            intent="customer_finance_query",
            source="odoo",
            summary=answer,
            metrics=[
                {"label": "Cliente", "value": detail.name},
                {"label": "Total pendiente", "value": str(detail.total_due)},
                {"label": "Vencido", "value": str(detail.total_overdue)},
                {"label": "Facturas abiertas", "value": str(len(detail.open_invoices))},
            ],
            tables=[
                {
                    "title": "Facturas vencidas",
                    "columns": ["Factura", "Pendiente", "Vence"],
                    "rows": [
                        [inv.name, str(inv.amount_residual), inv.due_date or "—"]
                        for inv in detail.overdue_invoices[:10]
                    ],
                }
            ],
            links=links_to_dict(links),
        )
        return AssistantQueryResponse(
            question=q,
            answer=answer,
            sources=["odoo"],
            query_type="customer_finance_query",
            structured_data=structured,
            cards=cards,
            links=links,
            data={"total_due": str(detail.total_due), "total_overdue": str(detail.total_overdue)},
        )

    async def _answer_invoice_context(
        self, q: str, invoice_id: int, sources: list[str]
    ) -> AssistantQueryResponse:
        detail = await self.odoo_detail.get_invoice_detail(invoice_id)
        if detail.message and not detail.lines:
            return AssistantQueryResponse(
                question=q, answer=detail.message or "Factura no encontrada", sources=["odoo"]
            )
        lines_text = "; ".join(
            f"{ln.product_name}: {ln.quantity} x {ln.unit_price} = {ln.subtotal}"
            for ln in detail.lines[:10]
        )
        answer = (
            f"Factura {detail.name} — {detail.partner_name}. "
            f"Total {detail.amount_total}, pendiente {detail.amount_residual}. "
            f"Líneas: {lines_text or 'sin líneas'}."
        )
        cards = [
            AssistantCard(
                title=ln.product_name,
                fields={"Cant.": str(ln.quantity), "Precio": str(ln.unit_price), "Subtotal": str(ln.subtotal)},
            )
            for ln in detail.lines[:8]
        ]
        links = [
            AssistantLink(label=detail.partner_name, url=f"/odoo/customers/{detail.partner_id}", type="customer"),
            AssistantLink(label=detail.name, url=f"/odoo/invoices/{invoice_id}", type="invoice"),
        ]
        if detail.odoo_url:
            links.append(AssistantLink(label="Ver en Odoo", url=detail.odoo_url, type="external"))
        return AssistantQueryResponse(
            question=q,
            answer=answer,
            sources=["odoo"],
            query_type="invoice_detail",
            cards=cards,
            links=links,
            data=detail.model_dump(mode="json"),
        )

    async def _answer_customer_context(
        self, q: str, partner_id: int, sources: list[str]
    ) -> AssistantQueryResponse:
        detail = await self.odoo_detail.get_customer_detail(partner_id)
        top_products = ", ".join(
            p.product_name for p in detail.products_purchased[:3]
        )
        answer = (
            f"Cliente {detail.name}: ventas históricas {detail.total_sales_historical}, "
            f"{len(detail.open_invoices)} facturas abiertas ({detail.total_due}), "
            f"{len(detail.overdue_invoices)} vencidas ({detail.total_overdue}), "
            f"{len(detail.quotations)} cotizaciones, {len(detail.opportunities)} oportunidades, "
            f"{len(detail.projects)} proyectos. "
            f"Productos más comprados: {top_products or 'sin datos'}."
        )
        links = [AssistantLink(label=detail.name, url=f"/odoo/customers/{partner_id}", type="customer")]
        return AssistantQueryResponse(
            question=q,
            answer=answer,
            sources=["odoo"],
            query_type="customer_detail",
            links=links,
            data=detail.model_dump(mode="json"),
        )

    async def _answer_product_context(
        self, q: str, product_id: int, sources: list[str]
    ) -> AssistantQueryResponse:
        detail = await self.odoo_detail.get_product_detail(product_id)
        buyers = ", ".join(b.partner_name for b in detail.buyers[:5])
        margin_txt = (
            f"{detail.estimated_margin_pct:.1f}%"
            if detail.estimated_margin_pct is not None
            else "N/A"
        )
        answer = (
            f"Producto {detail.name} ({detail.default_code or 'sin código'}). "
            f"Último: {detail.last_price or 'N/A'}, promedio: {detail.average_price or 'N/A'}, "
            f"mín: {detail.min_price or 'N/A'}, máx: {detail.max_price or 'N/A'}. "
            f"Margen est.: {margin_txt}. Costo estándar: {detail.standard_price}. "
            f"Comprado por: {buyers or 'sin ventas'}. "
            f"Compras a proveedores: {len(detail.purchase_history)} líneas."
        )
        return AssistantQueryResponse(
            question=q,
            answer=answer,
            sources=["odoo"],
            query_type="product_detail",
            links=[AssistantLink(label=detail.name, url=f"/odoo/products/{product_id}", type="product")],
            data=detail.model_dump(mode="json"),
        )

    async def _answer_dgcp(self, q: str) -> AssistantQueryResponse | None:
        lowered = q.lower()
        today = date.today()
        week_end = today + timedelta(days=7)

        if any(k in lowered for k in ("para licitar", "licitar", "to_bid", "licitaciones para")):
            result = await self.db.execute(
                select(DGCPOpportunity)
                .where(
                    DGCPOpportunity.tenant_id == self.tenant_id,
                    DGCPOpportunity.status == OpportunityStatus.TO_BID.value,
                )
                .order_by(DGCPOpportunity.deadline.asc())
                .limit(15)
            )
            items = list(result.scalars().all())
            cards = [
                AssistantCard(
                    title=o.title[:80],
                    subtitle=o.code,
                    fields={"Monto": str(o.amount), "Vence": str(o.deadline), "Empresa": o.company},
                    link=f"/dgcp/{o.id}",
                )
                for o in items[:10]
            ]
            links = [AssistantLink(label=o.code, url=f"/dgcp/{o.id}", type="dgcp") for o in items[:10]]
            return AssistantQueryResponse(
                question=q,
                answer=f"Hay {len(items)} procesos DGCP para licitar.",
                sources=["dgcp"],
                query_type="dgcp_to_bid",
                cards=cards,
                links=links,
            )

        if any(k in lowered for k in ("vencen esta semana", "vencen la semana", "vence esta semana")):
            result = await self.db.execute(
                select(DGCPOpportunity)
                .where(
                    DGCPOpportunity.tenant_id == self.tenant_id,
                    DGCPOpportunity.deadline >= today,
                    DGCPOpportunity.deadline <= week_end,
                    DGCPOpportunity.status.in_([
                        OpportunityStatus.TO_BID.value,
                        OpportunityStatus.TO_REVIEW.value,
                        OpportunityStatus.DETECTED.value,
                    ]),
                )
                .order_by(DGCPOpportunity.deadline.asc())
                .limit(15)
            )
            items = list(result.scalars().all())
            lines = [f"{o.code} vence {o.deadline}" for o in items[:8]]
            return AssistantQueryResponse(
                question=q,
                answer=f"Licitaciones que vencen esta semana ({len(items)}): " + "; ".join(lines),
                sources=["dgcp"],
                query_type="dgcp_deadline_week",
                links=[AssistantLink(label=o.code, url=f"/dgcp/{o.id}", type="dgcp") for o in items[:10]],
            )

        summary = await self.dgcp.compute_dashboard(self.tenant_id)
        if any(k in lowered for k in ("dgcp", "licit")):
            return AssistantQueryResponse(
                question=q,
                answer=(
                    f"DGCP: {summary.to_bid} para licitar, {summary.to_review} en revisión, "
                    f"monto potencial {summary.total_potential_amount}."
                ),
                sources=["dgcp"],
                query_type="dgcp_summary",
                data=summary.model_dump(mode="json"),
            )
        return None

    async def _answer_top_products(self, sources: list[str]) -> AssistantQueryResponse:
        sales = await self.odoo.sales_history(limit=200)
        agg: dict[str, dict] = {}
        for s in sales.items:
            if not isinstance(s, OdooSaleHistoryItem):
                continue
            key = s.product_name
            if key not in agg:
                agg[key] = {"qty": 0.0, "revenue": Decimal("0")}
            agg[key]["qty"] += s.quantity
            agg[key]["revenue"] += s.subtotal
        top = sorted(agg.items(), key=lambda x: x[1]["qty"], reverse=True)[:10]
        lines = [f"{name}: {int(v['qty'])} uds" for name, v in top[:5]]
        cards = [
            AssistantCard(title=name, fields={"Cantidad": str(int(v["qty"])), "Ingresos": str(v["revenue"])})
            for name, v in top[:5]
        ]
        return AssistantQueryResponse(
            question="productos más vendidos",
            answer="Productos con más ventas recientes: " + "; ".join(lines),
            sources=["odoo"],
            query_type="top_products",
            cards=cards,
        )

    async def _try_dgcp_record_answer(
        self,
        question: str,
        payload: AssistantQueryRequest,
        source_labels: list[str],
    ) -> AssistantQueryResponse | None:
        if payload.record_type not in ("dgcp", "dgcp_opportunity") or not payload.current_record_id:
            return None
        try:
            opp_id = uuid.UUID(payload.current_record_id)
        except ValueError:
            return None
        from app.services.document_finalization_question_service import DocumentFinalizationQuestionService
        from app.services.real_expediente_question_service import RealExpedienteQuestionService

        if RealExpedienteQuestionService.matches(question):
            real = await RealExpedienteQuestionService(
                self.db, self.tenant_id, user_id=self.user_id
            ).answer(question, opportunity_id=opp_id)
            if real is not None:
                real.question = question
                real.sources = list(dict.fromkeys(["dgcp_real_expediente"] + source_labels + (real.sources or [])))
                return real

        if DocumentFinalizationQuestionService.matches(question):
            fin = await DocumentFinalizationQuestionService(
                self.db, self.tenant_id, user_id=self.user_id
            ).answer(question, opportunity_id=opp_id)
            if fin is not None:
                fin.question = question
                fin.sources = list(dict.fromkeys(["dgcp_finalization"] + source_labels + (fin.sources or [])))
                return fin
        result = await DgcpRequirementsQuestionService(
            self.db, self.tenant_id, self.user_id
        ).answer(question, opp_id)
        if result is not None:
            result.sources = list(dict.fromkeys(["dgcp"] + source_labels + result.sources))
            return result
        return None

    async def _answer_work(
        self, q: str, lowered: str, payload: AssistantQueryRequest
    ) -> AssistantQueryResponse | None:
        if any(k in lowered for k in ("mis tareas vencidas", "tareas vencidas", "vencidas")):
            result = await self.tasks.list_tasks(assigned_to_id=self.user_id, limit=50)
            overdue = [t for t in result.items if t.due_date and t.due_date < date.today()]
            if not overdue:
                return AssistantQueryResponse(
                    question=q,
                    answer="No tienes tareas vencidas asignadas.",
                    sources=["work"],
                    query_type="my_overdue_tasks",
                    links=[AssistantLink(label="Work Hub", url="/work", type="work")],
                )
            lines = [f"• {t.title} (vence {t.due_date})" for t in overdue[:8]]
            return AssistantQueryResponse(
                question=q,
                answer=f"Tienes {len(overdue)} tareas vencidas:\n" + "\n".join(lines),
                sources=["work"],
                query_type="my_overdue_tasks",
                links=[AssistantLink(label=t.title, url=f"/tasks/{t.id}", type="task") for t in overdue[:5]],
            )

        if any(k in lowered for k in ("tareas críticas", "criticas hoy", "críticas hoy")):
            result = await self.tasks.list_tasks(priority="critica", limit=20)
            active = [t for t in result.items if t.status not in ("completada", "cancelada")]
            lines = [f"• {t.title} → {t.assigned_to_name or t.suggested_assignee_name or 'sin asignar'}" for t in active[:8]]
            return AssistantQueryResponse(
                question=q,
                answer=f"Hay {len(active)} tareas críticas activas:\n" + "\n".join(lines) if active else "No hay tareas críticas activas.",
                sources=["work"],
                query_type="critical_tasks",
                links=[AssistantLink(label=t.title, url=f"/tasks/{t.id}", type="task") for t in active[:5]],
            )

        assignee_match = re.search(
            r"(?:qué tiene pendiente|que tiene pendiente|pendiente de)\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
            q,
            re.IGNORECASE,
        )
        if assignee_match:
            name = assignee_match.group(1)
            user_result = await self.db.execute(
                select(User).where(User.full_name.ilike(f"%{name}%"), User.is_active.is_(True)).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if user:
                result = await self.tasks.list_tasks(assigned_to_id=user.id, limit=15)
                pending = [t for t in result.items if t.status in ("pendiente", "en_proceso")]
                lines = [f"• {t.title} ({t.priority})" for t in pending[:8]]
                return AssistantQueryResponse(
                    question=q,
                    answer=f"{user.full_name} tiene {len(pending)} tareas pendientes:\n" + "\n".join(lines),
                    sources=["work"],
                    query_type="assignee_pending",
                )

        if is_task_create := ("tarea" in lowered and any(k in lowered for k in ("crea", "crear", "asigna", "asignar"))):
            event_type = "otro"
            if "cotizacion" in lowered or "cotización" in lowered:
                event_type = "cotizacion"
            elif "factura" in lowered and "proveedor" in lowered:
                event_type = "factura_proveedor"
            elif "factura" in lowered:
                event_type = "factura_cliente"
            elif "soporte" in lowered:
                event_type = "soporte"
            elif "licitacion" in lowered or "licitación" in lowered:
                event_type = "licitacion"
            elif "pago" in lowered:
                event_type = "pago_cliente"
            elif "cobro" in lowered or "cobrar" in lowered:
                event_type = "cuenta_por_cobrar"

            preview = await self.routing.preview(
                event_type=event_type,
                title=q[:200],
                description=q,
            )
            return AssistantQueryResponse(
                question=q,
                answer=(
                    f"Puedo crear la tarea con routing automático:\n"
                    f"• Categoría: {preview.category}\n"
                    f"• Departamento: {preview.department}\n"
                    f"• Responsable sugerido: {preview.suggested_assignee_name or 'por asignar'}\n"
                    f"• Prioridad: {preview.priority}\n"
                    f"Confirma en /tasks o usa el botón «Crear tarea» en el módulo relacionado."
                ),
                sources=["work"],
                query_type="task_create_preview",
                links=[AssistantLink(label="Tasks Center", url="/tasks", type="work")],
                data=preview.model_dump(mode="json"),
            )

        if any(k in lowered for k in ("mis tareas", "mi trabajo", "work hub")):
            return AssistantQueryResponse(
                question=q,
                answer="Abre Work Hub en /work para ver tus tareas pendientes, vencidas, críticas y alertas operativas.",
                sources=["work"],
                query_type="work_hub_help",
                links=[AssistantLink(label="Work Hub", url="/work", type="work")],
            )
        return None

    async def _fallback_retrieval_chain(
        self,
        q: str,
        source_labels: list[str],
        semantic: SemanticResolution | None,
    ) -> AssistantQueryResponse | None:
        """Cadena Hermes → Knowledge Engine → sugerencias antes de fallar."""
        from app.schemas.assistant import AssistantAction
        from app.services.assistant_actions import build_customer_suggested_actions

        term = q.strip()
        if semantic and semantic.customer_label and not semantic.product_label:
            sales_svc = SalesQuestionService(self.db, self.tenant_id, self.user_id)
            rewritten = f"¿Qué le hemos vendido a {semantic.customer_label}?"
            sales_result = await sales_svc.answer(rewritten, source_labels=source_labels)
            if sales_result and "No encontré" not in sales_result.answer:
                sales_result.question = q
                return sales_result

        hermes = HermesRetrievalService(self.db, self.tenant_id, self.user_id)
        try:
            engine_result = await hermes.search(term, limit=6)
        except Exception:
            engine_result = None

        if engine_result and engine_result.total > 0:
            entity_prefix = ""
            if engine_result.resolved_entities:
                ent = engine_result.resolved_entities[0]
                entity_prefix = f"Entidad **{ent.canonical_name}**. "
            template = entity_prefix + f"Encontré {engine_result.total} resultado(s) relacionados con «{term}»."
            hits = []
            for group in engine_result.groups[:5]:
                for item in group.items[:3]:
                    hits.append({
                        "grupo": group.label,
                        "titulo": item.title,
                        "detalle": item.subtitle or item.description,
                        "fuente": item.source,
                    })
            synthesizer = AssistantSynthesisService(self.db, self.tenant_id)
            summary = await synthesizer.synthesize_retrieval_summary(
                question=q,
                template_summary=template,
                hits=hits,
                entities=[e.model_dump() for e in (engine_result.resolved_entities or [])],
            )
            actions = [
                AssistantAction(label="Ver búsqueda completa", type="internal_link", url=f"/search?q={term}"),
            ]
            if semantic and semantic.customer_label:
                actions.extend([
                    AssistantAction(**a) for a in build_customer_suggested_actions(semantic.customer_label)
                ])
            return AssistantQueryResponse(
                question=q,
                answer=summary,
                sources=list(dict.fromkeys(source_labels + ["hermes_retrieval", "enterprise_search"])),
                query_type="enterprise_search_query",
                actions=actions,
                links=[AssistantLink(label="Búsqueda empresarial", url=f"/search?q={term}", type="search")],
                data={"total": engine_result.total, "resolved_entities": [
                    e.model_dump() for e in (engine_result.resolved_entities or [])
                ]},
            )

        if semantic and semantic.product_label:
            norm = normalize_product(semantic.product_label)
            variants = (norm.variants_display if norm else semantic.product_terms)[:8]
            if variants:
                listed = "\n".join(f"• {v}" for v in variants[:6])
                return AssistantQueryResponse(
                    question=q,
                    answer=(
                        f"Encontré variantes relacionadas con «{semantic.product_label}»:\n\n{listed}\n\n"
                        "¿A cuál te refieres? Puedes preguntar, por ejemplo: "
                        f"«¿Cuántos {variants[0]} hemos vendido?»"
                    ),
                    sources=source_labels + ["semantic_resolver"],
                    query_type="product_disambiguation",
                    actions=[
                        AssistantAction(
                            label=f"Buscar {variants[0]}",
                            type="internal_link",
                            url=f"/search?q={variants[0]}",
                        ),
                    ],
                )
        return None

    @staticmethod
    def _extract_enterprise_search_query(question: str) -> str | None:
        patterns = (
            r"(?i)busca(?:r)?\s+todo\s+sobre\s+(.+)",
            r"(?i)busca(?:r)?\s+(.+)",
            r"(?i)encuentra(?:r)?\s+(.+)",
            r"(?i)búsqueda\s+de\s+(.+)",
            r"(?i)busqueda\s+de\s+(.+)",
        )
        for pattern in patterns:
            match = re.search(pattern, question.strip())
            if match:
                term = match.group(1).strip().rstrip("?.")
                if len(term) >= 2:
                    return term
        return None

    async def _answer_enterprise_search(
        self,
        term: str,
        source_labels: list[str],
    ) -> AssistantQueryResponse:
        from app.services.knowledge_engine_service import KnowledgeEngineService

        service = KnowledgeEngineService(self.db, self.tenant_id, self.user_id)
        result = await service.search_global(term, channel="assistant")
        search_link = AssistantLink(label="Búsqueda empresarial", url=f"/search?q={term}", type="search")
        if result.total == 0:
            summary = f"No encontré registros relacionados con {term} en las fuentes disponibles."
            structured = build_business_answer(
                intent="enterprise_search_query",
                source="enterprise_search",
                summary=summary,
                links=links_to_dict([search_link]),
            )
            return AssistantQueryResponse(
                question=f"Busca todo sobre {term}",
                answer=summary,
                sources=["enterprise_search"],
                query_type="enterprise_search_query",
                structured_data=structured,
                links=[search_link],
            )

        entity_prefix = ""
        if result.resolved_entities:
            ent = result.resolved_entities[0]
            entity_prefix = f"Entidad **{ent.canonical_name}** ({ent.entity_type}). "

        summary = entity_prefix + f"Encontré {result.total} resultado(s) para «{term}»."
        links: list[AssistantLink] = [search_link]
        from app.services.assistant_actions import table_row

        entity_map = {
            "customer": "customer",
            "producto": "product",
            "product": "product",
            "invoice": "invoice",
            "factura": "invoice",
            "dgcp": "dgcp",
            "task": "task",
            "vendor": "vendor",
        }
        rows: list[dict] = []
        for group in result.groups[:6]:
            for item in group.items[:4]:
                entity_type = entity_map.get((item.type or "").lower())
                entity_id = item.id if entity_type else None
                row = table_row(
                    [group.label, item.title, item.subtitle or "—"],
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                rows.append(row)
                links.append(AssistantLink(label=item.title, url=item.url, type=item.type))

        structured = build_business_answer(
            intent="enterprise_search_query",
            source="enterprise_search",
            summary=summary,
            metrics=[
                {"label": "Resultados", "value": str(result.total)},
                {"label": "Término", "value": term},
            ],
            tables=[{
                "title": "Resultados por fuente",
                "columns": ["Fuente", "Título", "Detalle"],
                "rows": rows[:16],
            }],
            links=links_to_dict(links[:12]),
        )
        return AssistantQueryResponse(
            question=f"Busca todo sobre {term}",
            answer=summary,
            sources=list(dict.fromkeys(["enterprise_search", "knowledge_engine"] + source_labels)),
            query_type="enterprise_search_query",
            structured_data=structured,
            links=links[:12],
            data=result.model_dump(mode="json"),
        )

    @staticmethod
    def _extract_name(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        value = match.group(1).strip().rstrip("?.")
        return value if len(value) > 2 else None

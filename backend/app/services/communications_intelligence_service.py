"""IA sobre conversaciones WhatsApp — Fase 2 con LLM + integraciones JAIOS."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import LLMProviderError
from app.llm.router import LLMRouter
from app.models.whatsapp import WhatsappChat, WhatsappMessage
from app.schemas.communications import (
    WhatsappAiActionResponse,
    WhatsappChatIntelligence,
    WhatsappIntelligenceLink,
)
from app.schemas.llm import LLMCompletionRequest, LLMMessage
from app.schemas.tasks import TaskCreateRequest
from app.services.assistant_synthesis_service import AssistantSynthesisService
from app.services.enterprise_search_service import EnterpriseSearchService
from app.services.m365_assistant_service import M365AssistantService
from app.services.m365_connection_service import M365ConnectionService
from app.services.price_intelligence_service import PriceIntelligenceService, PriceSearchFilters
from app.services.task_service import TaskService
from app.services.whatsapp_message_classifier import (
    CLASSIFICATION_LABELS,
    WhatsappMessageClassifier,
)

COMMUNICATIONS_ANALYSIS_PROMPT = """Eres analista de comunicaciones empresariales de JAIOS (Justech, República Dominicana).
Analiza la conversación WhatsApp y responde ÚNICAMENTE JSON válido (sin markdown):
{
  "classification": "cliente|proveedor|oportunidad|licitacion|soporte|cobro|seguimiento|reclamo|urgencia",
  "confidence": 0-100,
  "secondary_labels": ["..."],
  "priority": 0-100,
  "sentiment": "positive|neutral|negative",
  "entities": {"company": "", "contact_name": "", "products": [], "amounts": []},
  "intent_summary": "una oración",
  "suggested_actions": ["analyze","reply","search_prices","create_task","create_dgcp"]
}
Usa solo información presente en la conversación."""


class CommunicationsIntelligenceService:
    CLASSIFICATIONS = tuple(CLASSIFICATION_LABELS.keys())

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._classifier = WhatsappMessageClassifier()
        self._synthesis = AssistantSynthesisService(db, tenant_id)
        self._llm = LLMRouter(db)

    async def get_chat_intelligence(self, chat_id: uuid.UUID) -> WhatsappChatIntelligence | None:
        chat = await self._get_chat(chat_id)
        if chat is None:
            return None
        return self._chat_to_intelligence(chat)

    async def auto_analyze_chat(self, session_id: uuid.UUID, chat_id: uuid.UUID) -> None:
        """Análisis automático al recibir mensaje entrante."""
        chat = await self._get_chat(chat_id)
        if chat is None or chat.session_id != session_id:
            return
        messages = await self._load_messages(session_id, chat_id, limit=40)
        if not messages:
            return
        last = messages[-1]
        if last.from_me:
            return
        await self._analyze_and_persist(chat, messages, auto=True)

    async def run_action(
        self,
        action: str,
        session_id: uuid.UUID,
        chat_id: uuid.UUID | None = None,
    ) -> WhatsappAiActionResponse:
        chat = await self._get_chat(chat_id) if chat_id else None
        messages = await self._load_messages(session_id, chat_id)
        transcript = self._build_transcript(messages)
        contact_name = chat.name if chat else None
        rules = self._classifier.classify(text=transcript, contact_name=contact_name)
        analysis = await self._llm_classify(transcript, rules)

        links: list[WhatsappIntelligenceLink] = []
        suggestions: list[str] = []
        created_id: str | None = None

        if action == "analyze":
            if chat and chat_id:
                await self._analyze_and_persist(chat, messages, auto=False)
                chat = await self._get_chat(chat_id)
            result = self._format_analysis(analysis, len(messages))
            suggestions = ["Resumir conversación", "Generar respuesta", "Crear tarea"]
        elif action == "summarize":
            template = (
                f"Conversación tipo {analysis['classification']} "
                f"({analysis.get('intent_summary', '')}). {len(messages)} mensajes."
            )
            result = await self._synthesis.synthesize_answer(
                question="Resume esta conversación WhatsApp",
                template_answer=template,
                query_type="whatsapp_summary",
                sources=["whatsapp"],
                facts={"transcript": transcript[-3000:], "analysis": analysis},
            )
            if chat:
                chat.ai_summary = result
                await self.db.flush()
            suggestions = ["Generar respuesta", "Buscar documentos", "Crear tarea"]
        elif action == "reply":
            template = self._template_reply(analysis, messages)
            result = await self._synthesis.synthesize_answer(
                question="Genera respuesta profesional para WhatsApp",
                template_answer=template,
                query_type="whatsapp_reply",
                sources=["whatsapp"],
                facts={"analysis": analysis, "last_messages": transcript[-1500:]},
            )
            if chat:
                chat.ai_suggested_reply = result
                await self.db.flush()
            suggestions = ["Enviar", "Buscar precios", "Crear tarea"]
        elif action == "search_prices":
            result, links, suggestions = await self._search_prices(analysis, transcript)
        elif action == "search_docs":
            result, links = await self._search_docs(analysis, transcript)
            suggestions = ["Generar respuesta", "Buscar precios"]
        elif action == "search_mail":
            result, links = await self._search_mail(analysis, transcript, contact_name)
            suggestions = ["Ver en Outlook", "Crear tarea"]
        elif action == "create_task":
            result, created_id, links = await self._create_task(chat, analysis, transcript)
        elif action == "create_opportunity":
            result, created_id, links = await self._create_linked_task(
                chat, analysis, transcript, category="comercial", tag="oportunidad",
                title_prefix="Oportunidad WhatsApp",
            )
        elif action == "create_client":
            result, created_id, links = await self._create_linked_task(
                chat, analysis, transcript, category="comercial", tag="nuevo_cliente",
                title_prefix="Nuevo cliente WhatsApp",
            )
        elif action == "create_dgcp":
            result, created_id, links = await self._create_dgcp_action(chat, analysis, transcript)
        else:
            result = "Acción no reconocida."

        return WhatsappAiActionResponse(
            action=action,
            result=result,
            suggestions=suggestions,
            classification=analysis.get("classification"),
            priority=analysis.get("priority"),
            links=links,
            created_id=created_id,
            suggested_reply=chat.ai_suggested_reply if chat and action == "reply" else None,
        )

    async def _analyze_and_persist(
        self, chat: WhatsappChat, messages: list[WhatsappMessage], *, auto: bool
    ) -> dict[str, Any]:
        transcript = self._build_transcript(messages)
        rules = self._classifier.classify(text=transcript, contact_name=chat.name)
        analysis = await self._llm_classify(transcript, rules)
        analysis["auto"] = auto
        analysis["analyzed_at"] = datetime.now(UTC).isoformat()
        analysis["label"] = CLASSIFICATION_LABELS.get(analysis["classification"], analysis["classification"])

        chat.ai_classification = analysis
        chat.ai_priority = int(analysis.get("priority") or rules.priority)
        chat.ai_last_analyzed_at = datetime.now(UTC)

        if not chat.ai_summary or not auto:
            template = analysis.get("intent_summary") or f"Conversación {analysis['classification']}"
            chat.ai_summary = await self._synthesis.synthesize_answer(
                question="Resumen breve conversación WhatsApp",
                template_answer=template,
                query_type="whatsapp_auto_summary",
                sources=["whatsapp"],
                facts={"analysis": analysis, "transcript": transcript[-2000:]},
            )

        if not chat.ai_suggested_reply or (not auto and analysis.get("priority", 0) >= 70):
            chat.ai_suggested_reply = await self._synthesis.synthesize_answer(
                question="Respuesta sugerida WhatsApp",
                template_answer=self._template_reply(analysis, messages),
                query_type="whatsapp_auto_reply",
                sources=["whatsapp"],
                facts={"analysis": analysis, "transcript": transcript[-1200:]},
            )

        cls_label = CLASSIFICATION_LABELS.get(analysis["classification"], analysis["classification"])
        if cls_label not in (chat.labels or []):
            chat.labels = list(chat.labels or []) + [cls_label]

        for msg in messages[-5:]:
            if not msg.from_me and msg.body:
                msg.ai_classification = {
                    "classification": analysis["classification"],
                    "confidence": analysis.get("confidence"),
                }

        await self.db.flush()
        return analysis

    async def _llm_classify(self, transcript: str, rules) -> dict[str, Any]:
        base = {
            "classification": rules.classification,
            "confidence": rules.confidence,
            "secondary_labels": rules.secondary_labels,
            "priority": rules.priority,
            "sentiment": rules.sentiment,
            "entities": rules.entities,
            "signals": rules.signals,
            "intent_summary": f"Mensaje tipo {CLASSIFICATION_LABELS.get(rules.classification, rules.classification)}",
            "suggested_actions": self._default_actions(rules.classification),
        }
        if not settings.assistant_synthesis_enabled:
            return base

        request = LLMCompletionRequest(
            messages=[
                LLMMessage(role="system", content=COMMUNICATIONS_ANALYSIS_PROMPT),
                LLMMessage(role="user", content=transcript[-4000:] or "(sin texto)"),
            ],
            temperature=0.1,
            max_tokens=400,
        )
        try:
            response = await self._llm.complete(request, tenant_id=self.tenant_id)
            raw = (response.content or "").strip()
            raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.I)
            parsed = json.loads(raw)
            for key in ("classification", "confidence", "priority", "sentiment", "entities", "intent_summary"):
                if key in parsed and parsed[key]:
                    base[key] = parsed[key]
            if parsed.get("secondary_labels"):
                base["secondary_labels"] = parsed["secondary_labels"]
            if parsed.get("suggested_actions"):
                base["suggested_actions"] = parsed["suggested_actions"]
        except (LLMProviderError, json.JSONDecodeError, KeyError, TypeError):
            pass
        return base

    async def _search_prices(
        self, analysis: dict, transcript: str
    ) -> tuple[str, list[WhatsappIntelligenceLink], list[str]]:
        products = (analysis.get("entities") or {}).get("products") or []
        query = products[0] if products else self._extract_product_query(transcript)
        if not query:
            return (
                "No detecté productos en la conversación. Indique cantidad y modelo (ej. «25 laptops Dell»).",
                [],
                ["laptops", "servidores HPE", "licencias Microsoft"],
            )

        svc = PriceIntelligenceService(self.db, self.tenant_id)
        hits = await svc.search(PriceSearchFilters(q=query, limit=8))
        if not hits.items:
            return (
                f"Sin resultados en base de precios para «{query}». Revise listas de proveedores.",
                [WhatsappIntelligenceLink(label="Motor de precios", url="/prices", type="prices")],
                ["Sincronizar listas", "Buscar en Odoo"],
            )

        lines = [f"Precios para «{query}» — {hits.total} opciones:"]
        links: list[WhatsappIntelligenceLink] = []
        for p in hits.items[:5]:
            price = f"{p.currency} {p.price:,.2f}" if p.price else "sin precio"
            lines.append(f"• {p.description[:60]} — {p.supplier or 'N/D'} — {price}")
            links.append(
                WhatsappIntelligenceLink(
                    label=p.description[:40],
                    url=f"/prices?q={query}",
                    type="price_product",
                )
            )
        compare = await svc.compare(PriceSearchFilters(q=query, limit=5), question=query)
        if compare.alternatives:
            best = compare.alternatives[0]
            lines.append(f"\nRecomendación: {best.description} ({best.supplier}) — mejor relación precio/proveedor.")

        return "\n".join(lines), links, ["Generar respuesta con cotización", "Crear oportunidad"]

    async def _search_docs(
        self, analysis: dict, transcript: str
    ) -> tuple[str, list[WhatsappIntelligenceLink]]:
        query = (
            (analysis.get("entities") or {}).get("company")
            or self._extract_search_term(transcript)
            or analysis.get("classification", "")
        )
        search = EnterpriseSearchService(self.db, self.tenant_id, self.user_id)
        result = await search.search(query, limit_per_group=5)
        if not result.groups:
            return (
                f"Sin documentos ni registros para «{query}» en búsqueda empresarial.",
                [WhatsappIntelligenceLink(label="Búsqueda global", url=f"/search?q={query}", type="search")],
            )
        lines = [f"Resultados para «{query}»:"]
        links: list[WhatsappIntelligenceLink] = []
        for group in result.groups[:4]:
            lines.append(f"\n{group.label}:")
            for item in group.items[:3]:
                lines.append(f"• {item.title}")
                if item.url:
                    links.append(WhatsappIntelligenceLink(label=item.title[:40], url=item.url, type=item.type))
        return "\n".join(lines), links

    async def _search_mail(
        self, analysis: dict, transcript: str, contact_name: str | None
    ) -> tuple[str, list[WhatsappIntelligenceLink]]:
        conn = await M365ConnectionService(self.db, self.tenant_id, self.user_id).connection_state()
        if not conn.account_connected:
            return (
                "Outlook no conectado. Vincule su cuenta en Microsoft 365 para buscar correos relacionados.",
                [WhatsappIntelligenceLink(label="Conectar M365", url="/m365/cuentas", type="m365")],
            )
        query = (
            (analysis.get("entities") or {}).get("company")
            or contact_name
            or self._extract_search_term(transcript)
            or "seguimiento"
        )
        m365 = M365AssistantService(self.db, self.tenant_id, self.user_id)
        resp = await m365.answer(f"correos sobre {query}")
        links = [
            WhatsappIntelligenceLink(label=lnk.label, url=lnk.url, type=lnk.type)
            for lnk in (resp.links or [])
        ]
        if not links:
            links.append(WhatsappIntelligenceLink(label="Outlook", url="/comunicaciones?tab=outlook", type="mail"))
        return resp.answer, links

    async def _create_task(
        self, chat: WhatsappChat | None, analysis: dict, transcript: str
    ) -> tuple[str, str | None, list[WhatsappIntelligenceLink]]:
        return await self._create_linked_task(
            chat, analysis, transcript,
            category=self._task_category(analysis["classification"]),
            tag="whatsapp",
            title_prefix="Seguimiento WhatsApp",
        )

    async def _create_linked_task(
        self,
        chat: WhatsappChat | None,
        analysis: dict,
        transcript: str,
        *,
        category: str,
        tag: str,
        title_prefix: str,
    ) -> tuple[str, str | None, list[WhatsappIntelligenceLink]]:
        contact = chat.name if chat else (analysis.get("entities") or {}).get("contact_name") or "Contacto"
        cls = CLASSIFICATION_LABELS.get(analysis["classification"], analysis["classification"])
        summary = analysis.get("intent_summary") or transcript[-300:]
        priority = "alta" if (analysis.get("priority") or 0) >= 80 else "media"

        task = await TaskService(self.db, self.tenant_id, self.user_id).create_task(
            TaskCreateRequest(
                title=f"{title_prefix}: {contact}"[:120],
                description=f"Clasificación: {cls}\n\n{summary}\n\n---\n{transcript[-1500:]}",
                priority=priority,
                category=category,
                department="comercial" if category == "comercial" else "operaciones",
                source="whatsapp",
                customer_name=contact if chat else None,
                tags=[tag, "whatsapp", analysis["classification"]],
                metadata={
                    "whatsapp_chat_id": str(chat.id) if chat else None,
                    "classification": analysis["classification"],
                },
            )
        )
        links = [WhatsappIntelligenceLink(label="Ver tarea", url=f"/tasks?id={task.id}", type="task")]
        return f"Tarea creada: {task.title}", str(task.id), links

    async def _create_dgcp_action(
        self, chat: WhatsappChat | None, analysis: dict, transcript: str
    ) -> tuple[str, str | None, list[WhatsappIntelligenceLink]]:
        query = self._extract_search_term(transcript) or "licitación"
        search = EnterpriseSearchService(self.db, self.tenant_id, self.user_id)
        dgcp = await search.search(query, source_filter="dgcp", limit_per_group=5)
        links: list[WhatsappIntelligenceLink] = [
            WhatsappIntelligenceLink(label="DGCP", url="/dgcp", type="dgcp"),
            WhatsappIntelligenceLink(label="Expedientes", url="/oportunidades", type="dgcp"),
        ]
        lines = [f"Análisis licitación — clasificación: {analysis.get('classification')}"]

        if dgcp.groups:
            for group in dgcp.groups:
                for item in group.items[:3]:
                    lines.append(f"• {item.title}")
                    links.append(WhatsappIntelligenceLink(label=item.title[:40], url=item.url, type="dgcp"))

        task_msg, task_id, task_links = await self._create_linked_task(
            chat, {**analysis, "classification": "licitacion"},
            transcript, category="licitacion", tag="dgcp", title_prefix="Expediente DGCP WhatsApp",
        )
        lines.append(f"\n{task_msg}")
        links.extend(task_links)
        return "\n".join(lines), task_id, links

    async def _get_chat(self, chat_id: uuid.UUID | None) -> WhatsappChat | None:
        if not chat_id:
            return None
        q = await self.db.execute(
            select(WhatsappChat).where(
                WhatsappChat.id == chat_id,
                WhatsappChat.tenant_id == self.tenant_id,
            )
        )
        return q.scalar_one_or_none()

    async def _load_messages(
        self, session_id: uuid.UUID, chat_id: uuid.UUID | None, limit: int = 50
    ) -> list[WhatsappMessage]:
        stmt = select(WhatsappMessage).where(
            WhatsappMessage.tenant_id == self.tenant_id,
            WhatsappMessage.session_id == session_id,
        )
        if chat_id:
            stmt = stmt.where(WhatsappMessage.chat_id == chat_id)
        stmt = stmt.order_by(WhatsappMessage.wa_timestamp_ms.asc().nullslast()).limit(limit)
        q = await self.db.execute(stmt)
        return list(q.scalars().all())

    @staticmethod
    def _build_transcript(messages: list[WhatsappMessage]) -> str:
        lines: list[str] = []
        for m in messages:
            media = m.media_type or "media"
            body = m.body or f"[{media}]"
            who = "Yo" if m.from_me else "Contacto"
            lines.append(f"{who}: {body}")
        return "\n".join(lines)

    @staticmethod
    def _format_analysis(analysis: dict, msg_count: int) -> str:
        cls = CLASSIFICATION_LABELS.get(analysis.get("classification", ""), analysis.get("classification"))
        lines = [
            f"Clasificación: {cls} (confianza {analysis.get('confidence', 0)}%)",
            f"Prioridad: {analysis.get('priority', 50)}/100 — Sentimiento: {analysis.get('sentiment', 'neutral')}",
            f"Resumen: {analysis.get('intent_summary', '')}",
            f"Mensajes analizados: {msg_count}",
        ]
        entities = analysis.get("entities") or {}
        if entities.get("company"):
            lines.append(f"Empresa detectada: {entities['company']}")
        if entities.get("products"):
            lines.append(f"Productos: {', '.join(entities['products'][:5])}")
        if analysis.get("secondary_labels"):
            lines.append(f"Etiquetas secundarias: {', '.join(analysis['secondary_labels'])}")
        return "\n".join(lines)

    @staticmethod
    def _template_reply(analysis: dict, messages: list[WhatsappMessage]) -> str:
        last_inbound = next((m for m in reversed(messages) if not m.from_me and m.body), None)
        snippet = (last_inbound.body or "")[:120] if last_inbound else "su mensaje"
        cls = analysis.get("classification", "seguimiento")
        templates = {
            "licitacion": "Gracias por la información sobre la licitación. Revisaremos requisitos DGCP y le confirmamos expediente.",
            "oportunidad": f"Recibido. Preparamos cotización según: «{snippet}». ¿Confirma cantidades y plazo?",
            "cobro": "Confirmamos recepción. Verificamos estado de factura y le informamos hoy.",
            "soporte": f"Entendido. Abrimos seguimiento de soporte por: «{snippet}».",
            "urgencia": "Recibido con prioridad alta. Un especialista le responde en breve.",
            "reclamo": "Lamentamos la situación. Escalamos su caso y le contactamos hoy.",
        }
        return templates.get(cls, "Gracias por escribirnos. Hemos recibido su mensaje y le respondemos a la brevedad.")

    @staticmethod
    def _task_category(classification: str) -> str:
        return {
            "licitacion": "licitacion",
            "oportunidad": "comercial",
            "soporte": "soporte",
            "cobro": "finanzas",
            "reclamo": "soporte",
        }.get(classification, "otro")

    @staticmethod
    def _default_actions(classification: str) -> list[str]:
        base = ["analyze", "reply", "create_task"]
        if classification in ("licitacion", "oportunidad"):
            base.extend(["search_prices", "create_dgcp", "search_docs"])
        if classification == "cobro":
            base.append("search_mail")
        return base

    @staticmethod
    def _extract_product_query(text: str) -> str | None:
        m = re.search(
            r"(\d+\s+)?(laptops?|notebooks?|servidores?|licencias?|monitores?|computadoras?)\s*[\w\-]*",
            text,
            re.I,
        )
        return m.group(0).strip() if m else None

    @staticmethod
    def _extract_search_term(text: str) -> str | None:
        for line in reversed(text.split("\n")):
            if line.startswith("Contacto:") and len(line) > 20:
                return line.replace("Contacto:", "").strip()[:80]
        words = [w for w in re.split(r"\s+", text) if len(w) >= 4]
        return " ".join(words[-4:]) if words else None

    def _chat_to_intelligence(self, chat: WhatsappChat) -> WhatsappChatIntelligence:
        ai = chat.ai_classification or {}
        return WhatsappChatIntelligence(
            chat_id=chat.id,
            classification=ai.get("classification"),
            classification_label=ai.get("label") or CLASSIFICATION_LABELS.get(ai.get("classification", ""), ""),
            confidence=ai.get("confidence"),
            priority=chat.ai_priority or ai.get("priority"),
            sentiment=ai.get("sentiment"),
            summary=chat.ai_summary,
            suggested_reply=chat.ai_suggested_reply,
            entities=ai.get("entities") or {},
            secondary_labels=ai.get("secondary_labels") or [],
            suggested_actions=ai.get("suggested_actions") or [],
            last_analyzed_at=chat.ai_last_analyzed_at,
        )

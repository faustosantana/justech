"""Agente Microsoft 365 — consultas reales vía Graph + repositorio + Qdrant."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantQueryResponse
from app.services.m365_connection_service import M365ConnectionService
from app.services.m365_graph_session import M365GraphSessionService
from app.services.m365_qdrant_service import M365QdrantService
from app.services.m365_repository_service import M365RepositoryService
from integrations.microsoft365.errors import GraphError


class M365AssistantService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def answer(self, question: str) -> AssistantQueryResponse:
        conn = await M365ConnectionService(self.db, self.tenant_id, self.user_id).connection_state()
        if not conn.account_connected:
            return AssistantQueryResponse(
                question=question,
                answer="Microsoft 365 no está conectado. Vaya a Cuentas y autorice su buzón.",
                sources=["m365"],
                query_type="m365_not_connected",
            )

        q = question.lower()
        parts: list[str] = []
        links: list[dict] = []

        try:
            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account(None)
        except GraphError as exc:
            return AssistantQueryResponse(
                question=question,
                answer=f"No pude acceder a Microsoft 365: {exc.message}",
                sources=["m365"],
                query_type="m365_error",
            )

        if any(k in q for k in ("correo", "email", "outlook", "buzón", "buzon", "mensaje")):
            search_term = self._extract_term(question, ("correo", "email", "outlook", "buscar", "sobre"))
            mails = await sess.client.outlook.list_messages(folder="inbox", search=search_term, limit=8)
            if mails:
                parts.append(f"Encontré {len(mails)} correos recientes:")
                for m in mails[:5]:
                    parts.append(f"• {m.subject or '(sin asunto)'} — de {m.sender_name or m.sender}")
                    links.append({"label": m.subject or "Correo", "url": "/m365/operativo", "type": "mail"})
            else:
                parts.append("No hay correos que coincidan en la bandeja de entrada.")

        if any(k in q for k in ("calendario", "reunión", "reunion", "evento", "cita")):
            events = await sess.client.calendar.list_events(limit=6)
            if events:
                parts.append(f"Próximos eventos ({len(events)}):")
                for ev in events[:4]:
                    parts.append(f"• {ev.subject} — {ev.start}")
            else:
                parts.append("No hay eventos próximos en el calendario.")

        if any(k in q for k in ("archivo", "onedrive", "sharepoint", "documento", "repositorio")):
            repo = await M365RepositoryService(self.db, self.tenant_id, self.user_id).list_files(
                search=self._extract_term(question, ("archivo", "documento", "buscar", "sobre")),
                limit=8,
            )
            if repo.items:
                parts.append(f"Repositorio M365 — {len(repo.items)} documentos:")
                for f in repo.items[:5]:
                    parts.append(f"• [{f.document_category_label}] {f.name}")
            else:
                od = await sess.client.onedrive.list_items(search=self._extract_term(question, ()), limit=5)
                for item in od:
                    parts.append(f"• OneDrive: {item.name}")

        qdrant = M365QdrantService(self.tenant_id)
        if qdrant.is_ready():
            semantic = qdrant.search(question, limit=5)
            if semantic:
                parts.append("Búsqueda semántica M365:")
                for hit in semantic[:4]:
                    parts.append(f"• {hit['title']} ({hit['source']}) — {hit['snippet'][:80]}")

        if not parts:
            results = await sess.client.outlook.list_messages(search=self._extract_term(question, ()), limit=3)
            if results:
                parts.append("Resultados en correo:")
                for m in results:
                    parts.append(f"• {m.subject}")
            else:
                parts.append(
                    "Puedo buscar en correo, calendario, archivos y repositorio. "
                    "Pruebe: «correos sobre licitación», «eventos de hoy», «documentos legales»."
                )

        return AssistantQueryResponse(
            question=question,
            answer="\n".join(parts),
            sources=["m365"],
            query_type="m365_query",
            links=links,
        )

    @staticmethod
    def _extract_term(question: str, skip: tuple[str, ...]) -> str:
        words = [w for w in question.split() if w.lower() not in skip and len(w) > 2]
        return " ".join(words[:6]) if words else question[:60]

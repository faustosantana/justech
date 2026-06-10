"""Enterprise Knowledge Graph — relaciones cross-módulo (Fase 4)."""

from __future__ import annotations

from app.schemas.search import EnterpriseSearchResponse, SearchResultGroup
from app.services.entity_resolution_engine import ResolvedEntity


class EnterpriseKnowledgeGraph:
    GROUP_TO_NODE = {
        "customers": ("cliente", "Cliente"),
        "products": ("producto", "Producto"),
        "invoices": ("factura", "Factura"),
        "quotations": ("cotización", "Cotización"),
        "vendors": ("proveedor", "Proveedor"),
        "dgcp": ("licitación", "Licitación"),
        "documents": ("documento", "Documento"),
        "knowledge": ("conocimiento", "Documento legal"),
        "tasks": ("tarea", "Tarea"),
        "notifications": ("notificación", "Alerta"),
        "opportunities": ("oportunidad", "Oportunidad"),
        "projects": ("proyecto", "Proyecto"),
    }

    @classmethod
    def build(
        cls,
        *,
        query: str,
        entities: list[ResolvedEntity],
        response: EnterpriseSearchResponse,
    ) -> dict:
        nodes: list[dict] = []
        edges: list[dict] = []
        center_id = "query-root"

        nodes.append({
            "id": center_id,
            "label": query[:80],
            "type": "consulta",
            "module": "search",
        })

        for ent in entities[:3]:
            eid = f"entity-{ent.entity_id}"
            nodes.append({
                "id": eid,
                "label": ent.canonical_name,
                "type": ent.entity_type,
                "module": "entity_resolution",
                "confidence": ent.confidence,
            })
            edges.append({"from": center_id, "to": eid, "relation": "resuelve_a"})

        entity_ids = {e.entity_id for e in entities}
        for group in response.groups:
            gtype, _ = cls.GROUP_TO_NODE.get(group.type, (group.type, group.label))
            hub_id = f"hub-{group.type}"
            nodes.append({
                "id": hub_id,
                "label": group.label,
                "type": gtype,
                "module": group.type,
                "count": group.count,
            })
            edges.append({"from": center_id, "to": hub_id, "relation": "incluye"})

            for item in group.items[:4]:
                nid = f"{group.type}-{item.id}"
                nodes.append({
                    "id": nid,
                    "label": item.title[:60],
                    "type": item.type,
                    "module": item.source,
                    "url": item.url,
                })
                edges.append({"from": hub_id, "to": nid, "relation": "contiene"})
                for ent in entities:
                    if ent.entity_id in entity_ids and ent.canonical_name.lower() in item.title.lower():
                        edges.append({
                            "from": f"entity-{ent.entity_id}",
                            "to": nid,
                            "relation": "vinculado",
                        })

        summary = cls._build_summary(response.groups)
        return {"nodes": nodes, "edges": edges, "summary": summary}

    @staticmethod
    def _build_summary(groups: list[SearchResultGroup]) -> dict[str, int]:
        out: dict[str, int] = {}
        for g in groups:
            out[g.type] = g.count
        return out

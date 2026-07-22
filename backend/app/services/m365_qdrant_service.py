"""Búsqueda semántica M365 vía Qdrant — indexación cross-M365."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from app.config import settings

VECTOR_DIM = 384
COLLECTION_SUFFIX = "m365_semantic"


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", text.lower()) if len(t) > 2]


def simple_embed(text: str, dim: int = VECTOR_DIM) -> list[float]:
    vec = [0.0] * dim
    for token in _tokenize(text):
        h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


class M365QdrantService:
    def __init__(self, tenant_id: uuid.UUID):
        self.tenant_id = tenant_id
        self.collection = f"{settings.qdrant_collection_prefix}{COLLECTION_SUFFIX}_{tenant_id.hex[:12]}"

    def _client(self):
        from qdrant_client import QdrantClient

        kwargs: dict[str, Any] = {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
            "check_compatibility": False,
        }
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        return QdrantClient(**kwargs)

    def ensure_collection(self) -> bool:
        try:
            from qdrant_client.models import Distance, VectorParams

            client = self._client()
            names = {c.name for c in client.get_collections().collections}
            if self.collection not in names:
                client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
            return True
        except Exception:
            return False

    def is_ready(self) -> bool:
        try:
            self._client().get_collections()
            return True
        except Exception:
            return False

    def upsert_document(
        self,
        *,
        doc_id: str,
        title: str,
        text: str,
        source: str,
        category: str = "",
        url: str = "",
        metadata: dict | None = None,
    ) -> bool:
        if not self.ensure_collection():
            return False
        try:
            from qdrant_client.models import PointStruct

            payload = {
                "title": title,
                "text": text[:4000],
                "source": source,
                "category": category,
                "url": url,
                "tenant_id": str(self.tenant_id),
                **(metadata or {}),
            }
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{self.tenant_id}:{doc_id}"))
            self._client().upsert(
                collection_name=self.collection,
                points=[PointStruct(id=point_id, vector=simple_embed(f"{title} {text}"), payload=payload)],
            )
            return True
        except Exception:
            return False

    def search(self, query: str, *, limit: int = 20, source: str | None = None) -> list[dict]:
        if not query.strip() or not self.ensure_collection():
            return []
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            flt = Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=str(self.tenant_id)))]
            )
            if source:
                flt.must.append(FieldCondition(key="source", match=MatchValue(value=source)))

            response = self._client().query_points(
                collection_name=self.collection,
                query=simple_embed(query),
                query_filter=flt,
                limit=limit,
            )
            hits = []
            for r in response.points:
                p = r.payload or {}
                hits.append({
                    "title": p.get("title", ""),
                    "snippet": (p.get("text") or "")[:200],
                    "source": p.get("source", "m365"),
                    "category": p.get("category", ""),
                    "url": p.get("url", ""),
                    "score": round(r.score, 3),
                    "match_reason": f"Similitud semántica ({round(r.score * 100)}%)",
                })
            return hits
        except Exception:
            return []

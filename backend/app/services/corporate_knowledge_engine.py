"""Corporate Knowledge Engine — descubrimiento, clasificación y grafo (Fase 7.2)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge import (
    KnowledgeAlert,
    KnowledgeAsset,
    KnowledgeEntity,
    KnowledgeRelationship,
    KnowledgeSyncState,
)
from app.models.document import DocumentChunk
from app.schemas.knowledge import (
    KnowledgeAssetListResponse,
    KnowledgeAssetResponse,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphResponse,
    KnowledgeHealthResponse,
    KnowledgeSearchHit,
    KnowledgeSearchResponse,
    KnowledgeSyncResult,
    KnowledgeVigencyItem,
    KnowledgeVigencyResponse,
)
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_intelligence_engine import DocumentIntelligenceEngine
from app.services.document_repository_catalog import count_by_category, enrich_asset
from app.services.knowledge_classifier import COMPANY_LABELS, KnowledgeClassifier
from app.services.knowledge_source_provider import get_knowledge_source_provider
from app.services.vigency_engine import VigencyEngine


class CorporateKnowledgeEngine:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.source = get_knowledge_source_provider()
        self.classifier = KnowledgeClassifier()
        self.vigency = VigencyEngine()
        self.extractor = DocumentExtractionService()
        self.intelligence = DocumentIntelligenceEngine()

    async def health(self) -> KnowledgeHealthResponse:
        total = await self.db.scalar(
            select(func.count()).select_from(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == self.tenant_id,
                KnowledgeAsset.is_active.is_(True),
            )
        )
        entities = await self.db.scalar(
            select(func.count()).select_from(KnowledgeEntity).where(
                KnowledgeEntity.tenant_id == self.tenant_id,
            )
        )
        alerts = await self.db.scalar(
            select(func.count()).select_from(KnowledgeAlert).where(
                KnowledgeAlert.tenant_id == self.tenant_id,
                KnowledgeAlert.is_resolved.is_(False),
            )
        )
        state = await self._get_sync_state()
        active_assets = list(
            (await self.db.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.tenant_id == self.tenant_id,
                    KnowledgeAsset.is_active.is_(True),
                    KnowledgeAsset.folder_category.in_(
                        tuple(settings.knowledge_sync_folder_list)
                    ),
                )
            )).scalars().all()
        )
        chunks = await self.db.scalar(
            select(func.count()).select_from(DocumentChunk).where(
                DocumentChunk.tenant_id == self.tenant_id
            )
        )
        return KnowledgeHealthResponse(
            enabled=settings.knowledge_source_enabled,
            source_path=self.source.root_path(),
            source_available=self.source.is_available(),
            assets_count=int(total or 0),
            entities_count=int(entities or 0),
            alerts_open=int(alerts or 0),
            last_sync_at=state.last_sync_at if state else None,
            sync_folders=settings.knowledge_sync_folder_list,
            category_counts=count_by_category(active_assets),
            chunks_count=int(chunks or 0),
        )

    async def sync(self) -> KnowledgeSyncResult:
        started = datetime.now(timezone.utc)
        errors: list[str] = []
        created = updated = alerts_created = 0

        if not settings.knowledge_source_enabled:
            return KnowledgeSyncResult(
                source_provider=self.source.provider_name,
                assets_synced=0, assets_created=0, assets_updated=0,
                entities_created=0, relationships_created=0, alerts_created=0,
                duration_ms=0, errors=["Knowledge source disabled"],
            )

        if not self.source.is_available():
            return KnowledgeSyncResult(
                source_provider=self.source.provider_name,
                assets_synced=0, assets_created=0, assets_updated=0,
                entities_created=0, relationships_created=0, alerts_created=0,
                duration_ms=0, errors=[f"Source not available: {self.source.root_path()}"],
            )

        files = self.source.list_files(settings.knowledge_sync_folder_list)
        seen_paths: set[str] = set()

        for info in files:
            seen_paths.add(info.relative_path)
            try:
                is_new, asset = await self._upsert_asset(info)
                if is_new:
                    created += 1
                else:
                    updated += 1
                if await self._sync_alerts(asset):
                    alerts_created += 1
            except Exception as exc:
                errors.append(f"{info.relative_path}: {exc}")

        await self._deactivate_missing(seen_paths)
        graph_stats = await self.rebuild_graph()

        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        await self._save_sync_state(len(files), created, updated, errors)

        return KnowledgeSyncResult(
            source_provider=self.source.provider_name,
            assets_synced=len(files),
            assets_created=created,
            assets_updated=updated,
            entities_created=graph_stats["entities"],
            relationships_created=graph_stats["relationships"],
            alerts_created=alerts_created,
            duration_ms=elapsed,
            errors=errors[:20],
        )

    async def _upsert_asset(self, info) -> tuple[bool, KnowledgeAsset]:
        result = await self.db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == self.tenant_id,
                KnowledgeAsset.source_provider == self.source.provider_name,
                KnowledgeAsset.relative_path == info.relative_path,
            )
        )
        existing = result.scalar_one_or_none()
        text = ""
        if info.filename.lower().endswith((".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".csv", ".rtf", ".odt")):
            try:
                content = self.source.read_bytes(info.relative_path)
                extraction = self.extractor.extract(content, filename=info.filename, mime_type=info.mime_type)
                text = extraction.text[:50000]
            except Exception:
                text = ""

        classified = self.classifier.classify(
            relative_path=info.relative_path,
            filename=info.filename,
            text=text,
            folder_name=info.folder_category,
        )
        intel = self.intelligence.analyze(
            text=text, title=info.filename, filename=info.filename, category=classified.document_type
        )

        valid_from = self._parse_date(classified.valid_from)
        valid_until = self._parse_date(classified.valid_until)
        if not valid_until and intel.expirations:
            for exp in intel.expirations:
                raw = exp.get("date_raw")
                if raw:
                    parsed = self._parse_date_raw(raw)
                    if parsed:
                        valid_until = parsed
                        break

        vigency_status = self.vigency.classify(valid_until)
        now = datetime.now(timezone.utc)

        if existing and existing.content_hash == info.content_hash:
            existing.vigency_status = vigency_status
            existing.valid_until = valid_until
            existing.valid_from = valid_from
            existing.is_active = True
            existing.synced_at = datetime.now(timezone.utc)
            await self.db.commit()
            return False, existing

        asset = existing or KnowledgeAsset(
            tenant_id=self.tenant_id,
            source_provider=self.source.provider_name,
            source_root=self.source.root_path(),
            relative_path=info.relative_path,
        )
        asset.folder_category = info.folder_category
        asset.filename = info.filename
        asset.title = info.filename
        asset.format = self.extractor.detect_format(info.filename, info.mime_type)
        asset.document_type = classified.document_type
        asset.company_key = classified.company_key
        asset.supplier_name = classified.supplier_name
        asset.manufacturer_name = classified.manufacturer_name
        asset.client_name = classified.client_name
        asset.mime_type = info.mime_type
        asset.file_size = info.file_size
        asset.content_hash = info.content_hash
        asset.source_modified_at = info.modified_at
        asset.extracted_text = text or None
        asset.intelligence = intel.model_dump(mode="json")
        asset.metadata_ = {"folder_category": classified.folder_category}
        asset.valid_from = valid_from
        asset.valid_until = valid_until
        asset.vigency_status = vigency_status
        asset.tags = classified.tags
        asset.keywords = classified.keywords
        asset.synced_at = now
        asset.analyzed_at = now
        asset.is_active = True

        if not existing:
            self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return existing is None, asset

    async def rebuild_graph(self) -> dict[str, int]:
        await self.db.execute(
            delete(KnowledgeRelationship).where(KnowledgeRelationship.tenant_id == self.tenant_id)
        )
        await self.db.execute(
            delete(KnowledgeEntity).where(KnowledgeEntity.tenant_id == self.tenant_id)
        )
        await self.db.commit()

        entities_created = 0
        relationships_created = 0

        for company_key, label in COMPANY_LABELS.items():
            ent = await self._ensure_entity("company", company_key, label, company_key=company_key)
            entities_created += 1

            assets = await self.db.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.tenant_id == self.tenant_id,
                    KnowledgeAsset.company_key == company_key,
                    KnowledgeAsset.is_active.is_(True),
                )
            )
            for asset in assets.scalars().all():
                doc_ent = await self._ensure_entity(
                    "document_type", asset.document_type, asset.document_type.replace("_", " ").title()
                )
                entities_created += 1
                await self._link(ent.id, doc_ent.id, "has_document", asset.id)
                relationships_created += 1

                if asset.supplier_name:
                    sup = await self._ensure_entity(
                        "supplier", asset.supplier_name.lower().replace(" ", "_"), asset.supplier_name
                    )
                    entities_created += 1
                    await self._link(sup.id, doc_ent.id, "supplies", asset.id)
                    relationships_created += 1

                if asset.manufacturer_name:
                    mfr = await self._ensure_entity(
                        "manufacturer",
                        asset.manufacturer_name.lower().replace(" ", "_"),
                        asset.manufacturer_name,
                    )
                    entities_created += 1
                    await self._link(mfr.id, doc_ent.id, "certifies", asset.id)
                    relationships_created += 1

        await self.db.commit()
        return {"entities": entities_created, "relationships": relationships_created}

    async def get_graph(self) -> KnowledgeGraphResponse:
        entities = list(
            (await self.db.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.tenant_id == self.tenant_id)
            )).scalars().all()
        )
        rels = list(
            (await self.db.execute(
                select(KnowledgeRelationship).where(KnowledgeRelationship.tenant_id == self.tenant_id)
            )).scalars().all()
        )
        doc_counts: dict[uuid.UUID, int] = {}
        for rel in rels:
            if rel.relationship_type == "has_document" and rel.from_entity_id:
                doc_counts[rel.from_entity_id] = doc_counts.get(rel.from_entity_id, 0) + 1

        nodes = [
            KnowledgeGraphNode(
                id=e.id,
                entity_type=e.entity_type,
                slug=e.slug,
                name=e.name,
                company_key=e.company_key,
                document_count=doc_counts.get(e.id, 0),
            )
            for e in entities
        ]
        edges = [
            KnowledgeGraphEdge(
                from_id=r.from_entity_id,
                to_id=r.to_entity_id,
                relationship_type=r.relationship_type,
            )
            for r in rels
        ]
        return KnowledgeGraphResponse(nodes=nodes, edges=edges)

    async def list_assets(
        self,
        *,
        document_type: str | None = None,
        company_key: str | None = None,
        repository_category: str | None = None,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> KnowledgeAssetListResponse:
        stmt = select(KnowledgeAsset).where(
            KnowledgeAsset.tenant_id == self.tenant_id,
            KnowledgeAsset.is_active.is_(True),
            KnowledgeAsset.folder_category.in_(
                tuple(settings.knowledge_sync_folder_list)
            ),
        )
        if document_type:
            stmt = stmt.where(KnowledgeAsset.document_type == document_type)
        if company_key:
            stmt = stmt.where(KnowledgeAsset.company_key == company_key)
        if search:
            pat = f"%{search}%"
            stmt = stmt.where(
                or_(
                    KnowledgeAsset.title.ilike(pat),
                    KnowledgeAsset.filename.ilike(pat),
                    KnowledgeAsset.extracted_text.ilike(pat),
                    KnowledgeAsset.document_type.ilike(pat),
                )
            )
        rows = list((await self.db.execute(stmt.order_by(KnowledgeAsset.updated_at.desc()))).scalars().all())
        if repository_category:
            rows = [
                a for a in rows
                if enrich_asset(a)["repository_category"] == repository_category
            ]
        total = len(rows)
        page = rows[offset : offset + limit]
        items = [self._asset_response(a) for a in page]
        return KnowledgeAssetListResponse(items=items, total=int(total))

    async def search(self, query: str, limit: int = 20) -> KnowledgeSearchResponse:
        pat = f"%{query}%"
        stmt = (
            select(KnowledgeAsset)
            .where(
                KnowledgeAsset.tenant_id == self.tenant_id,
                KnowledgeAsset.is_active.is_(True),
                or_(
                    KnowledgeAsset.title.ilike(pat),
                    KnowledgeAsset.filename.ilike(pat),
                    KnowledgeAsset.extracted_text.ilike(pat),
                    KnowledgeAsset.document_type.ilike(pat),
                    KnowledgeAsset.supplier_name.ilike(pat),
                    KnowledgeAsset.manufacturer_name.ilike(pat),
                ),
            )
            .limit(limit)
        )
        hits: list[KnowledgeSearchHit] = []
        for asset in (await self.db.execute(stmt)).scalars().all():
            snippet = (asset.extracted_text or asset.filename)[:200]
            score = 90.0 if query.lower() in asset.filename.lower() else 70.0
            hits.append(
                KnowledgeSearchHit(
                    asset_id=asset.id,
                    title=asset.title,
                    document_type=asset.document_type,
                    company_key=asset.company_key,
                    relative_path=asset.relative_path,
                    snippet=snippet,
                    score=score,
                )
            )
        return KnowledgeSearchResponse(query=query, hits=hits, total=len(hits))

    async def vigencies(self) -> KnowledgeVigencyResponse:
        assets = list(
            (await self.db.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.tenant_id == self.tenant_id,
                    KnowledgeAsset.is_active.is_(True),
                    KnowledgeAsset.document_type.in_(
                        ("rpe", "dgii", "tss", "registro_mercantil", "certificacion_bancaria")
                    ),
                )
            )).scalars().all()
        )
        resp = KnowledgeVigencyResponse()
        for asset in assets:
            item = KnowledgeVigencyItem(
                asset_id=asset.id,
                title=asset.title,
                document_type=asset.document_type,
                company_key=asset.company_key,
                valid_until=asset.valid_until,
                vigency_status=asset.vigency_status,
                relative_path=asset.relative_path,
            )
            bucket = getattr(resp, asset.vigency_status, None)
            if bucket is not None:
                bucket.append(item)
            else:
                resp.sin_fecha.append(item)
        return resp

    def get_company_profile(self, company_key: str = "justech") -> dict:
        profile = {}
        key = company_key.lower().replace(" ", "_")
        path = f"00_DATOS_EMPRESAS/{key.upper()}/datos_empresa.json"
        alt_paths = [
            f"00_DATOS_EMPRESAS/JUSTECH/datos_empresa.json",
            f"00_DATOS_EMPRESAS/{company_key.upper()}/datos_empresa.json",
        ]
        if key == "justech":
            alt_paths = [f"00_DATOS_EMPRESAS/JUSTECH/datos_empresa.json"]
        for rel in alt_paths:
            try:
                raw = self.source.read_bytes(rel)
                data = json.loads(raw.decode("utf-8"))
                profile = {
                    "razon_social": data.get("empresa") or data.get("razon_social"),
                    "rnc": data.get("rnc"),
                    "rpe": data.get("rpe"),
                    "direccion": data.get("direccion"),
                    "telefono": data.get("telefono_principal") or data.get("telefono"),
                    "correo": data.get("correo_principal") or data.get("correo"),
                    "representante_legal": data.get("representante_legal"),
                    "ciudad": data.get("ciudad"),
                    "sitio_web": data.get("sitio_web"),
                }
                profile = {k: v for k, v in profile.items() if v}
                if profile:
                    return profile
            except Exception:
                continue
        return profile

    async def find_by_document_type(
        self,
        document_type: str,
        *,
        company_key: str | None = None,
    ) -> list[KnowledgeAsset]:
        stmt = select(KnowledgeAsset).where(
            KnowledgeAsset.tenant_id == self.tenant_id,
            KnowledgeAsset.is_active.is_(True),
            KnowledgeAsset.document_type == document_type,
        )
        if company_key:
            stmt = stmt.where(KnowledgeAsset.company_key == company_key)
        stmt = stmt.order_by(KnowledgeAsset.valid_until.desc().nullslast())
        return list((await self.db.execute(stmt)).scalars().all())

    async def _ensure_entity(
        self,
        entity_type: str,
        slug: str,
        name: str,
        *,
        company_key: str | None = None,
    ) -> KnowledgeEntity:
        result = await self.db.execute(
            select(KnowledgeEntity).where(
                KnowledgeEntity.tenant_id == self.tenant_id,
                KnowledgeEntity.entity_type == entity_type,
                KnowledgeEntity.slug == slug,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        ent = KnowledgeEntity(
            tenant_id=self.tenant_id,
            entity_type=entity_type,
            slug=slug,
            name=name,
            company_key=company_key,
        )
        self.db.add(ent)
        await self.db.flush()
        return ent

    async def _link(
        self,
        from_id: uuid.UUID,
        to_id: uuid.UUID,
        rel_type: str,
        asset_id: uuid.UUID | None = None,
    ) -> None:
        rel = KnowledgeRelationship(
            tenant_id=self.tenant_id,
            from_entity_id=from_id,
            to_entity_id=to_id,
            relationship_type=rel_type,
            knowledge_asset_id=asset_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(rel)

    async def _sync_alerts(self, asset: KnowledgeAsset) -> bool:
        alert_data = self.vigency.alert_for_status(
            title=asset.title,
            document_type=asset.document_type,
            status=asset.vigency_status,
            valid_until=asset.valid_until,
        )
        if not alert_data:
            return False
        existing = await self.db.execute(
            select(KnowledgeAlert).where(
                KnowledgeAlert.tenant_id == self.tenant_id,
                KnowledgeAlert.knowledge_asset_id == asset.id,
                KnowledgeAlert.alert_type == alert_data["alert_type"],
                KnowledgeAlert.is_resolved.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            return False
        self.db.add(
            KnowledgeAlert(
                tenant_id=self.tenant_id,
                knowledge_asset_id=asset.id,
                **alert_data,
            )
        )
        await self.db.commit()
        return True

    async def _deactivate_missing(self, seen_paths: set[str]) -> None:
        result = await self.db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == self.tenant_id,
                KnowledgeAsset.is_active.is_(True),
            )
        )
        for asset in result.scalars().all():
            if asset.relative_path not in seen_paths:
                asset.is_active = False
        await self.db.commit()

    async def _get_sync_state(self) -> KnowledgeSyncState | None:
        result = await self.db.execute(
            select(KnowledgeSyncState).where(
                KnowledgeSyncState.tenant_id == self.tenant_id,
                KnowledgeSyncState.source_provider == self.source.provider_name,
            )
        )
        return result.scalar_one_or_none()

    async def _save_sync_state(
        self,
        synced: int,
        created: int,
        updated: int,
        errors: list[str],
    ) -> None:
        state = await self._get_sync_state()
        now = datetime.now(timezone.utc)
        if not state:
            state = KnowledgeSyncState(
                tenant_id=self.tenant_id,
                source_provider=self.source.provider_name,
            )
            self.db.add(state)
        state.last_sync_at = now
        state.assets_synced = synced
        state.assets_created = created
        state.assets_updated = updated
        state.last_error = "; ".join(errors[:5]) if errors else None
        await self.db.commit()

    @staticmethod
    def _asset_response(asset: KnowledgeAsset) -> KnowledgeAssetResponse:
        extra = enrich_asset(asset)
        return KnowledgeAssetResponse(
            id=asset.id,
            source_provider=asset.source_provider,
            relative_path=asset.relative_path,
            folder_category=asset.folder_category,
            filename=asset.filename,
            title=asset.filename,
            display_name=extra["display_name"],
            format=asset.format,
            document_type=asset.document_type,
            repository_category=extra["repository_category"],
            repository_category_label=extra["repository_category_label"],
            display_type=extra["display_type"],
            display_status=extra["display_status"],
            sncc_label=extra.get("sncc_label"),
            detected_supplier=extra.get("detected_supplier"),
            requires_vigency=extra["requires_vigency"],
            company_key=asset.company_key,
            supplier_name=asset.supplier_name,
            manufacturer_name=asset.manufacturer_name,
            client_name=asset.client_name,
            valid_from=asset.valid_from,
            valid_until=asset.valid_until,
            vigency_status=asset.vigency_status,
            tags=list(asset.tags or []),
            synced_at=asset.synced_at,
            analyzed_at=asset.analyzed_at,
        )

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    @staticmethod
    def _parse_date_raw(raw: str) -> date | None:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None

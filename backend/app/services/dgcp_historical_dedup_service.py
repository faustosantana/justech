"""Deduplicación profesional de identidades históricas (sin borrar filas fuente)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_historical_award import DGCPHistoricalAward, DGCPHistoricalIdentityAction
from app.services.dgcp_historical_identity import (
    classify_name_pair,
    institution_stable_key,
    normalize_party_name,
    supplier_stable_key,
)
from app.services.dgcp_historical_profile_service import _cache_clear_prefix


class DGCPHistoricalDedupService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def conservation_snapshot(self) -> dict[str, Any]:
        row = (
            await self.db.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(DGCPHistoricalAward.awarded_amount), 0),
                    func.count(func.distinct(DGCPHistoricalAward.process_code)),
                    func.count(func.distinct(DGCPHistoricalAward.supplier_rpe)),
                    func.count(func.distinct(DGCPHistoricalAward.buyer_institution_code)),
                ).where(DGCPHistoricalAward.tenant_id == self.tenant_id)
            )
        ).one()
        return {
            "lines": int(row[0] or 0),
            "total_amount": float(row[1] or 0),
            "processes": int(row[2] or 0),
            "supplier_rpe_identities": int(row[3] or 0),
            "institution_code_identities": int(row[4] or 0),
        }

    async def active_merge_map(self, party_type: str = "supplier") -> dict[str, str]:
        """Alias → canonical key for active merges."""
        q = await self.db.execute(
            select(DGCPHistoricalIdentityAction).where(
                and_(
                    DGCPHistoricalIdentityAction.tenant_id == self.tenant_id,
                    DGCPHistoricalIdentityAction.party_type == party_type,
                    DGCPHistoricalIdentityAction.action == "merge",
                    DGCPHistoricalIdentityAction.status == "active",
                )
            )
        )
        mapping: dict[str, str] = {}
        for row in q.scalars().all():
            canon = row.canonical_key or row.identity_a
            mapping[row.identity_a] = canon
            mapping[row.identity_b] = canon
        return mapping

    def resolve_canonical(self, key: str, merge_map: dict[str, str]) -> str:
        seen: set[str] = set()
        cur = key
        while cur in merge_map and cur not in seen:
            seen.add(cur)
            cur = merge_map[cur]
        return cur

    async def list_possible_supplier_duplicates(self, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(
                    DGCPHistoricalAward.supplier_name,
                    DGCPHistoricalAward.supplier_rpe,
                    func.count().label("awards_count"),
                    func.coalesce(func.sum(DGCPHistoricalAward.awarded_amount), 0).label("total_amount"),
                )
                .where(
                    and_(
                        DGCPHistoricalAward.tenant_id == self.tenant_id,
                        DGCPHistoricalAward.supplier_name.is_not(None),
                    )
                )
                .group_by(DGCPHistoricalAward.supplier_name, DGCPHistoricalAward.supplier_rpe)
            )
        ).all()

        parties = [
            {
                "display_name": name,
                "display_name_original": name,
                "name_norm": normalize_party_name(name),
                "rpe": rpe,
                "rnc": None,
                "awards_count": int(c),
                "total_amount": float(amt or 0),
                "identity_key": supplier_stable_key(rpe=rpe, name=name, rnc=None),
            }
            for name, rpe, c, amt in rows
            if name
        ]

        ignored = await self._ignored_pairs("supplier")
        kept = await self._kept_pairs("supplier")
        merge_map = await self.active_merge_map("supplier")

        # Index by first significant token for candidate generation
        by_prefix: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for p in parties:
            tokens = [t for t in p["name_norm"].split() if len(t) > 2][:3]
            if not tokens:
                continue
            by_prefix[" ".join(tokens[:2])].append(p)

        out: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()
        for group in by_prefix.values():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    if a["identity_key"] == b["identity_key"]:
                        continue
                    # Already same via merge
                    if self.resolve_canonical(a["identity_key"], merge_map) == self.resolve_canonical(
                        b["identity_key"], merge_map
                    ):
                        continue
                    pair = tuple(sorted([a["identity_key"], b["identity_key"]]))
                    if pair in seen_pairs or pair in ignored or pair in kept:
                        continue
                    status, conf, reason = classify_name_pair(
                        name_a=a["display_name"],
                        name_b=b["display_name"],
                        rpe_a=a["rpe"],
                        rpe_b=b["rpe"],
                    )
                    if status in ("NOT_DUPLICATE",):
                        continue
                    if status == "REVIEW_REQUIRED" and conf < 0.75:
                        continue
                    seen_pairs.add(pair)
                    out.append(
                        {
                            "party_type": "supplier",
                            "supplier_a": a,
                            "supplier_b": b,
                            "rnc_a": a.get("rnc"),
                            "rnc_b": b.get("rnc"),
                            "rpe_a": a.get("rpe"),
                            "rpe_b": b.get("rpe"),
                            "name_norm_a": a["name_norm"],
                            "name_norm_b": b["name_norm"],
                            "awards_a": a["awards_count"],
                            "awards_b": b["awards_count"],
                            "confidence": round(conf, 3),
                            "status": status,
                            "reason": reason,
                            "auto_merge_allowed": False,
                        }
                    )
        out.sort(key=lambda x: (-x["confidence"], -(x["awards_a"] + x["awards_b"])))
        return out[:limit]

    async def list_possible_institution_duplicates(self, *, limit: int = 30) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(
                    DGCPHistoricalAward.buyer_institution,
                    DGCPHistoricalAward.buyer_institution_code,
                    func.count().label("awards_count"),
                )
                .where(DGCPHistoricalAward.tenant_id == self.tenant_id)
                .group_by(DGCPHistoricalAward.buyer_institution, DGCPHistoricalAward.buyer_institution_code)
            )
        ).all()
        parties = [
            {
                "display_name": name,
                "name_norm": normalize_party_name(name),
                "code": code,
                "awards_count": int(c),
                "identity_key": institution_stable_key(code=code, name=name),
            }
            for name, code, c in rows
            if name
        ]
        ignored = await self._ignored_pairs("institution")
        kept = await self._kept_pairs("institution")
        by_norm: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for p in parties:
            if p["name_norm"]:
                by_norm[p["name_norm"]].append(p)

        out: list[dict[str, Any]] = []
        for _norm, group in by_norm.items():
            codes = {g["code"] for g in group if g["code"]}
            if len(codes) <= 1 and len({g["identity_key"] for g in group}) <= 1:
                continue
            # same normalized name, different codes → candidate only
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    if a["identity_key"] == b["identity_key"]:
                        continue
                    if a["code"] and b["code"] and a["code"] == b["code"]:
                        continue  # already same identity by code
                    pair = tuple(sorted([a["identity_key"], b["identity_key"]]))
                    if pair in ignored or pair in kept:
                        continue
                    out.append(
                        {
                            "party_type": "institution",
                            "institution_a": a,
                            "institution_b": b,
                            "confidence": 0.8,
                            "status": "POSSIBLE_DUPLICATE",
                            "reason": "SAME_NORMALIZED_NAME_DIFFERENT_CODE",
                            "auto_merge_allowed": False,
                        }
                    )
        return out[:limit]

    async def apply_action(
        self,
        *,
        party_type: str,
        identity_a: str,
        identity_b: str,
        action: str,
        actor_user_id: uuid.UUID | None = None,
        note: str | None = None,
        criterion: str | None = None,
        confidence: str | None = None,
    ) -> DGCPHistoricalIdentityAction:
        canonical: str | None = None

        if action == "unmerge":
            q = await self.db.execute(
                select(DGCPHistoricalIdentityAction).where(
                    and_(
                        DGCPHistoricalIdentityAction.tenant_id == self.tenant_id,
                        DGCPHistoricalIdentityAction.party_type == party_type,
                        DGCPHistoricalIdentityAction.action == "merge",
                        DGCPHistoricalIdentityAction.status == "active",
                    )
                )
            )
            for existing in q.scalars().all():
                keys = {existing.identity_a, existing.identity_b, existing.canonical_key}
                if identity_a in keys and identity_b in keys:
                    existing.status = "reversed"
            row = DGCPHistoricalIdentityAction(
                tenant_id=self.tenant_id,
                party_type=party_type,
                identity_a=identity_a,
                identity_b=identity_b,
                action="unmerge",
                criterion=criterion or "MANUAL",
                confidence=confidence,
                status="active",
                actor_user_id=actor_user_id,
                note=note,
            )
            self.db.add(row)
            await self.db.flush()
            _cache_clear_prefix(f"sup:{self.tenant_id}:")
            _cache_clear_prefix(f"inst:{self.tenant_id}:")
            return row

        if action == "merge":
            canonical = self._prefer_canonical(identity_a, identity_b)

        row = DGCPHistoricalIdentityAction(
            tenant_id=self.tenant_id,
            party_type=party_type,
            identity_a=identity_a,
            identity_b=identity_b,
            canonical_key=canonical if action == "merge" else None,
            action=action,
            criterion=criterion or ("MANUAL_MERGE" if action == "merge" else action.upper()),
            confidence=confidence,
            status="active",
            actor_user_id=actor_user_id,
            note=note,
        )
        self.db.add(row)
        await self.db.flush()
        _cache_clear_prefix(f"sup:{self.tenant_id}:")
        _cache_clear_prefix(f"inst:{self.tenant_id}:")
        return row

    @staticmethod
    def _prefer_canonical(a: str, b: str) -> str:
        def rank(k: str) -> int:
            if k.startswith("rnc-"):
                return 0
            if k.startswith("rpe-") or k.startswith("code-"):
                return 1
            if k.startswith("dgcp-"):
                return 2
            return 3

        return a if rank(a) <= rank(b) else b

    async def _ignored_pairs(self, party_type: str) -> set[tuple[str, str]]:
        return await self._pairs_for_actions(party_type, ("ignore",))

    async def _kept_pairs(self, party_type: str) -> set[tuple[str, str]]:
        return await self._pairs_for_actions(party_type, ("keep_separate",))

    async def _pairs_for_actions(self, party_type: str, actions: tuple[str, ...]) -> set[tuple[str, str]]:
        q = await self.db.execute(
            select(DGCPHistoricalIdentityAction).where(
                and_(
                    DGCPHistoricalIdentityAction.tenant_id == self.tenant_id,
                    DGCPHistoricalIdentityAction.party_type == party_type,
                    DGCPHistoricalIdentityAction.action.in_(actions),
                    DGCPHistoricalIdentityAction.status == "active",
                )
            )
        )
        out: set[tuple[str, str]] = set()
        for row in q.scalars().all():
            out.add(tuple(sorted([row.identity_a, row.identity_b])))
        return out

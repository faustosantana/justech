"""Perfiles 360° proveedor e institución sobre dgcp_historical_awards (índice local)."""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean, median
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_historical_award import DGCPHistoricalAward
from app.schemas.dgcp_historical_intelligence import (
    ConcentrationBlock,
    DataQualitySummary,
    FrequencyBlock,
    HistoricalPurchaseRow,
    HistoricalSourceRef,
    ModalityStatsRow,
    PriceHistoryBlock,
    PricePoint,
)
from app.schemas.dgcp_historical_profiles import (
    CategoryStatRow,
    CurrencyAmount,
    DiversificationBlock,
    DGCPInstitutionProfileResponse,
    DGCPSupplierCompareResponse,
    DGCPSupplierCompareRow,
    DGCPSupplierProfileResponse,
    PartyShareRow,
    ProductAwardRow,
    ProfileIdentity,
    SupplierInstitutionPair,
    TimelineBucket,
)
from app.services.dgcp_historical_identity import (
    extract_rnc_from_payload,
    identity_confidence,
    institution_stable_key,
    normalize_party_name,
    parse_institution_key,
    parse_supplier_key,
    supplier_stable_key,
)
from app.services.dgcp_historical_similarity_engine import is_valid_award_status

logger = logging.getLogger(__name__)

UTC = timezone.utc
SCAN_LIMIT = 8000
_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 300.0


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _amt(a: DGCPHistoricalAward) -> Decimal:
    return _dec(a.awarded_amount) or _dec(a.total_line_amount) or Decimal("0")


def _valid(a: DGCPHistoricalAward) -> bool:
    if not a.award_date:
        return False
    if not is_valid_award_status(a.award_status):
        return False
    if not a.contract_url and not a.awarded_amount and not a.total_line_amount:
        return False
    return True


def _category(a: DGCPHistoricalAward) -> str:
    for v in (a.objeto_proceso, a.unspsc_family, a.modality):
        if v and str(v).strip():
            return str(v).strip()
    return "Sin categoría"


def _cache_get(key: str):
    hit = _CACHE.get(key)
    if not hit:
        return None
    ts, val = hit
    if time.time() - ts > CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key: str, val: Any) -> None:
    _CACHE[key] = (time.time(), val)
    if len(_CACHE) > 256:
        # drop oldest
        oldest = sorted(_CACHE.items(), key=lambda x: x[1][0])[:64]
        for k, _ in oldest:
            _CACHE.pop(k, None)


class DGCPHistoricalProfileService:
    def __init__(self, db: AsyncSession, tenant_id):
        self.db = db
        self.tenant_id = tenant_id

    async def get_supplier_profile(
        self,
        key: str,
        *,
        window_months: int | None = 24,
        institution_key: str | None = None,
        limit: int = 100,
    ) -> DGCPSupplierProfileResponse:
        t0 = time.perf_counter()
        window_months = None if window_months in (0, None) else max(1, min(int(window_months), 120))
        cache_key = f"sup:{self.tenant_id}:{key}:{window_months}:{institution_key}:{limit}"
        cached = _cache_get(cache_key)
        if cached:
            cached.cache_hit = True
            cached.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            return cached

        parsed = parse_supplier_key(key)
        awards = await self._load_supplier_awards(parsed, window_months=window_months)
        awards = [a for a in awards if _valid(a)]
        if not awards:
            identity = ProfileIdentity(
                stable_key=key,
                display_name=parsed.get("name_norm") or key,
                identity_kind=str(parsed.get("kind") or "name"),
                identity_confidence=identity_confidence(str(parsed.get("kind") or "name")),
                note="Sin adjudicaciones válidas en el índice para esta clave.",
            )
            return DGCPSupplierProfileResponse(
                identity=identity,
                window_months=window_months,
                message="Sin datos verificables en el índice local.",
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            )

        display = awards[0].supplier_name or key
        rpe = next((a.supplier_rpe for a in awards if a.supplier_rpe), None)
        rnc = next((extract_rnc_from_payload(a.raw_payload) for a in awards if extract_rnc_from_payload(a.raw_payload)), None)
        stable = supplier_stable_key(rpe=rpe, name=display, rnc=rnc)
        identity = ProfileIdentity(
            stable_key=stable,
            display_name=display,
            identity_kind=str(parsed.get("kind") or "name"),
            identity_confidence=identity_confidence(str(parsed.get("kind") or "name")),
            rnc=rnc,
            rpe=rpe,
            rnc_available=bool(rnc),
            rpe_available=bool(rpe),
            note=None
            if rnc or rpe
            else "RNC/RPE no disponible en la fuente; identidad por nombre normalizado (confianza sugerida).",
        )

        pair = None
        if institution_key:
            pair = self._pair_metrics(awards, display, stable, institution_key)

        resp = self._build_supplier_response(
            identity=identity,
            awards=awards,
            window_months=window_months,
            pair=pair,
            limit=limit,
            t0=t0,
        )
        _cache_set(cache_key, resp)
        logger.info(
            "historical_profile_supplier key=%s duration_ms=%.1f rows=%s cache_hit=0",
            key,
            resp.latency_ms or 0,
            resp.rows_scanned,
        )
        return resp

    async def get_institution_profile(
        self,
        key: str,
        *,
        window_months: int | None = 24,
        limit: int = 100,
    ) -> DGCPInstitutionProfileResponse:
        t0 = time.perf_counter()
        window_months = None if window_months in (0, None) else max(1, min(int(window_months), 120))
        cache_key = f"inst:{self.tenant_id}:{key}:{window_months}:{limit}"
        cached = _cache_get(cache_key)
        if cached:
            cached.cache_hit = True
            cached.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            return cached

        parsed = parse_institution_key(key)
        awards = await self._load_institution_awards(parsed, window_months=window_months)
        awards = [a for a in awards if _valid(a)]
        if not awards:
            identity = ProfileIdentity(
                stable_key=key,
                display_name=parsed.get("name_norm") or key,
                identity_kind=str(parsed.get("kind") or "name"),
                identity_confidence=identity_confidence(str(parsed.get("kind") or "name")),
                note="Sin adjudicaciones válidas en el índice.",
            )
            return DGCPInstitutionProfileResponse(
                identity=identity,
                window_months=window_months,
                message="Sin datos verificables en el índice local.",
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            )

        display = awards[0].buyer_institution
        code = next((a.buyer_institution_code for a in awards if a.buyer_institution_code), None)
        stable = institution_stable_key(code=code, name=display)
        identity = ProfileIdentity(
            stable_key=stable,
            display_name=display,
            identity_kind=str(parsed.get("kind") or "name"),
            identity_confidence=identity_confidence(str(parsed.get("kind") or "name")),
            institution_code=str(code) if code else None,
        )
        resp = self._build_institution_response(
            identity=identity,
            awards=awards,
            window_months=window_months,
            limit=limit,
            t0=t0,
        )
        _cache_set(cache_key, resp)
        logger.info(
            "historical_profile_institution key=%s duration_ms=%.1f rows=%s cache_hit=0",
            key,
            resp.latency_ms or 0,
            resp.rows_scanned,
        )
        return resp

    async def compare_suppliers(
        self, keys: list[str], *, window_months: int | None = 24
    ) -> DGCPSupplierCompareResponse:
        rows: list[DGCPSupplierCompareRow] = []
        for key in keys[:3]:
            profile = await self.get_supplier_profile(key, window_months=window_months, limit=20)
            total = profile.totals_by_currency[0].amount if profile.totals_by_currency else None
            currency = profile.totals_by_currency[0].currency if profile.totals_by_currency else "DOP"
            rows.append(
                DGCPSupplierCompareRow(
                    identity=profile.identity,
                    awards_count=profile.awards_count,
                    total_amount=total,
                    currency=currency,
                    last_award_date=profile.last_award_date,
                    institutions_count=profile.institutions_count,
                    categories_count=profile.categories_count,
                    last_12m_amount=profile.last_12m_amount,
                )
            )
        return DGCPSupplierCompareResponse(window_months=window_months, rows=rows)

    async def _load_supplier_awards(
        self, parsed: dict[str, str | None], *, window_months: int | None
    ) -> list[DGCPHistoricalAward]:
        filters = [DGCPHistoricalAward.tenant_id == self.tenant_id]
        if window_months:
            since = datetime.now(UTC) - timedelta(days=int(window_months) * 30)
            filters.append(DGCPHistoricalAward.award_date >= since)

        kind = parsed.get("kind")
        if kind == "rpe" and parsed.get("value"):
            filters.append(DGCPHistoricalAward.supplier_rpe == parsed["value"])
            q = (
                select(DGCPHistoricalAward)
                .where(and_(*filters))
                .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
                .limit(SCAN_LIMIT)
            )
            return list((await self.db.execute(q)).scalars().all())

        if kind == "rnc" and parsed.get("value"):
            # RNC lives in JSON — scan recent and filter
            q = (
                select(DGCPHistoricalAward)
                .where(and_(*filters))
                .where(DGCPHistoricalAward.supplier_name.is_not(None))
                .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
                .limit(SCAN_LIMIT)
            )
            rows = list((await self.db.execute(q)).scalars().all())
            target = parsed["value"]
            return [a for a in rows if extract_rnc_from_payload(a.raw_payload) == target]

        # name
        name_norm = parsed.get("name_norm") or ""
        token = (name_norm.split() or [""])[0]
        if len(token) >= 3:
            filters.append(DGCPHistoricalAward.supplier_name.ilike(f"%{token}%"))
        q = (
            select(DGCPHistoricalAward)
            .where(and_(*filters))
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .limit(SCAN_LIMIT)
        )
        rows = list((await self.db.execute(q)).scalars().all())
        if not name_norm:
            return rows
        out = []
        for a in rows:
            if normalize_party_name(a.supplier_name) == name_norm:
                out.append(a)
            elif name_norm and name_norm in normalize_party_name(a.supplier_name):
                # weak contain — only if confidence suggested and unique-ish
                out.append(a)
        # Prefer exact norm matches
        exact = [a for a in out if normalize_party_name(a.supplier_name) == name_norm]
        return exact or out

    async def _load_institution_awards(
        self, parsed: dict[str, str | None], *, window_months: int | None
    ) -> list[DGCPHistoricalAward]:
        filters = [DGCPHistoricalAward.tenant_id == self.tenant_id]
        if window_months:
            since = datetime.now(UTC) - timedelta(days=int(window_months) * 30)
            filters.append(DGCPHistoricalAward.award_date >= since)

        kind = parsed.get("kind")
        if kind == "code" and parsed.get("value"):
            filters.append(DGCPHistoricalAward.buyer_institution_code == parsed["value"])
            q = (
                select(DGCPHistoricalAward)
                .where(and_(*filters))
                .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
                .limit(SCAN_LIMIT)
            )
            return list((await self.db.execute(q)).scalars().all())

        name_norm = parsed.get("name_norm") or ""
        # ILIKE with accent-folded token is unreliable in Postgres; use broad name tokens.
        raw_tokens = [t for t in name_norm.split() if len(t) >= 4][:2]
        if raw_tokens:
            # Match any token (accent-insensitive enough via leading chars of original words)
            like_filters = [DGCPHistoricalAward.buyer_institution.ilike(f"%{t}%") for t in raw_tokens]
            # Also try common accented forms for Spanish public entities
            accented = {
                "direccion": "dirección",
                "educacion": "educación",
                "administracion": "administración",
                "comision": "comisión",
                "republica": "república",
            }
            for t in raw_tokens:
                if t in accented:
                    like_filters.append(DGCPHistoricalAward.buyer_institution.ilike(f"%{accented[t]}%"))
            filters.append(or_(*like_filters))
        q = (
            select(DGCPHistoricalAward)
            .where(and_(*filters))
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .limit(SCAN_LIMIT)
        )
        rows = list((await self.db.execute(q)).scalars().all())
        if not name_norm:
            return rows
        exact = [a for a in rows if normalize_party_name(a.buyer_institution) == name_norm]
        if exact:
            return exact
        return [a for a in rows if name_norm in normalize_party_name(a.buyer_institution)]

    def _to_purchase_row(self, a: DGCPHistoricalAward) -> HistoricalPurchaseRow:
        amount = _amt(a)
        qty = _dec(a.quantity)
        unit = _dec(a.unit_price)
        if unit is not None and (qty is None or float(qty) <= 0):
            unit = None
        rnc = extract_rnc_from_payload(a.raw_payload)
        quality = "VERIFICADO"
        if not (a.supplier_name and amount and a.award_date and a.process_code):
            quality = "INCOMPLETO"
        elif unit is None:
            quality = "PARCIAL"
        return HistoricalPurchaseRow(
            award_id=str(a.id),
            process_code=a.process_code,
            contract_code=a.contract_code,
            award_date=_iso(a.award_date),
            institution=a.buyer_institution,
            description=a.item_description_user or a.item_description or a.contract_object,
            supplier_name=a.supplier_name,
            supplier_rpe=a.supplier_rpe,
            supplier_rnc=rnc,
            awarded_amount=amount if amount else None,
            currency=a.currency or "DOP",
            quantity=qty,
            unit_price=unit,
            unit_measure=a.unit_measure,
            modality=a.modality,
            award_status=a.award_status,
            data_quality=quality,  # type: ignore[arg-type]
            source=HistoricalSourceRef(
                source=a.source or "dgcp_contratos",
                source_url=a.contract_url or a.process_url,
                process_url=a.process_url,
                contract_url=a.contract_url,
                dgcp_process_code=a.process_code,
                retrieved_at=_iso(a.indexed_at),
            ),
        )

    def _totals_by_currency(self, awards: list[DGCPHistoricalAward]) -> list[CurrencyAmount]:
        buckets: dict[str, dict[str, Any]] = {}
        for a in awards:
            cur = (a.currency or "DOP").upper()
            slot = buckets.setdefault(cur, {"amount": Decimal("0"), "count": 0})
            slot["amount"] += _amt(a)
            slot["count"] += 1
        rows = [
            CurrencyAmount(currency=k, amount=v["amount"], awards_count=v["count"])
            for k, v in buckets.items()
        ]
        rows.sort(key=lambda r: r.amount, reverse=True)
        return rows

    def _quality(self, awards: list[DGCPHistoricalAward], *, has_id: bool) -> DataQualitySummary:
        rows = [self._to_purchase_row(a) for a in awards[:200]]
        c = Counter(r.data_quality for r in rows)
        if has_id and c["VERIFICADO"] + c["PARCIAL"] >= max(1, len(rows) // 2):
            overall = "VERIFICADO" if c["VERIFICADO"] else "PARCIAL"
        elif awards:
            overall = "PARCIAL"
        else:
            overall = "INCOMPLETO"
        return DataQualitySummary(
            overall=overall,  # type: ignore[arg-type]
            verified_count=c["VERIFICADO"],
            partial_count=c["PARCIAL"],
            incomplete_count=c["INCOMPLETO"],
            notes=[
                "Montos = adjudicados/contratados del índice DGCP.",
                "RNC solo si viene en payload fuente.",
            ],
        )

    def _categories(self, awards: list[DGCPHistoricalAward]) -> list[CategoryStatRow]:
        buckets: dict[str, dict[str, Any]] = {}
        for a in awards:
            cat = _category(a)
            slot = buckets.setdefault(
                cat,
                {"count": 0, "processes": set(), "amount": Decimal("0"), "last": None, "cur": a.currency or "DOP"},
            )
            slot["count"] += 1
            slot["processes"].add(a.process_code)
            slot["amount"] += _amt(a)
            if a.award_date and (slot["last"] is None or a.award_date > slot["last"]):
                slot["last"] = a.award_date
        rows = [
            CategoryStatRow(
                category=k,
                awards_count=v["count"],
                process_count=len(v["processes"]),
                total_amount=v["amount"],
                currency=v["cur"],
                last_award_date=_iso(v["last"]),
            )
            for k, v in buckets.items()
        ]
        rows.sort(key=lambda r: r.total_amount, reverse=True)
        return rows

    def _modalities(self, awards: list[DGCPHistoricalAward]) -> list[ModalityStatsRow]:
        buckets: dict[str, dict[str, Any]] = {}
        for a in awards:
            key = (a.modality or "Sin modalidad").strip() or "Sin modalidad"
            slot = buckets.setdefault(key, {"processes": set(), "amount": Decimal("0"), "suppliers": set()})
            slot["processes"].add(a.process_code)
            slot["amount"] += _amt(a)
            if a.supplier_name:
                slot["suppliers"].add(a.supplier_name)
        rows = [
            ModalityStatsRow(
                modality=k,
                process_count=len(v["processes"]),
                total_amount=v["amount"],
                suppliers_count=len(v["suppliers"]),
            )
            for k, v in buckets.items()
        ]
        rows.sort(key=lambda r: r.total_amount, reverse=True)
        return rows

    def _timeline(self, awards: list[DGCPHistoricalAward]) -> list[TimelineBucket]:
        buckets: dict[str, dict[str, Any]] = {}
        for a in awards:
            if not a.award_date:
                continue
            period = a.award_date.strftime("%Y-%m")
            cur = (a.currency or "DOP").upper()
            key = f"{period}|{cur}"
            slot = buckets.setdefault(key, {"period": period, "currency": cur, "count": 0, "amount": Decimal("0")})
            slot["count"] += 1
            slot["amount"] += _amt(a)
        rows = [
            TimelineBucket(
                period=v["period"],
                awards_count=v["count"],
                amount=v["amount"],
                currency=v["currency"],
            )
            for v in buckets.values()
        ]
        rows.sort(key=lambda r: r.period)
        return rows

    def _products(self, awards: list[DGCPHistoricalAward], *, limit: int = 80) -> list[ProductAwardRow]:
        out: list[ProductAwardRow] = []
        for a in awards[:limit]:
            qty = _dec(a.quantity)
            unit = _dec(a.unit_price)
            if unit is not None and (qty is None or float(qty) <= 0):
                unit = None
            out.append(
                ProductAwardRow(
                    description_original=(
                        a.item_description_user or a.item_description or a.contract_object or "—"
                    )[:2000],
                    quantity=qty,
                    unit_measure=a.unit_measure,
                    unit_price=unit,
                    awarded_amount=_amt(a) or None,
                    currency=a.currency or "DOP",
                    institution=a.buyer_institution,
                    institution_key=institution_stable_key(
                        code=a.buyer_institution_code, name=a.buyer_institution
                    ),
                    supplier_name=a.supplier_name,
                    supplier_key=supplier_stable_key(
                        rpe=a.supplier_rpe,
                        name=a.supplier_name,
                        rnc=extract_rnc_from_payload(a.raw_payload),
                    ),
                    award_date=_iso(a.award_date),
                    process_code=a.process_code,
                    source=HistoricalSourceRef(
                        source=a.source or "dgcp_contratos",
                        source_url=a.contract_url or a.process_url,
                        process_url=a.process_url,
                        contract_url=a.contract_url,
                        dgcp_process_code=a.process_code,
                        retrieved_at=_iso(a.indexed_at),
                    ),
                )
            )
        return out

    def _pair_metrics(
        self,
        awards: list[DGCPHistoricalAward],
        supplier_name: str,
        supplier_key: str,
        institution_key: str,
    ) -> SupplierInstitutionPair | None:
        parsed = parse_institution_key(institution_key)
        filtered: list[DGCPHistoricalAward] = []
        for a in awards:
            if parsed.get("kind") == "code" and parsed.get("value"):
                if str(a.buyer_institution_code or "") == parsed["value"]:
                    filtered.append(a)
            else:
                nn = parsed.get("name_norm") or ""
                if nn and nn in normalize_party_name(a.buyer_institution):
                    filtered.append(a)
        if not filtered:
            return None
        total = sum((_amt(a) for a in filtered), Decimal("0"))
        dates = sorted(a.award_date for a in filtered if a.award_date)
        cats = sorted({_category(a) for a in filtered})[:8]
        processes = []
        seen = set()
        for a in sorted(filtered, key=lambda x: x.award_date or datetime.min.replace(tzinfo=UTC), reverse=True):
            if a.process_code not in seen:
                seen.add(a.process_code)
                processes.append(a.process_code)
            if len(processes) >= 10:
                break
        return SupplierInstitutionPair(
            supplier_key=supplier_key,
            supplier_name=supplier_name,
            institution_key=institution_stable_key(
                code=filtered[0].buyer_institution_code, name=filtered[0].buyer_institution
            ),
            institution_name=filtered[0].buyer_institution,
            awards_count=len(filtered),
            process_count=len({a.process_code for a in filtered}),
            total_amount=total,
            currency=(filtered[0].currency or "DOP"),
            first_award_date=_iso(dates[0]) if dates else None,
            last_award_date=_iso(dates[-1]) if dates else None,
            categories=cats,
            recent_processes=processes,
        )

    def _build_supplier_response(
        self,
        *,
        identity: ProfileIdentity,
        awards: list[DGCPHistoricalAward],
        window_months: int | None,
        pair: SupplierInstitutionPair | None,
        limit: int,
        t0: float,
    ) -> DGCPSupplierProfileResponse:
        awards_sorted = sorted(
            awards, key=lambda a: a.award_date or datetime.min.replace(tzinfo=UTC), reverse=True
        )
        totals = self._totals_by_currency(awards_sorted)
        institutions_map: dict[str, dict[str, Any]] = {}
        total_main = totals[0].amount if totals else Decimal("0")
        main_cur = totals[0].currency if totals else "DOP"
        for a in awards_sorted:
            if (a.currency or "DOP").upper() != main_cur:
                continue
            name = a.buyer_institution
            key = institution_stable_key(code=a.buyer_institution_code, name=name)
            slot = institutions_map.setdefault(
                key,
                {
                    "name": name,
                    "count": 0,
                    "processes": set(),
                    "amount": Decimal("0"),
                    "last": None,
                },
            )
            slot["count"] += 1
            slot["processes"].add(a.process_code)
            slot["amount"] += _amt(a)
            if a.award_date and (slot["last"] is None or a.award_date > slot["last"]):
                slot["last"] = a.award_date
        inst_rows = []
        for k, v in institutions_map.items():
            share = float(v["amount"] / total_main * 100) if total_main > 0 else 0.0
            inst_rows.append(
                PartyShareRow(
                    name=v["name"],
                    stable_key=k,
                    awards_count=v["count"],
                    process_count=len(v["processes"]),
                    total_amount=v["amount"],
                    currency=main_cur,
                    last_award_date=_iso(v["last"]),
                    share_pct=round(share, 1),
                )
            )
        inst_rows.sort(key=lambda r: r.total_amount, reverse=True)

        top1 = inst_rows[0].share_pct if inst_rows else None
        top3 = sum(r.share_pct for r in inst_rows[:3]) if inst_rows else None
        if top1 is None:
            level = "INSUFICIENTE"
        elif top1 >= 50 or (top3 or 0) >= 80:
            level = "CONCENTRADO"
        elif top1 >= 30 or (top3 or 0) >= 60:
            level = "MODERADO"
        else:
            level = "DIVERSIFICADO"

        cats = self._categories(awards_sorted)
        since_12 = datetime.now(UTC) - timedelta(days=365)
        last12 = [a for a in awards_sorted if a.award_date and a.award_date >= since_12]
        last12_amt = sum((_amt(a) for a in last12 if (a.currency or "DOP").upper() == main_cur), Decimal("0"))

        last = awards_sorted[0]
        dates = [a.award_date for a in awards_sorted if a.award_date]
        dq = self._quality(awards_sorted, has_id=identity.rpe_available or identity.rnc_available)

        summary = [
            (
                f"{identity.display_name} registra {len({a.process_code for a in awards_sorted})} "
                f"procesos adjudicados conocidos en el período analizado"
                + (f", por un monto acumulado de {main_cur} {float(total_main):,.2f}." if total_main else ".")
            )
        ]
        if last.award_date:
            summary.append(
                f"Su adjudicación más reciente fue con {last.buyer_institution} el "
                f"{last.award_date.date().isoformat()} (proceso {last.process_code})."
            )
        if inst_rows:
            summary.append(
                f"El {inst_rows[0].share_pct}% del monto adjudicado conocido "
                f"(moneda {main_cur}) corresponde a {inst_rows[0].name}."
            )

        return DGCPSupplierProfileResponse(
            identity=identity,
            window_months=window_months,
            data_quality=dq,
            totals_by_currency=totals,
            awards_count=len(awards_sorted),
            process_count=len({a.process_code for a in awards_sorted}),
            institutions_count=len(institutions_map),
            categories_count=len(cats),
            last_award_date=_iso(last.award_date),
            last_award=self._to_purchase_row(last),
            last_12m_amount=last12_amt,
            last_12m_awards=len(last12),
            last_12m_currency=main_cur,
            primary_category=cats[0].category if cats else None,
            period_from=_iso(min(dates)) if dates else None,
            period_to=_iso(max(dates)) if dates else None,
            indexed_at=_iso(max((a.indexed_at for a in awards_sorted if a.indexed_at), default=None)),
            executive_summary=summary,
            awards=[self._to_purchase_row(a) for a in awards_sorted[:limit]],
            institutions=inst_rows[:30],
            categories=cats[:30],
            products=self._products(awards_sorted, limit=limit),
            timeline=self._timeline(awards_sorted),
            diversification=DiversificationBlock(
                level=level,  # type: ignore[arg-type]
                top1_share_pct=top1,
                top3_share_pct=round(top3, 1) if top3 is not None else None,
            ),
            pair=pair,
            modalities=self._modalities(awards_sorted),
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            rows_scanned=len(awards_sorted),
            cache_hit=False,
            message="Perfil construido desde adjudicaciones/contratos indexados (fuente DGCP).",
        )

    def _build_institution_response(
        self,
        *,
        identity: ProfileIdentity,
        awards: list[DGCPHistoricalAward],
        window_months: int | None,
        limit: int,
        t0: float,
    ) -> DGCPInstitutionProfileResponse:
        awards_sorted = sorted(
            awards, key=lambda a: a.award_date or datetime.min.replace(tzinfo=UTC), reverse=True
        )
        totals = self._totals_by_currency(awards_sorted)
        main_cur = totals[0].currency if totals else "DOP"
        total_main = totals[0].amount if totals else Decimal("0")

        suppliers_map: dict[str, dict[str, Any]] = {}
        for a in awards_sorted:
            if (a.currency or "DOP").upper() != main_cur:
                continue
            name = (a.supplier_name or "").strip()
            if not name:
                continue
            key = supplier_stable_key(
                rpe=a.supplier_rpe, name=name, rnc=extract_rnc_from_payload(a.raw_payload)
            )
            slot = suppliers_map.setdefault(
                key,
                {
                    "name": name,
                    "rpe": a.supplier_rpe,
                    "rnc": extract_rnc_from_payload(a.raw_payload),
                    "count": 0,
                    "processes": set(),
                    "amount": Decimal("0"),
                    "last": None,
                },
            )
            slot["count"] += 1
            slot["processes"].add(a.process_code)
            slot["amount"] += _amt(a)
            if a.award_date and (slot["last"] is None or a.award_date > slot["last"]):
                slot["last"] = a.award_date

        supplier_rows = []
        for k, v in suppliers_map.items():
            share = float(v["amount"] / total_main * 100) if total_main > 0 else 0.0
            supplier_rows.append(
                PartyShareRow(
                    name=v["name"],
                    stable_key=k,
                    rpe=v["rpe"],
                    rnc=v["rnc"],
                    awards_count=v["count"],
                    process_count=len(v["processes"]),
                    total_amount=v["amount"],
                    currency=main_cur,
                    last_award_date=_iso(v["last"]),
                    share_pct=round(share, 1),
                )
            )
        supplier_rows.sort(key=lambda r: r.total_amount, reverse=True)

        top1 = supplier_rows[0].share_pct if supplier_rows else None
        top3 = sum(r.share_pct for r in supplier_rows[:3]) if supplier_rows else None
        if top1 is None:
            conc_level = "INSUFICIENTE"
        elif top1 >= 50 or (top3 or 0) >= 80:
            conc_level = "ALTA"
        elif top1 >= 30 or (top3 or 0) >= 60:
            conc_level = "MEDIA"
        else:
            conc_level = "BAJA"

        cats = self._categories(awards_sorted)
        last = awards_sorted[0]
        dates = [a.award_date for a in awards_sorted if a.award_date]
        processes = {a.process_code for a in awards_sorted}

        # Frequency
        if dates:
            first, last_d = min(dates), max(dates)
            span_days = max(1, (last_d - first).days)
            months_span = max(1, round(span_days / 30))
            n_proc = max(len(processes), 1)
            if n_proc >= months_span:
                phrase = f"unas {round(n_proc / months_span, 1)} adjudicaciones/procesos por mes"
                approx = round(months_span / n_proc, 2)
            else:
                approx = round(months_span / n_proc, 1)
                phrase = f"1 compra cada {approx} mes(es)"
            window_label = f"últimos {window_months} meses" if window_months else "el histórico disponible"
            freq = FrequencyBlock(
                available=True,
                first_purchase_date=_iso(first),
                last_purchase_date=_iso(last_d),
                process_count=len(processes),
                purchase_count=len(awards_sorted),
                months_span=months_span,
                approx_months_between=approx,
                summary=(
                    f"Esta institución registra {len(processes)} procesos adjudicados "
                    f"en {window_label}. Promedio aproximado: {phrase}."
                ),
            )
            month_counts = Counter(d.month for d in dates)
            temporal = [
                {"month": m, "count": c, "share_pct": round(c / len(dates) * 100, 1)}
                for m, c in sorted(month_counts.items())
            ]
            if len(dates) >= 4 and month_counts.most_common(1)[0][1] >= 3:
                names = {
                    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
                    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
                }
                top_m, top_n = month_counts.most_common(1)[0]
                freq.temporal_pattern = (
                    f"{top_n} de {len(dates)} adjudicaciones concentradas en {names[top_m]} "
                    f"(fecha de adjudicación; evidencia descriptiva)."
                )
        else:
            freq = FrequencyBlock(available=False)
            temporal = []

        # Price history from unit prices
        points: list[PricePoint] = []
        units: list[float] = []
        for a in sorted(awards_sorted, key=lambda x: x.award_date or datetime.min.replace(tzinfo=UTC)):
            qty = _dec(a.quantity)
            unit = _dec(a.unit_price)
            if unit is None or qty is None or float(qty) <= 0 or float(unit) <= 0:
                continue
            units.append(float(unit))
            points.append(
                PricePoint(
                    award_date=_iso(a.award_date),
                    supplier_name=a.supplier_name,
                    quantity=qty,
                    unit_price=unit,
                    awarded_amount=_amt(a) or None,
                    process_code=a.process_code,
                    source_url=a.contract_url or a.process_url,
                )
            )
        if points:
            last_u, avg_u = units[-1], mean(units)
            price_hist = PriceHistoryBlock(
                available=True,
                currency=main_cur,
                points=points[-40:],
                last_unit_price=Decimal(str(round(last_u, 2))),
                avg_unit_price=Decimal(str(round(avg_u, 2))),
                min_unit_price=Decimal(str(round(min(units), 2))),
                max_unit_price=Decimal(str(round(max(units), 2))),
                median_unit_price=Decimal(str(round(median(units), 2))),
                variation_vs_last_pct=round((last_u - avg_u) / avg_u * 100, 1) if avg_u else None,
            )
        else:
            price_hist = PriceHistoryBlock(
                available=False,
                caveats=["Sin precios unitarios con cantidad confiable."],
            )

        dq = self._quality(awards_sorted, has_id=bool(identity.institution_code))
        summary = [
            (
                f"{identity.display_name} registra {len(processes)} adjudicaciones/procesos "
                f"en el período analizado"
                + (f", por un monto acumulado de {main_cur} {float(total_main):,.2f}." if total_main else ".")
            )
        ]
        if supplier_rows:
            summary.append(
                f"El proveedor con mayor monto adjudicado ({supplier_rows[0].name}) "
                f"representa {supplier_rows[0].share_pct}% del total conocido ({main_cur})."
            )
        if last.award_date:
            summary.append(
                f"La compra/adjudicación más reciente fue el {last.award_date.date().isoformat()} "
                f"a {last.supplier_name or 'proveedor no identificado'} "
                f"(proceso {last.process_code})."
            )

        return DGCPInstitutionProfileResponse(
            identity=identity,
            window_months=window_months,
            data_quality=dq,
            totals_by_currency=totals,
            awards_count=len(awards_sorted),
            process_count=len(processes),
            suppliers_count=len(suppliers_map),
            categories_count=len(cats),
            last_award_date=_iso(last.award_date),
            last_purchase=self._to_purchase_row(last),
            last_supplier_name=last.supplier_name,
            last_supplier_key=supplier_stable_key(
                rpe=last.supplier_rpe,
                name=last.supplier_name,
                rnc=extract_rnc_from_payload(last.raw_payload),
            )
            if last.supplier_name
            else None,
            primary_category=cats[0].category if cats else None,
            period_from=_iso(min(dates)) if dates else None,
            period_to=_iso(max(dates)) if dates else None,
            indexed_at=_iso(max((a.indexed_at for a in awards_sorted if a.indexed_at), default=None)),
            executive_summary=summary,
            awards=[self._to_purchase_row(a) for a in awards_sorted[:limit]],
            suppliers=supplier_rows[:30],
            concentration=ConcentrationBlock(
                level=conc_level,  # type: ignore[arg-type]
                top1_share_pct=top1,
                top3_share_pct=round(top3, 1) if top3 is not None else None,
                suppliers_count=len(supplier_rows),
            ),
            categories=cats[:30],
            products=self._products(awards_sorted, limit=limit),
            price_history=price_hist,
            frequency=freq,
            modalities=self._modalities(awards_sorted),
            temporal_months=temporal,
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            rows_scanned=len(awards_sorted),
            cache_hit=False,
            message="Perfil construido desde adjudicaciones/contratos indexados (fuente DGCP).",
        )

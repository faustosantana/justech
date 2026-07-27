"""Discovery Engine — automatic observational pattern discovery (Fase D / v2.2.0).

READ-ONLY over historical evidence already gathered.
Never mutates motor / ranking / Tabla 1-2 / Prompt Maestro / draws.
Never predicts. Language is observational only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.lottery.ai.analyst.discovery_store import (
    StoredFinding,
    get_discovery_store,
    new_finding_id,
    utc_now_iso,
)


FindingLevel = Literal["Muy Alto", "Alto", "Medio", "Bajo", "Insuficiente"]

FINDING_KINDS = (
    "frequency",
    "sequences",
    "repetitions",
    "confirmations",
    "year_changes",
    "lottery_changes",
    "position_changes",
    "equivalent_cases",
    "unique_cases",
)

_PREDICTIVE = re.compile(
    r"\b(esto\s+suceder[aá]|suceder[aá]|seguramente|predice|predecir|"
    r"va\s+a\s+salir|ganar[aá]|recomend|apuest)\b",
    re.I,
)


@dataclass
class DiscoveryRequest:
    kind: str = "auto_discovery"
    params: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryFinding:
    kind: str
    title: str
    level: FindingLevel
    what: str
    why: str
    evidence: dict[str, Any]
    limitations: list[str]
    tools: list[str] = field(default_factory=list)
    case_count: int = 0
    period: str | None = None
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "level": self.level,
            "what": self.what,
            "why": self.why,
            "evidence": self.evidence,
            "limitations": self.limitations,
            "tools": self.tools,
            "case_count": self.case_count,
            "period": self.period,
            "status": self.status,
        }


@dataclass
class DiscoveryResult:
    status: str = "ok"
    enabled: bool = True
    kind: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class DiscoveryEngineProtocol(Protocol):
    def can_discover(self, request: DiscoveryRequest) -> bool: ...

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult: ...


class FindingValidator:
    """Discard findings that do not meet minimum observational quality."""

    MIN_CASES = {
        "Muy Alto": 50,
        "Alto": 20,
        "Medio": 8,
        "Bajo": 3,
        "Insuficiente": 0,
    }

    @classmethod
    def classify(cls, *, case_count: int, consistency: float) -> FindingLevel:
        c = max(0, int(case_count))
        cons = max(0.0, min(1.0, float(consistency)))
        if c < 3:
            return "Insuficiente"
        if c >= 50 and cons >= 0.7:
            return "Muy Alto"
        if c >= 20 and cons >= 0.55:
            return "Alto"
        if c >= 8 and cons >= 0.4:
            return "Medio"
        if c >= 3:
            return "Bajo"
        return "Insuficiente"

    @classmethod
    def validate(cls, finding: DiscoveryFinding) -> tuple[bool, str]:
        if finding.level == "Insuficiente":
            return False, "nivel_insuficiente"
        min_cases = cls.MIN_CASES.get(finding.level, 3)
        if finding.case_count < min_cases:
            return False, "casos_bajo_minimo"
        if not finding.what or not finding.evidence:
            return False, "evidencia_incompleta"
        text = f"{finding.title} {finding.what} {finding.why}"
        if _PREDICTIVE.search(text):
            return False, "lenguaje_predictivo"
        if not finding.period and not finding.evidence.get("period"):
            # soft fail — allow with limitation, still publish if cases ok
            pass
        return True, "ok"


class DiscoveryLanguage:
    @staticmethod
    def sanitize(text: str) -> str:
        t = (text or "").strip()
        t = _PREDICTIVE.sub("se observó en la muestra", t)
        # Normalize openings
        if t and not re.match(
            r"^(se\s+observ|se\s+detect|en\s+la\s+muestra|en\s+el\s+per[ií]odo)",
            t,
            re.I,
        ):
            t = f"Se observó: {t}"
        return t


class DiscoveryEngine:
    """Observational discovery over provided historical evidence (read-only)."""

    ENABLED = True
    VERSION = "2.2.0"
    SUPPORTED_KINDS = (
        "auto_discovery",
        "findings_digest",
        "observation",
        # Reserved — not published as predictions
        "hypothesis",
        "auto_report",
    )
    ACTIVE_KINDS = ("auto_discovery", "findings_digest", "observation")

    def __init__(self, store=None):
        self.store = store or get_discovery_store()

    def can_discover(self, request: DiscoveryRequest) -> bool:
        if not self.ENABLED:
            return False
        return (request.kind or "auto_discovery") in self.ACTIVE_KINDS

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        kind = request.kind or "auto_discovery"
        if kind in {"hypothesis", "auto_report"}:
            return DiscoveryResult(
                status="rejected",
                enabled=True,
                kind=kind,
                payload={
                    "message": (
                        "El Discovery Engine no publica hipótesis ni informes predictivos. "
                        "Solo hallazgos observados en el histórico."
                    ),
                    "findings": [],
                },
            )
        if not self.can_discover(request):
            return DiscoveryResult(
                status="unsupported",
                enabled=True,
                kind=kind,
                payload={"findings": [], "supported_kinds": list(self.ACTIVE_KINDS)},
            )

        context = dict(request.context or {})
        params = dict(request.params or {})
        evidence_blob = {
            **context,
            **params,
            "evidence_package": context.get("evidence_package")
            or params.get("evidence_package")
            or {},
            "charts": context.get("charts") or params.get("charts") or [],
            "lottery_counts": context.get("lottery_counts") or params.get("lottery_counts") or {},
            "year_counts": context.get("year_counts") or params.get("year_counts") or {},
            "position_counts": context.get("position_counts")
            or params.get("position_counts")
            or {},
            "sequence_hits": context.get("sequence_hits") or params.get("sequence_hits") or [],
            "repetition_hits": context.get("repetition_hits")
            or params.get("repetition_hits")
            or [],
            "confirmation_stats": context.get("confirmation_stats")
            or params.get("confirmation_stats")
            or {},
            "equivalent_case_count": context.get("equivalent_case_count")
            or params.get("equivalent_case_count"),
            "unique_case_count": context.get("unique_case_count")
            or params.get("unique_case_count"),
            "tools_used": context.get("tools_used")
            or params.get("tools_used")
            or (context.get("evidence_package") or {}).get("tools_used")
            or [],
            "period": context.get("period")
            or params.get("period")
            or (context.get("evidence_package") or {}).get("period"),
            "investigation_id": context.get("investigation_id") or params.get("investigation_id"),
        }

        candidates = self._detect_all(evidence_blob)
        published: list[dict[str, Any]] = []
        discarded: list[dict[str, Any]] = []

        for finding in candidates:
            finding.what = DiscoveryLanguage.sanitize(finding.what)
            finding.why = DiscoveryLanguage.sanitize(finding.why)
            finding.title = DiscoveryLanguage.sanitize(finding.title)
            ok, reason = FindingValidator.validate(finding)
            if not ok:
                finding.status = "discarded"
                discarded.append({**finding.to_dict(), "discard_reason": reason})
                self._persist(finding, evidence_blob.get("investigation_id"), status="discarded")
                continue
            finding.status = "published"
            published.append(finding.to_dict())
            self._persist(finding, evidence_blob.get("investigation_id"), status="published")

        return DiscoveryResult(
            status="ok",
            enabled=True,
            kind=kind,
            payload={
                "version": self.VERSION,
                "findings": published,
                "discarded_count": len(discarded),
                "discarded": discarded[:20],
                "finding_count": len(published),
                "read_only": True,
                "predictive": False,
                "message": (
                    f"Se detectaron {len(published)} hallazgo(s) observado(s) "
                    f"en el período analizado; {len(discarded)} descartado(s) por validación."
                ),
            },
        )

    def list_history(self, *, limit: int = 50, status: str | None = "published") -> list[dict[str, Any]]:
        return [x.to_dict() for x in self.store.list(status=status, limit=limit)]

    def _persist(
        self,
        finding: DiscoveryFinding,
        investigation_id: str | None,
        *,
        status: str,
    ) -> None:
        self.store.save(
            StoredFinding(
                id=new_finding_id(),
                created_at=utc_now_iso(),
                investigation_id=str(investigation_id) if investigation_id else None,
                kind=finding.kind,
                title=finding.title,
                level=finding.level,
                status=status,
                tools=list(finding.tools or []),
                payload=finding.to_dict(),
            )
        )

    def _detect_all(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        out: list[DiscoveryFinding] = []
        out.extend(self._detect_frequency(blob))
        out.extend(self._detect_lottery_changes(blob))
        out.extend(self._detect_year_changes(blob))
        out.extend(self._detect_position_changes(blob))
        out.extend(self._detect_sequences(blob))
        out.extend(self._detect_repetitions(blob))
        out.extend(self._detect_confirmations(blob))
        out.extend(self._detect_equivalent(blob))
        out.extend(self._detect_unique(blob))
        return out

    def _base_tools(self, blob: dict[str, Any]) -> list[str]:
        tools = [str(t) for t in (blob.get("tools_used") or []) if t]
        return tools or ["historical_read_only"]

    def _detect_frequency(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        charts = blob.get("charts") or []
        pairs: list[tuple[str, int]] = []
        for item in charts:
            if isinstance(item, dict) and item.get("label") is not None and item.get("value") is not None:
                try:
                    pairs.append((str(item["label"]), int(item["value"])))
                except (TypeError, ValueError):
                    continue
        pkg = blob.get("evidence_package") or {}
        if not pairs and pkg.get("case_count") is not None:
            pairs.append((str(blob.get("subject") or "sujeto"), int(pkg["case_count"])))
        if len(pairs) < 1:
            return []
        pairs.sort(key=lambda x: x[1], reverse=True)
        top_label, top_n = pairs[0]
        total = sum(v for _, v in pairs) or top_n
        share = top_n / total if total else 0.0
        level = FindingValidator.classify(case_count=top_n, consistency=share)
        return [
            DiscoveryFinding(
                kind="frequency",
                title=f"Concentración de frecuencia en {top_label}",
                level=level,
                what=(
                    f"Se detectó que {top_label} concentra {top_n} de {total} "
                    f"registros observados ({share:.0%} de la muestra comparada)."
                ),
                why=(
                    "Apareció al ordenar los conteos históricos disponibles; "
                    "la proporción respecto al resto de la muestra indica concentración."
                ),
                evidence={
                    "top": {"label": top_label, "count": top_n},
                    "total": total,
                    "share": round(share, 4),
                    "sample": [{"label": a, "count": b} for a, b in pairs[:8]],
                    "period": blob.get("period"),
                },
                limitations=[
                    "La concentración describe la muestra analizada, no un resultado futuro.",
                    "Juegos multi-número pueden inflar conteos absolutos.",
                ],
                tools=self._base_tools(blob),
                case_count=top_n,
                period=blob.get("period"),
            )
        ]

    def _detect_lottery_changes(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        counts = blob.get("lottery_counts") or {}
        if not isinstance(counts, dict) or len(counts) < 2:
            return []
        items = []
        for k, v in counts.items():
            try:
                items.append((str(k), int(v)))
            except (TypeError, ValueError):
                continue
        if len(items) < 2:
            return []
        items.sort(key=lambda x: x[1], reverse=True)
        a, b = items[0], items[1]
        diff = a[1] - b[1]
        case_count = a[1] + b[1]
        consistency = abs(diff) / case_count if case_count else 0.0
        level = FindingValidator.classify(case_count=case_count, consistency=consistency)
        return [
            DiscoveryFinding(
                kind="lottery_changes",
                title=f"Diferencia entre loterías: {a[0]} vs {b[0]}",
                level=level,
                what=(
                    f"Se observó una diferencia de {diff} apariciones entre {a[0]} ({a[1]}) "
                    f"y {b[0]} ({b[1]}) en el período analizado."
                ),
                why="Se compararon conteos por lotería presentes en el contexto de evidencia.",
                evidence={
                    "leader": {"lottery": a[0], "count": a[1]},
                    "second": {"lottery": b[0], "count": b[1]},
                    "difference": diff,
                    "distribution": [{"lottery": x, "count": y} for x, y in items[:10]],
                    "period": blob.get("period"),
                },
                limitations=[
                    "La diferencia es descriptiva de la muestra; no implica que una lotería 'confirme' a futuro.",
                ],
                tools=self._base_tools(blob),
                case_count=case_count,
                period=blob.get("period"),
            )
        ]

    def _detect_year_changes(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        years = blob.get("year_counts") or {}
        if not isinstance(years, dict) or len(years) < 2:
            return []
        items = []
        for k, v in years.items():
            try:
                items.append((str(k), int(v)))
            except (TypeError, ValueError):
                continue
        if len(items) < 2:
            return []
        items.sort(key=lambda x: x[0])
        # compare last two years in sorted order
        y0, y1 = items[-2], items[-1]
        diff = y1[1] - y0[1]
        case_count = y0[1] + y1[1]
        consistency = abs(diff) / case_count if case_count else 0.0
        level = FindingValidator.classify(case_count=case_count, consistency=min(1.0, consistency + 0.2))
        direction = "aumento" if diff > 0 else "disminución" if diff < 0 else "estabilidad"
        return [
            DiscoveryFinding(
                kind="year_changes",
                title=f"Cambio entre años {y0[0]} y {y1[0]}",
                level=level,
                what=(
                    f"Se detectó {direction} de {abs(diff)} apariciones entre {y0[0]} ({y0[1]}) "
                    f"y {y1[0]} ({y1[1]}) en la muestra."
                ),
                why="Se compararon conteos anuales suministrados en el contexto histórico.",
                evidence={
                    "year_a": {"year": y0[0], "count": y0[1]},
                    "year_b": {"year": y1[0], "count": y1[1]},
                    "difference": diff,
                    "period": f"{y0[0]}–{y1[0]}",
                },
                limitations=[
                    "Cambios interanuales pueden deberse a cobertura de datos o calendario de sorteos.",
                ],
                tools=self._base_tools(blob),
                case_count=case_count,
                period=f"{y0[0]}–{y1[0]}",
            )
        ]

    def _detect_position_changes(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        pos = blob.get("position_counts") or {}
        if not isinstance(pos, dict) or not pos:
            return []
        items = []
        for k, v in pos.items():
            try:
                items.append((str(k), int(v)))
            except (TypeError, ValueError):
                continue
        if len(items) < 2:
            return []
        items.sort(key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in items) or 1
        top, top_n = items[0]
        share = top_n / total
        level = FindingValidator.classify(case_count=total, consistency=share)
        return [
            DiscoveryFinding(
                kind="position_changes",
                title=f"Distribución por posición: predominio de {top}",
                level=level,
                what=(
                    f"Se observó que la posición «{top}» concentra {top_n}/{total} "
                    f"apariciones ({share:.0%}) en el período analizado."
                ),
                why="Se contrastaron conteos por posición disponibles en la evidencia.",
                evidence={
                    "distribution": [{"position": a, "count": b} for a, b in items],
                    "top_position": top,
                    "share": round(share, 4),
                    "period": blob.get("period"),
                },
                limitations=["La posición predominante es un hecho de muestra, no una regla predictiva."],
                tools=self._base_tools(blob),
                case_count=total,
                period=blob.get("period"),
            )
        ]

    def _detect_sequences(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        hits = blob.get("sequence_hits") or []
        if not isinstance(hits, list) or not hits:
            return []
        n = len(hits)
        level = FindingValidator.classify(case_count=n, consistency=0.6 if n >= 5 else 0.35)
        return [
            DiscoveryFinding(
                kind="sequences",
                title="Secuencias temporales detectadas",
                level=level,
                what=f"Se detectaron {n} secuencia(s)/ventana(s) temporales en la muestra analizada.",
                why="Aparecieron al revisar anclas temporales o ventanas D+N presentes en la evidencia.",
                evidence={"sequence_count": n, "sample": hits[:10], "period": blob.get("period")},
                limitations=["Una secuencia histórica no implica repetición futura."],
                tools=self._base_tools(blob),
                case_count=n,
                period=blob.get("period"),
            )
        ]

    def _detect_repetitions(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        hits = blob.get("repetition_hits") or []
        if not isinstance(hits, list) or not hits:
            # derive from charts if duplicate-like high counts
            return []
        n = len(hits)
        level = FindingValidator.classify(case_count=n, consistency=0.55)
        return [
            DiscoveryFinding(
                kind="repetitions",
                title="Repeticiones observadas",
                level=level,
                what=f"Se observaron {n} repetición(es) en el período analizado.",
                why="Se identificaron reapariciones cercanas o conteos repetidos en la evidencia.",
                evidence={"repetition_count": n, "sample": hits[:10], "period": blob.get("period")},
                limitations=["La repetición pasada no garantiza nueva repetición."],
                tools=self._base_tools(blob),
                case_count=n,
                period=blob.get("period"),
            )
        ]

    def _detect_confirmations(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        stats = blob.get("confirmation_stats") or {}
        if not isinstance(stats, dict) or not stats:
            return []
        # expect {lottery: count} of first confirmations
        items = []
        for k, v in stats.items():
            try:
                items.append((str(k), int(v)))
            except (TypeError, ValueError):
                continue
        if not items:
            return []
        items.sort(key=lambda x: x[1], reverse=True)
        top, top_n = items[0]
        total = sum(v for _, v in items) or top_n
        level = FindingValidator.classify(case_count=total, consistency=top_n / total)
        return [
            DiscoveryFinding(
                kind="confirmations",
                title=f"Confirmaciones históricas: {top} lidera la muestra",
                level=level,
                what=(
                    f"Se observó que {top} aparece primero en {top_n} de {total} "
                    f"casos de confirmación evaluados en la muestra."
                ),
                why=(
                    f"Sobre {total} casos con hit, {top} fue el más frecuente como primera "
                    "lotería/evento; eso describe la muestra, no un pronóstico."
                ),
                evidence={
                    "leader": {"label": top, "count": top_n},
                    "total_cases": total,
                    "distribution": [{"label": a, "count": b} for a, b in items[:10]],
                    "period": blob.get("period"),
                },
                limitations=[
                    "«Confirmó primero» es un conteo histórico bajo un criterio temporal fijo.",
                    "No significa que volverá a confirmar primero.",
                ],
                tools=self._base_tools(blob),
                case_count=total,
                period=blob.get("period"),
            )
        ]

    def _detect_equivalent(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        n = blob.get("equivalent_case_count")
        try:
            n_i = int(n) if n is not None else 0
        except (TypeError, ValueError):
            n_i = 0
        if n_i <= 0:
            pkg = blob.get("evidence_package") or {}
            for f in pkg.get("findings") or []:
                m = re.search(r"(\d+)\s+casos?", str(f), re.I)
                if m and "equiv" in str(f).lower():
                    n_i = int(m.group(1))
                    break
        if n_i <= 0:
            return []
        level = FindingValidator.classify(case_count=n_i, consistency=0.65)
        return [
            DiscoveryFinding(
                kind="equivalent_cases",
                title="Casos equivalentes en el histórico",
                level=level,
                what=f"Se detectaron {n_i} caso(s) equivalentes según el criterio declarado.",
                why="El conteo proviene de condiciones históricas equivalentes/similares en la evidencia.",
                evidence={"equivalent_case_count": n_i, "period": blob.get("period")},
                limitations=["Equivalencia depende del criterio usado; no implica identidad total de contexto."],
                tools=self._base_tools(blob),
                case_count=n_i,
                period=blob.get("period"),
            )
        ]

    def _detect_unique(self, blob: dict[str, Any]) -> list[DiscoveryFinding]:
        n = blob.get("unique_case_count")
        try:
            n_i = int(n) if n is not None else 0
        except (TypeError, ValueError):
            n_i = 0
        if n_i <= 0:
            return []
        # Unique cases are interesting but often low volume → may discard as Insuficiente
        level = FindingValidator.classify(case_count=max(n_i, 3) if n_i >= 3 else n_i, consistency=0.3)
        if n_i < 3:
            level = "Insuficiente"
        return [
            DiscoveryFinding(
                kind="unique_cases",
                title="Casos únicos observados",
                level=level,
                what=f"Se observaron {n_i} caso(s) único(s) en la muestra.",
                why="Aparecieron como eventos sin réplica cercana bajo el criterio de unicidad aplicado.",
                evidence={"unique_case_count": n_i, "period": blob.get("period")},
                limitations=["Los casos únicos tienen baja base muestral y se interpretan con cautela."],
                tools=self._base_tools(blob),
                case_count=n_i,
                period=blob.get("period"),
            )
        ]


# Backward-compatible stub name (now wraps real engine disabled only if forced)
class DiscoveryEngineStub(DiscoveryEngine):
    """Legacy name — Fase D enables discovery; stub class kept for imports."""

    ENABLED = True


def get_discovery_engine() -> DiscoveryEngine:
    return DiscoveryEngine()

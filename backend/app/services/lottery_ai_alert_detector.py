"""Continuous Lottery AI alert detector — runs inside lottery-sync-worker only."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.lottery.ai.alert_thresholds import DEFAULT_ALERT_THRESHOLDS, merge_thresholds
from app.lottery.ai.metrics import ai_conversational_metrics, ai_quality_metrics
from app.lottery.ai.runtime import runtime_snapshot
from app.models.lottery import (
    LotteryAiAlert,
    LotteryAiAlertThreshold,
    LotteryAiAuditEvent,
    LotteryAiBenchmark,
    LotteryAiPromptVersion,
    LotteryAiToolSetting,
)
from app.services.lottery_sync_lock import SyncLockError, acquire_sync_lock, release_sync_lock

logger = logging.getLogger("lottery.ai.alert_detector")

ACTIVE_STATUSES = frozenset({"open", "acknowledged", "silenced", "reopened"})
LOCK_KEY = "lottery:ai:alert-detector"


@dataclass
class DetectedFinding:
    code: str
    severity: str
    message: str
    title: str | None = None
    component: str | None = None
    fingerprint: str | None = None
    metric_name: str | None = None
    metric_value: float | None = None
    threshold_value: float | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    tool_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str | None = None


@dataclass
class DetectorRunResult:
    status: str
    findings: int = 0
    upserted: int = 0
    auto_resolved: int = 0
    skipped_reason: str | None = None
    codes: list[str] = field(default_factory=list)


def _fp(code: str, tenant_id: uuid.UUID | None, extra: str = "") -> str:
    raw = f"{tenant_id or 'global'}|{code}|{extra}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _sev_from_rates(value: float, warn: float, crit: float) -> str:
    if value >= crit:
        return "critical"
    if value >= warn:
        return "high"
    return "warning"


class LotteryAiAlertDetector:
    def __init__(self, db: AsyncSession, *, tenant_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def _thresholds(self) -> dict[str, Any]:
        q = (
            select(LotteryAiAlertThreshold)
            .where(LotteryAiAlertThreshold.status == "active")
            .order_by(LotteryAiAlertThreshold.published_at.desc().nullslast())
            .limit(1)
        )
        if self.tenant_id:
            q = q.where(
                (LotteryAiAlertThreshold.tenant_id == self.tenant_id)
                | (LotteryAiAlertThreshold.tenant_id.is_(None))
            )
        row = (await self.db.execute(q)).scalar_one_or_none()
        return merge_thresholds(row.payload if row else None)

    async def _audit(self, action: str, *, entity_id: str | None = None, after: dict | None = None) -> None:
        self.db.add(
            LotteryAiAuditEvent(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                user_id=None,
                action=action,
                entity_type="alert_detector",
                entity_id=entity_id,
                after=after or {},
                result="ok",
            )
        )

    async def evaluate(self) -> list[DetectedFinding]:
        th = await self._thresholds()
        metrics = await ai_quality_metrics(self.db, days=int(th.get("window_days") or 7))
        conv = await ai_conversational_metrics(self.db, days=int(th.get("window_days") or 7))
        runtime = runtime_snapshot()
        findings: list[DetectedFinding] = []
        min_q = int(th.get("min_queries_for_rates") or 10)
        total = int(metrics.get("total_queries") or 0)

        health = (runtime.get("health") or {})
        if not health.get("synthesis_credentials_ok"):
            findings.append(
                DetectedFinding(
                    code="PROVIDER_DOWN",
                    severity="critical",
                    title="Provider / síntesis degradado",
                    message="synthesis_credentials_ok=false — sin credenciales de síntesis",
                    component="provider",
                    fingerprint=_fp("PROVIDER_DOWN", self.tenant_id),
                    metric_name="synthesis_credentials_ok",
                    metric_value=0.0,
                    threshold_value=1.0,
                    details={"recommendation": "Verificar HERMES_MODEL_API_* / Huawei ModelArts"},
                    recommendation="Restaurar credenciales de síntesis sin exponer secretos.",
                    model_name=runtime.get("model_configured"),
                )
            )

        last_ok = runtime.get("last_successful_call")
        no_ok_min = int(th.get("no_successful_call_minutes") or 60)
        if last_ok and last_ok.get("recorded_at"):
            try:
                ts = datetime.fromisoformat(str(last_ok["recorded_at"]).replace("Z", "+00:00"))
                age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
                if age_min > no_ok_min and total > 0:
                    findings.append(
                        DetectedFinding(
                            code="NO_SUCCESSFUL_CALL",
                            severity="high",
                            title="Sin llamada exitosa reciente",
                            message=f"Última llamada exitosa hace {age_min:.0f} min (umbral {no_ok_min})",
                            component="runtime",
                            fingerprint=_fp("NO_SUCCESSFUL_CALL", self.tenant_id),
                            metric_name="minutes_since_success",
                            metric_value=age_min,
                            threshold_value=float(no_ok_min),
                            recommendation="Revisar provider, timeouts y fallbacks.",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass
        elif total == 0 and not last_ok:
            # Only fire if detector has seen usage history elsewhere; soft info when cold
            pass

        ok_rate = metrics.get("resolved_rate")
        if ok_rate is not None and total >= min_q:
            err = 1.0 - float(ok_rate)
            if err >= float(th["error_rate_warning"]):
                findings.append(
                    DetectedFinding(
                        code="MODEL_DEGRADED",
                        severity=_sev_from_rates(err, th["error_rate_warning"], th["error_rate_critical"]),
                        title="Tasa de error elevada",
                        message=f"error_rate={err:.2%} (ok_rate={ok_rate})",
                        component="model",
                        fingerprint=_fp("MODEL_DEGRADED", self.tenant_id),
                        metric_name="error_rate",
                        metric_value=err,
                        threshold_value=float(th["error_rate_warning"]),
                        recommendation="Revisar modelos, timeouts y logs de síntesis.",
                        model_name=runtime.get("model_active") or runtime.get("model_configured"),
                    )
                )

        p95 = metrics.get("latency_ms_p95")
        if p95 is not None and total >= min_q:
            if float(p95) >= float(th["p95_latency_ms_warning"]):
                findings.append(
                    DetectedFinding(
                        code="MODEL_DEGRADED",
                        severity=_sev_from_rates(
                            float(p95),
                            th["p95_latency_ms_warning"],
                            th["p95_latency_ms_critical"],
                        ),
                        title="Latencia p95 elevada",
                        message=f"p95={p95}ms",
                        component="model",
                        fingerprint=_fp("MODEL_DEGRADED", self.tenant_id, "p95"),
                        metric_name="latency_ms_p95",
                        metric_value=float(p95),
                        threshold_value=float(th["p95_latency_ms_warning"]),
                        recommendation="Revisar carga del provider y timeouts.",
                    )
                )

        fb = metrics.get("fallback_rate")
        if fb is not None and total >= min_q and float(fb) >= float(th["fallback_rate_warning"]):
            findings.append(
                DetectedFinding(
                    code="FALLBACK_HIGH",
                    severity=_sev_from_rates(float(fb), th["fallback_rate_warning"], th["fallback_rate_critical"]),
                    title="Fallback elevado",
                    message=f"fallback_rate={fb}",
                    component="fallback",
                    fingerprint=_fp("FALLBACK_HIGH", self.tenant_id),
                    metric_name="fallback_rate",
                    metric_value=float(fb),
                    threshold_value=float(th["fallback_rate_warning"]),
                    recommendation="Verificar síntesis remota; fallback local no debe dominar.",
                )
            )

        tool_fail = conv.get("tool_failure_rate")
        if tool_fail is not None and float(tool_fail) >= float(th["tool_failure_rate"]):
            findings.append(
                DetectedFinding(
                    code="TOOL_FAILURE_HIGH",
                    severity="high",
                    title="Fallos de tools elevados",
                    message=f"tool_failure_rate={tool_fail}",
                    component="tools",
                    fingerprint=_fp("TOOL_FAILURE_HIGH", self.tenant_id),
                    metric_name="tool_failure_rate",
                    metric_value=float(tool_fail),
                    threshold_value=float(th["tool_failure_rate"]),
                    recommendation="Revisar settings de tools y catálogo habilitado.",
                )
            )

        ctx_loss = conv.get("context_loss_rate")
        if ctx_loss is not None and float(ctx_loss) >= float(th["context_loss_rate"]):
            findings.append(
                DetectedFinding(
                    code="CONTEXT_LOSS",
                    severity="high",
                    title="Pérdida de contexto",
                    message=f"context_loss_rate={ctx_loss}",
                    component="memory",
                    fingerprint=_fp("CONTEXT_LOSS", self.tenant_id),
                    metric_name="context_loss_rate",
                    metric_value=float(ctx_loss),
                    threshold_value=float(th["context_loss_rate"]),
                    recommendation="Revisar ConversationState restore y UAT memoria.",
                )
            )

        mem_fail = conv.get("memory_restore_rate")
        if mem_fail is not None and float(mem_fail) < 0.85 and total >= min_q:
            findings.append(
                DetectedFinding(
                    code="MEMORY_PERSISTENCE_FAILURE",
                    severity="high",
                    title="Persistencia de memoria degradada",
                    message=f"memory_restore_rate={mem_fail}",
                    component="memory",
                    fingerprint=_fp("MEMORY_PERSISTENCE_FAILURE", self.tenant_id),
                    metric_name="memory_restore_rate",
                    metric_value=float(mem_fail),
                    threshold_value=0.85,
                    recommendation="Verificar JSONB de sesión y restore_sessions.",
                )
            )

        ood = conv.get("domain_rejection_accuracy")
        if ood is not None and float(ood) < 0.9 and total >= min_q:
            findings.append(
                DetectedFinding(
                    code="OUT_OF_DOMAIN_FAILURE",
                    severity="critical",
                    title="Rechazo fuera de dominio insuficiente",
                    message=f"domain_rejection_accuracy={ood}",
                    component="safety",
                    fingerprint=_fp("OUT_OF_DOMAIN_FAILURE", self.tenant_id),
                    metric_name="domain_rejection_accuracy",
                    metric_value=float(ood),
                    threshold_value=0.9,
                    recommendation="No publicar prompt con fallas de dominio; revisar classifier.",
                )
            )

        leak = conv.get("technical_leak_rate")
        if leak is not None and float(leak) > 0:
            findings.append(
                DetectedFinding(
                    code="TECHNICAL_LEAK",
                    severity="critical",
                    title="Posible fuga técnica",
                    message=f"technical_leak_rate={leak}",
                    component="safety",
                    fingerprint=_fp("TECHNICAL_LEAK", self.tenant_id),
                    metric_name="technical_leak_rate",
                    metric_value=float(leak),
                    threshold_value=0.0,
                    recommendation="Bloquear publicación; auditar renderer y síntesis.",
                )
            )

        json_vis = conv.get("renderer_clean_rate")
        if json_vis is not None and float(json_vis) < 0.98 and total >= min_q:
            findings.append(
                DetectedFinding(
                    code="JSON_VISIBLE",
                    severity="high",
                    title="Salida técnica visible",
                    message=f"renderer_clean_rate={json_vis}",
                    component="renderer",
                    fingerprint=_fp("JSON_VISIBLE", self.tenant_id),
                    metric_name="renderer_clean_rate",
                    metric_value=float(json_vis),
                    threshold_value=0.98,
                    recommendation="Revisar renderer structured; ocultar tool dumps.",
                )
            )

        unc = conv.get("unnecessary_clarification_rate")
        if unc is not None and float(unc) >= float(th["unnecessary_clarification_rate"]):
            findings.append(
                DetectedFinding(
                    code="UNNECESSARY_CLARIFICATION_HIGH",
                    severity="warning",
                    title="Aclaraciones innecesarias altas",
                    message=f"unnecessary_clarification_rate={unc}",
                    component="understanding",
                    fingerprint=_fp("UNNECESSARY_CLARIFICATION_HIGH", self.tenant_id),
                    metric_name="unnecessary_clarification_rate",
                    metric_value=float(unc),
                    threshold_value=float(th["unnecessary_clarification_rate"]),
                    recommendation="Ajustar prompt/memoria; benchmark aclaraciones.",
                )
            )

        tokens = int(metrics.get("tokens_total") or 0)
        daily_limit = float(th["token_daily_limit"])
        # Approximate daily from window
        days = max(1, int(th.get("window_days") or 7))
        daily_est = tokens / days
        if daily_est >= daily_limit * 0.85:
            findings.append(
                DetectedFinding(
                    code="TOKEN_USAGE_HIGH",
                    severity="warning" if daily_est < daily_limit else "high",
                    title="Uso de tokens elevado",
                    message=f"est_daily_tokens={daily_est:.0f} limit={daily_limit}",
                    component="usage",
                    fingerprint=_fp("TOKEN_USAGE_HIGH", self.tenant_id),
                    metric_name="est_daily_tokens",
                    metric_value=daily_est,
                    threshold_value=daily_limit,
                    recommendation="Revisar max_tokens y profundidad de análisis.",
                )
            )

        # Benchmark
        bench = (
            await self.db.execute(
                select(LotteryAiBenchmark)
                .where(LotteryAiBenchmark.last_result.is_not(None))
                .order_by(LotteryAiBenchmark.last_run_at.desc().nullslast())
                .limit(1)
            )
        ).scalar_one_or_none()
        if bench and isinstance(bench.last_result, dict):
            res = bench.last_result
            total_c = max(1, int(res.get("total") or 0))
            passed = int(res.get("passed") or 0)
            score = passed / total_c
            p0 = int(res.get("p0") or res.get("p0_count") or 0)
            p1 = int(res.get("p1") or res.get("p1_count") or 0)
            if score < float(th["benchmark_min_score"]) or p0 > int(th["max_p0"]) or p1 > int(th["max_p1"]):
                findings.append(
                    DetectedFinding(
                        code="BENCHMARK_DEGRADED",
                        severity="critical" if p0 or p1 else "high",
                        title="Benchmark degradado",
                        message=f"score={score:.2%} p0={p0} p1={p1}",
                        component="benchmark",
                        fingerprint=_fp("BENCHMARK_DEGRADED", self.tenant_id, str(bench.id)),
                        metric_name="benchmark_score",
                        metric_value=score,
                        threshold_value=float(th["benchmark_min_score"]),
                        details={"p0": p0, "p1": p1, "benchmark_id": str(bench.id)},
                        recommendation="No publicar prompt; corregir P0/P1.",
                    )
                )

        # Prompt active
        prompt = (
            await self.db.execute(
                select(LotteryAiPromptVersion).where(LotteryAiPromptVersion.status == "active").limit(1)
            )
        ).scalar_one_or_none()
        if prompt:
            for f in findings:
                if not f.prompt_version:
                    f.prompt_version = prompt.version

        # Tools enabled sanity
        tools_total = (
            await self.db.execute(select(func.count()).select_from(LotteryAiToolSetting))
        ).scalar_one()
        tools_on = (
            await self.db.execute(
                select(func.count())
                .select_from(LotteryAiToolSetting)
                .where(LotteryAiToolSetting.enabled.is_(True))
            )
        ).scalar_one()
        if tools_total and tools_on == 0:
            findings.append(
                DetectedFinding(
                    code="TOOL_FAILURE_HIGH",
                    severity="critical",
                    title="Todas las tools deshabilitadas",
                    message="tools_enabled=0",
                    component="tools",
                    fingerprint=_fp("TOOL_FAILURE_HIGH", self.tenant_id, "none_enabled"),
                    metric_name="tools_enabled",
                    metric_value=0.0,
                    threshold_value=1.0,
                    recommendation="Rehabilitar tools tipadas en Admin Center.",
                )
            )

        return findings

    async def upsert_finding(self, finding: DetectedFinding) -> LotteryAiAlert:
        fp = finding.fingerprint or _fp(finding.code, self.tenant_id)
        now = datetime.now(timezone.utc)
        q = (
            select(LotteryAiAlert)
            .where(
                LotteryAiAlert.fingerprint == fp,
                LotteryAiAlert.status.in_(tuple(ACTIVE_STATUSES)),
            )
            .order_by(LotteryAiAlert.last_detected_at.desc().nullslast())
            .limit(1)
        )
        if self.tenant_id:
            q = q.where(
                (LotteryAiAlert.tenant_id == self.tenant_id) | (LotteryAiAlert.tenant_id.is_(None))
            )
        row = (await self.db.execute(q)).scalar_one_or_none()

        details = dict(finding.details or {})
        if finding.recommendation:
            details["recommendation"] = finding.recommendation

        if row:
            # Respect silence window
            if row.status == "silenced" and row.silenced_until and row.silenced_until > now:
                row.last_detected_at = now
                row.occurrence_count = int(row.occurrence_count or 1) + 1
                row.updated_at = now
                await self.db.flush()
                return row
            if row.status == "resolved":
                row.status = "reopened"
                row.auto_resolved = False
                row.resolved_at = None
                row.resolved_by = None
            elif row.status not in ACTIVE_STATUSES:
                row.status = "open"
            row.severity = finding.severity
            row.message = finding.message
            row.title = finding.title or row.title
            row.details = details
            row.metric_name = finding.metric_name
            row.metric_value = finding.metric_value
            row.threshold_value = finding.threshold_value
            row.component = finding.component
            row.prompt_version = finding.prompt_version
            row.model_name = finding.model_name
            row.tool_name = finding.tool_name
            row.last_detected_at = now
            row.occurrence_count = int(row.occurrence_count or 1) + 1
            row.updated_at = now
            row.acknowledged = row.status == "acknowledged"
            await self.db.flush()
            return row

        row = LotteryAiAlert(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            severity=finding.severity,
            code=finding.code,
            title=finding.title,
            message=finding.message,
            details=details,
            status="open",
            fingerprint=fp,
            component=finding.component,
            first_detected_at=now,
            last_detected_at=now,
            occurrence_count=1,
            acknowledged=False,
            prompt_version=finding.prompt_version,
            model_name=finding.model_name,
            tool_name=finding.tool_name,
            metric_name=finding.metric_name,
            metric_value=finding.metric_value,
            threshold_value=finding.threshold_value,
            auto_resolved=False,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def auto_resolve_missing(self, active_fps: set[str]) -> int:
        now = datetime.now(timezone.utc)
        q = select(LotteryAiAlert).where(LotteryAiAlert.status.in_(("open", "acknowledged", "reopened")))
        if self.tenant_id:
            q = q.where(
                (LotteryAiAlert.tenant_id == self.tenant_id) | (LotteryAiAlert.tenant_id.is_(None))
            )
        rows = (await self.db.execute(q)).scalars().all()
        n = 0
        for row in rows:
            fp = row.fingerprint or ""
            if fp and fp not in active_fps:
                row.status = "resolved"
                row.auto_resolved = True
                row.resolved_at = now
                row.resolution_note = "auto_resolved: condition cleared"
                row.updated_at = now
                row.acknowledged = True
                n += 1
        if n:
            await self.db.flush()
        return n

    async def run(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        initiated_by: str = "lottery-sync-worker",
        use_lock: bool = True,
    ) -> DetectorRunResult:
        if tenant_id is not None:
            self.tenant_id = tenant_id
        if not settings.lottery_ai_alert_detector_enabled and initiated_by == "lottery-sync-worker":
            return DetectorRunResult(status="disabled", skipped_reason="detector_disabled")

        handle = None
        if use_lock:
            ttl = max(30, min(3600, int(settings.lottery_ai_alert_lock_ttl_seconds or 240)))
            try:
                handle = await acquire_sync_lock(LOCK_KEY, ttl_seconds=ttl)
            except SyncLockError:
                logger.debug("alert detector lock busy key=%s", LOCK_KEY)
                return DetectorRunResult(status="skipped", skipped_reason="lock_busy")

        try:
            findings = await self.evaluate()
            upserted = 0
            fps: set[str] = set()
            for f in findings:
                row = await self.upsert_finding(f)
                fps.add(row.fingerprint or "")
                upserted += 1
                # Optional notify stub — lazy import avoids cycles; channels disabled by default
                try:
                    from app.lottery.ai.alert_notifications import notify_alert

                    notify_alert(
                        {
                            "id": str(row.id),
                            "code": row.code,
                            "fingerprint": row.fingerprint,
                            "severity": row.severity,
                            "title": row.title,
                            "message": row.message,
                            "status": row.status,
                        }
                    )
                except Exception:  # noqa: BLE001
                    logger.debug("alert notify stub skipped", exc_info=True)
            auto_resolved = await self.auto_resolve_missing(fps)
            await self._audit(
                "alert_detector_run",
                after={
                    "initiated_by": initiated_by,
                    "findings": len(findings),
                    "upserted": upserted,
                    "auto_resolved": auto_resolved,
                    "codes": [f.code for f in findings],
                },
            )
            await self.db.flush()
            return DetectorRunResult(
                status="ok",
                findings=len(findings),
                upserted=upserted,
                auto_resolved=auto_resolved,
                codes=[f.code for f in findings],
            )
        finally:
            if handle:
                await release_sync_lock(handle)


async def maybe_run_detector_tick(
    db: AsyncSession,
    *,
    last_run_at: datetime | None,
    now: datetime | None = None,
) -> tuple[DetectorRunResult | None, datetime | None]:
    """Cadence helper for worker loop — returns (result|None, new_last_run_at)."""
    if not settings.lottery_ai_alert_detector_enabled:
        return None, last_run_at
    now = now or datetime.now(timezone.utc)
    interval = max(60, min(3600, int(settings.lottery_ai_alert_detector_interval_seconds or 300)))
    if last_run_at and (now - last_run_at).total_seconds() < interval:
        return None, last_run_at
    detector = LotteryAiAlertDetector(db)
    result = await detector.run(initiated_by="lottery-sync-worker", use_lock=True)
    return result, now

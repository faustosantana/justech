# Lottery IA Admin Center — Closeout

**Branch:** `feature/lottery-3.0`  
**Migración:** `060_lottery_ai_alerting_closeout` (revises `059_lottery_ai_admin_center`)

## Entregado

1. Detector continuo en `app.lottery.sync.worker` (`LotteryAiAlertDetector`)
2. CRUD alertas: create/upsert/ack/resolve/silence/reopen + list/get
3. API admin + UI dashboard `#alerts` + badge menú
4. Umbrales versionados (`lottery_ai_alert_thresholds`)
5. Benchmark ≥300 (350 casos) + comparación v2 vs v3
6. Plantillas de tono completas + preview + prefs tenant/user
7. Métricas conversacionales en dashboard/detector
8. Docs runbook / benchmark / tones / gates / evaluación

## Prompt activo

**v2 permanece activo.** v3 no se activa: gate `activate_v3=false` (P0/P1 residuales en suite offline; tasas iguales en runner local que no inyecta cuerpo de prompt en `understand()`).

## Confirmaciones de no-regresión

- Un solo scheduler owner (worker standalone)
- Sync/auto-write no modificados en este closeout
- Nacional Día no tocado
- Etapa C no iniciada

## Deploy (ops)

1. Backup PostgreSQL + tag rollback
2. `alembic upgrade head` → 060
3. Bake imágenes backend/frontend
4. force-recreate backend + frontend + lottery-sync-worker + gateway
5. Verificar detector logs `ai_alert_detector` en worker
6. Verificar Centro IA `/lottery/admin/ai`

No hot-patch / no `docker cp` / no cron paralelo.

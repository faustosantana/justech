# Lottery 3.0 — Production Closeout

**Date:** 2026-07-23  
**Branch:** `feature/lottery-3.0`  
**Environment:** https://jaios.justech.do (`/opt/jaios-app`)  
**Evidence:** `/var/jaios/lottery-bake/lottery-3.0-deploy-20260723/`

## 1. Commit inicial

`cae4870` — checkpoint before Lottery 3.0 work / mail branch switch.

## 2. Commits creados

| Hash | Message |
|------|---------|
| `806ecef` | feat(lottery): add Lottery 3.0 core, sync, analytics, and AI engines |
| `6536a56` | feat(lottery): ship dashboard v3 and catalog admin ops UI |
| `0fa6460` | feat(lottery): add migration 058 for windows, sources, and metadata repair |
| `f153554` | feat(lottery): run sync worker standalone outside the API process |
| `e3de74e` | docs(lottery): document Lottery 3.0 architecture and Phase 0 fixes |
| `e8da00c` | fix(lottery): clarify Resultados Hoy expected/pending and worker status |
| `93c8836` | fix(lottery): route ops questions to sync/missing tools with natural copy |

Working tree clean after `93c8836` (closeout doc may follow as docs commit).

## 3. Commit final

`93c8836` (code/runtime). Closeout documentation may append after this report.

## 4. Backup

| Field | Value |
|-------|-------|
| Path | `/var/jaios/backups/pre_lottery_3_0_20260723.dump` |
| Gate copy | `/var/jaios/lottery-sync-gate/pre_lottery_sync.dump` (mounted RO into worker as `/tmp/pre_lottery_sync.dump`) |
| Date | 2026-07-23 |
| Size | ~36M |
| SHA256 | `6c924461d280e63f86bede3e2d37bf5f688f89968fa31d3660e5c76908b774b6` |
| Alembic at backup | pre-058 (upgrade applied after backup) |

## 5. Imágenes y tags

| Image | Tags |
|-------|------|
| backend | `latest`, `lottery-3.0-20260723` (`9c2cff71c0b7`) |
| frontend | `latest`, `lottery-3.0-20260723` (`a964b258b350`) |
| rollback backend | `pre-lottery-3.0-20260723` (= lottery-2.0-20260722) |
| rollback frontend | `pre-lottery-3.0-20260723` |
| worker | **same backend image** (`jaios-app-backend:lottery-3.0-20260723`) |

No hot-patch / no `docker cp` of application code.

## 6. Resultado migración 058

- `alembic_version` = `058_lottery_3_0_platform`
- Applied successfully after backup

## 7. Resultado metadata Real

| Field | Before | After |
|-------|--------|-------|
| Quiniela Real `last_draw_date` | 2099 (bogus) | **2026-07-21** |
| `draw_count` / actual draws | inflated vs actual | **4118 / 4118** |
| Coverage | 2015-01-02 → 2026-07-21 | unchanged bounds, metadata aligned |

Sync/auto-write for Real remain **false**.

## 8. Conteos finales

| Metric | Value |
|--------|-------|
| Lotteries | 50 |
| Draws | **91934** (was 91931 pre-write; +3 after gated write of 2026-07-22 for sources 4/5/6) |
| Numbers | **388797** |
| Auto-write | 3 (Leidsa 5, Loteka 6, Lotería Nacional 4) |
| Sync enabled | 3 |

Historical counts did not decrease.

## 9. Estado del API

- Healthy
- `LOTTERY_SYNC_WORKER_STANDALONE=true`
- `lottery_scheduler_running()=False` (no internal scheduler)

## 10. Estado del worker

- Service: `lottery-sync-worker` (profile `lottery-sync`)
- Command: `python -m app.lottery.sync.worker`
- Restart: `unless-stopped`
- Image: backend `lottery-3.0-20260723`
- Gate dump bind-mounted for `guarded_write`
- After backup mount: write run inserted 3 draws (`guarded_write_ok` / write completed)

## 11. Un solo scheduler

Confirmed: API standalone flag true + API scheduler false; only worker owns ticks.

## 12. Periodicidad (auto-write activas)

Timezone: **America/Santo_Domingo** for all three.

| Lottery | Days | Draw time | PRE | LIVE | POST | IDLE | Retries/backoff/timeout |
|---------|------|-----------|-----|------|------|------|-------------------------|
| Lotería Nacional (4) | daily (default) | **20:55** | 15m / every 5m | 10m / every 1m | window 45m / every 1m | every **60m** | null → code defaults |
| Quiniela Leidsa (5) | daily | **20:55** | same | same | same | 60m | same |
| Quiniela Loteka (6) | daily | **20:55** | same | same | same | 60m | same |

Worker loop base: **60s** (planner decides due).

## 13. Próxima ejecución exacta

- Next draw window: **2026-07-23T20:55:00-04:00**
- PRE starts ~20:40; LIVE ~20:55; POST until result validated (~45m default)
- Idle reconciliation: ~hourly while outside window
- Dashboard `next_sync_at` tracks last completed tick + loop (e.g. ~hourly idle cadence)

## 14–15. Resultados Hoy

Local today: **2026-07-23** (`America/Santo_Domingo`).

| KPI | Value | Notes |
|-----|-------|-------|
| results_today | **0** | No draws with `draw_date=today` yet (morning; last imported **2026-07-22** for sync trio) |
| expected_today | **49** | Visible dashboard lotteries |
| pending_sync_enabled | **3** | Leidsa / Loteka / Nacional |
| pending_visible | **49** | Explicitly not limited to the 3 synced without labeling |

Worker status exposed on dashboard v3.

## 16. Fuentes auditadas

- External public scrape not expanded (Etapa C not authorized).
- Inventory of 49 visible lotteries with `sync_enabled=false` retained for Stage C (`inventory.json` in evidence).
- Sync trio adapter: `elboletoganador.historial.v1`.

## 17. Analytics UAT

Leidsa, Loteka, Lotería Nacional, Quiniela Real:

- hot-cold, frequencies, quality, anomalies, coverage → **HTTP 200**
- No prediction language in payloads
- Coincidences endpoint needs correct UUID params (422 with source_id ints) — AI path used tools successfully for weekly coincidence question

## 18. IA UAT

Authenticated session (`admin@justech.do`): **14/14** HTTP PASS on ops/analytics set; quality question exercised separately.

Strengths: today/missing/next sync/syncing set/Real date/30-draw analysis/frequencies/compare/coincidences/anti-prediction disclaimer.

Residual: a few intents still fall back to generic help (cold numbers; “qué significa caliente”) without full analytic payload — risk noted, not Stage C.

## 19. Dashboard UAT

- `/lottery` page HTTP 200
- KPIs populated (not empty last sync; Real without 2099; worker status; pending breakdown)
- Visual multi-viewport browser pass not fully automated; API contract validated

## 20. Módulos existentes

- Gateway/home/frontend/lottery → 200
- Lottery admin (owner) → 200
- Non-lottery module SPA paths may 404 at exact `/bids`/`/pricing` URLs (routing); core lottery + health OK

## 21. Permisos

- Role `usuario` → **403** on lottery dashboard and admin routes
- No dedicated `lottery_client` user in production; forged JWT role alone insufficient (membership/permissions DB-backed)
- Owner retains admin access

## 22. Rollback

1. Tag images: `pre-lottery-3.0-20260723`
2. Restore dump: `/var/jaios/backups/pre_lottery_3_0_20260723.dump`
3. `docker compose --profile lottery-sync stop lottery-sync-worker` if needed
4. Point backend/frontend to pre tags; alembic downgrade only if required and validated

## 23. Riesgos pendientes

1. **Backup gate age** — `lottery_sync_backup_max_age_hours=24`; refresh `/var/jaios/lottery-sync-gate/pre_lottery_sync.dump` daily or writes block again.
2. IA soft intents (cold/hot definition) occasionally generic.
3. Etapa C not started — many lotteries have public-like schedules but sync off.
4. Tick duration ~60–100s for dry-run+write; lock key `lottery:sync:staging:api` — avoid concurrent manual ticks.
5. Coincidences API parameter shape (UUIDs) easy to misuse from scripts.

## 24. Nacional Día

**Not modified.** Alias remains ambiguous (candidates source **20** La Primera Tarde / **21** La Suerte MD). Both remain `sync=false`, `auto_write=false`.

## 25. Etapa C

**Not started.** No new lotteries enabled for sync/auto-write.

---

## Gate checklist (authorization)

| Gate | Status |
|------|--------|
| Worker running persistently | YES |
| Single scheduler | YES |
| Resultados Hoy coherent for local today | YES (0 received; expected/pending explained) |
| Real without 2099 | YES |
| IA usable with tools/params on core ops questions | YES (residual soft intents) |
| No uncommitted Lottery 3.0 code at deploy tip | YES (`93c8836`) |

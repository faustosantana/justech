# PRODUCCIÓN BETA 2.1 — Deploy controlado

**Veredicto: PRODUCCIÓN BETA 2.1 ACTIVA**

## Versión desplegada

| Campo | Valor |
|-------|-------|
| Commit certificado | `3c09c48b1ea9e2b4b452c853abdddf622854d62a` |
| Tag | `lottery-analyst-2.1.0-beta` |
| Imagen | `jaios-app-backend:lottery-analyst-2.1.0-beta` |
| Digest | `sha256:b083bc8bd52e85d4e15b475e2433074bf0fab6c710a772e8c5f51cac604f6294` |
| Origen certificado | `jaios-app-backend:lottery-analyst-2.1.0-reasoning-dev` (**mismo digest**, sin rebuild) |
| Prompt reasoning | `analyst-reasoning-v1.1` |

Checksums de archivos críticos en imagen = `git show 3c09c48` (reasoning_layer, factual_guard, reasoning_prompt, lottery_chat_service, intent_resolver).

## Backup / rollback

| Artefacto | Ruta |
|-----------|------|
| Backup completo | `/opt/jaios/backups/lottery-analyst-2.1-beta-20260729T004150Z/` |
| Compose backup | `/opt/jaios-app/docker-compose.harden.yml.bak-pre-beta21-20260729T004150Z` |
| Imagen rollback backend | `jaios-app-backend:pre-beta21-backend-20260729T004150Z` |
| Imagen rollback worker | `jaios-app-backend:pre-beta21-worker-20260729T004150Z` |
| Chat tables dump | `…/db/lottery_chat_tables.sql` (~3.0 MB) |
| Smoke | `…/smoke_results.json` |

### Rollback command (probado: script + imágenes presentes)

```bash
bash /opt/jaios/backups/lottery-analyst-2.1-beta-20260729T004150Z/ROLLBACK.sh
```

Equivalente:

```bash
cd /opt/jaios-app && \
cp /opt/jaios-app/docker-compose.harden.yml.bak-pre-beta21-20260729T004150Z /opt/jaios-app/docker-compose.harden.yml && \
docker compose -f docker-compose.harden.yml up -d --no-deps --force-recreate backend lottery-sync-worker && \
docker network connect jaios-app_jaios-net jaios-app-backend-1 || true && \
docker network connect jaios-app_jaios-net jaios-app-lottery-sync-worker-1 || true
```

## Invalidación

- Redis: best-effort delete de claves `*lottery*analyst*`, `*evidence*cache*`, `*chat*cache*`
- Contenedores recreados (estado in-memory limpio)
- Histórico de sorteos / motor / Prompt Maestro / Huawei credentials: **no tocados**

## Smoke producción (A–H)

**all_pass = true · HTTP 500 = 0**

| Case | Resultado | Notas |
|------|-----------|--------|
| A factual simple | PASS | `local_template`, `reasoning_mode=skip` (sin Huawei) |
| B explicación 35+14 | PASS | Huawei `explain_evidence`; Guard rechazó `count_mismatch:77!=120`; fallback seguro con **120** + misma fecha ≠ misma lotería |
| C follow-up loterías | PASS | `evidence_reuse`; conserva 35+14; sin loterías externas |
| D comparación 22 vs 38 | PASS | `huawei_modelarts`, `explain_evidence` |
| E alcance oficial | PASS | total **120**; sin Haiti/King/Anguila |
| F Factual Guard | PASS | rechazo `external_lottery` + predicción; good case accepted (offline en proceso) |
| G continuidad sesión | PASS | follow-up conserva 35+14 |
| H salud | PASS | backend + worker **healthy** |

### Provider / Guard

- Providers observados: `local_template`, `huawei_modelarts`, `evidence_reuse`
- Guard: `guard_passed` / `rejection_reason` / `fallback_used` visibles en `agent_trace.analyst_reasoning`
- Ejemplo B: `rejection_reason=count_mismatch:77!=120`, `fallback_used=true`, respuesta final conserva 120

## Servicios

- `jaios-app-backend-1` → `lottery-analyst-2.1.0-beta` · healthy
- `jaios-app-lottery-sync-worker-1` → `lottery-analyst-2.1.0-beta` · healthy
- postgres / redis / gateway / hermes: up

## Restricciones respetadas

Motor matemático, histórico, OFFICIAL_LOTTERY_SCOPE (7), Prompt Maestro v6, Huawei credentials, Hermes, cert200/evaluadores: sin cambios funcionales en esta promoción.

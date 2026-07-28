# HOTFIX BETA — OFFICIAL LOTTERY SCOPE

**Fecha:** 2026-07-28  
**Tag propuesto:** `lottery-analyst-official-scope-hotfix-2026.1.2`

## 7 loterías oficiales

| # | Alias de alcance | Nombre en BD |
|---|------------------|--------------|
| 1 | Gana Más | Gana Mas |
| 2 | Nacional | Loteria Nacional |
| 3 | New York 10:30 | New York 10:30 |
| 4 | New York 2:30 | New York 2:30 |
| 5 | Leidsa | Quiniela Leidsa |
| 6 | Loteka | Quiniela Loteka |
| 7 | Real | Quiniela Real |

Fuente única: `backend/app/lottery/ai/official_lottery_scope.py` → `OFFICIAL_LOTTERY_SCOPE`  
(`DEFAULT_ALL_HISTORY_LOTTERIES` es alias de esa tupla.)

## Causa raíz

`LotteryQueryService.same_day_number_coincidences` dejaba `lottery_ids=None` cuando no había loterías explícitas → el repositorio consultaba las ~50 loterías del histórico global (Haiti Bolet, King Lottery, Anguila, …).

Primera pérdida de alcance: planner `coincidences_only` no inyectaba `lotteries` si `lottery_explicit=False` → tools → query sin filtro.

## Caso 35 + 14 (prod DB)

| Universo | Coincidencias same-day |
|----------|------------------------|
| Histórico global (~50) | **1893** |
| 7 loterías oficiales | **120** |

Chat post-hotfix: «120 ocasiones»; follow-up solo Quiniela Loteka / Lotería Nacional; sin Haiti/King/Anguila.

## Suites

| Suite | Resultado |
|-------|-----------|
| OFFICIAL_LOTTERY_SCOPE (unit) | 18/18 PASS |
| Agent50 | 50/0 |
| Manual30 | 30/0 |
| Cert200 | 200/0 |

## Despliegue

- Commit: `4c983f4` (+ `7be8a9d`)
- Tag: `lottery-analyst-official-scope-hotfix-2026.1.2`
- Imagen: `jaios-app-backend:lottery-analyst-official-scope-hotfix-2026.1.2` (`sha256:ef9afa7f6464…`)
- Backup: `/opt/jaios/backups/lottery-official-scope-hotfix-20260728T210354Z/`
- Rollback image: `jaios-app-backend:pre-official-scope-hotfix-20260728T210354Z` / `lottery-analyst-2.0.0-beta`

## Veredicto

**LISTO PARA PRODUCCIÓN** (hotfix beta activo en jaios.justech.do).

## Archivos tocados

- `official_lottery_scope.py` (nuevo SSOT)
- `lottery_query_service.py`, `lottery_tools.py`, `dynamic_planner.py`
- `lottery_intent.py`, `nlp_stability.py`, `same_day_coincidence.py`
- `session_expiration.py`, `hermes_decision_engine.py`, `evidence_aggregator.py`
- `lottery_chat_service.py` (etiquetas)
- tests `test_official_lottery_scope.py` + ajuste group1

## No modificado

Motor matemático, Prompt Maestro, Huawei, Hermes arquitectura, histórico almacenado, banco cert200, semilla, evaluadores.

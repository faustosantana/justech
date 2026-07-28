# FINAL CERTIFICATION REPORT — Lottery Analyst 200

**Audit run:** `cert200-20260728T104943Z-d9f41fa3`  
**Finished (UTC):** 2026-07-28T11:39:35Z  
**Baseline:** `lottery-analyst-certified-2026.1` / `lottery-ia-ux-v2.4.5.3` / `ec27d96`  
**Mode:** read-only production chat API (same as frontend)

## Resultado final

# BLOQUEADO

| Métrica | Valor |
|---------|-------|
| PASS | 175 |
| FAIL | 25 |
| Turnos evaluados (primarios) | 200 |
| Exactitud factual media | 4.375 |
| Continuidad media | 5.0 |
| Naturalidad media | 4.462 |
| Interpretación / prudencia media | 4.378 |
| Claridad media | 4.375 |
| Manejo de ambigüedad media | 4.667 |
| Puntuación global media | 4.417 |
| Contradicciones | 0 |
| Jerga interna | 0 |
| HTTP 500 | 0 |
| Datos inventados (flag evaluador) | 1 |
| Sujetos incorrectos | 6 |
| Fails factuales (criterio script) | 25 |
| Repetibilidad equivalente | 18 / 20 |
| Concurrencia IDs únicos | true |

## Por qué BLOQUEADO

Criterio del brief: cualquier fail factual, sujeto incorrecto, dato inventado o exactitud factual &lt; 100% ⇒ **BLOQUEADO**, aunque la media global sea alta.

Este run tiene **25 FAIL** (varios `wrong_or_missing_date`, `wrong_subject`, un `guaranteed_or_fabricated` falso positivo probable, un `false_negative_same_day`).

## Freeze (FASE 1) — confirmado

| Campo | Valor |
|-------|-------|
| Baseline | `LOTTERY_ANALYST_CERTIFIED_2026_1` |
| Tag | `lottery-analyst-certified-2026.1` → `ec27d96` |
| Imagen | `jaios-app-backend:lottery-ia-ux-v2.4.5.3` |
| Digest/Id | `sha256:68f2db99229a81359706298c5792fba72aa2d7dce7e6ab23ac276b4353468ce8` |
| Alembic | `061_lottery_ia_control_center` |
| Backup | `/var/jaios/backups/LOTTERY_ANALYST_CERTIFIED_2026_1_20260728_031519.dump` |
| Backup SHA-256 | `94fcc63befcba347d843563cab54e377fc2404230e86fcf4abb4ed459d4182c3` |
| Banco | `QUESTION_BANK.json` SHA-256 `b982c83bbcefa039a6e23dcb1ce3d3442b3d89067384639694c2cd61ab65b232` |
| Semilla | `20260727` |
| Conversaciones / turnos banco | 29 / 200 |

## Evidencias

`evidence/lottery-analyst-certification-200/`

- FREEZE_MANIFEST.json, BASELINE_CERTIFICATE.md, ROLLBACK.md  
- QUESTION_BANK.json + .sha256  
- audit/raw_results.json, turn_evaluation.csv, failure_matrix.csv, …  
- SUMMARY.json (este veredicto)

## Nota de auditor

No se modificó código, prompts ni criterios durante la auditoría.  
El baseline congelado **permanece válido como punto de restauración**; la certificación conversacional extendida **no** alcanza CERTIFIED ni CONDITIONAL PASS.

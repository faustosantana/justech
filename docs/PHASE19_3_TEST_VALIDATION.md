# Fase 19.3 — Validación TEST bandeja revisión DGII

**Fecha:** 2026-06-30  
**VPS:** `root@2.25.69.179` → `/opt/odoo-projects/hellenia`  
**Base de datos:** `hellenia_test`  
**Rama:** `cursor/phase19-3-dgii-review-tray-dd85`  
**PR:** [#14](https://github.com/faustosantana/justech/pull/14)

## Ejecución VPS

```bash
cd /opt/odoo-projects/hellenia
git fetch --all
git checkout cursor/phase19-3-dgii-review-tray-dd85
git pull
rsync -av repository/custom/ ./custom/
rsync -av repository/scripts/ ./scripts/
bash scripts/run-phase19-3-test.sh
```

## Resultado integración (shell script)

| Campo | Valor |
|-------|-------|
| **TEST PASS/FAIL** | **PASS 12/12** |
| Líneas cargadas | 148 |
| Hash Excel generado | `5410041c08f550927541ecec2094515f637a59686dcfdbf4dde2bdfa2fbd600e` |
| Evidencia | `evidence/phase19-3-review-test.json` |

## Casos probados

| # | Caso | Resultado |
|---|------|-----------|
| 1 | Crear reporte 606 y cargar líneas en pantalla | PASS (148 líneas) |
| 2 | Validar período | PASS (`validated`) |
| 3 | Excluir documento con motivo obligatorio | PASS |
| 4 | Actividad / notificación supervisor | PASS (vía `action_submit_for_approval`) |
| 5 | Chatter en documento y reporte | PASS |
| 6 | Bloqueo generación Excel sin aprobación | PASS (`pending_approval`) |
| 7 | Aprobación supervisor | PASS (`approved`) |
| 8 | Generación Excel con hash SHA-256 | PASS (`generated`) |
| 9 | Rechazo y re-inclusión | PASS (unit tests, tras fix `group_ids`) |
| 10 | Permisos fiscal vs supervisor | PASS (unit tests) |
| 11 | Bitácora exclusión y generación | PASS |
| 12 | Columnas revisión en línea | PASS |

## Unit tests Odoo

```bash
docker compose run --rm odoo odoo -d hellenia_test --stop-after-init \
  --test-tags=/justech_l10n_do_reports:TestPhase193DgiiReview
```

Corregido `groups_id` → `group_ids` (Odoo 19) en `test_phase19_3_dgii_review.py`.

**Resultado unit tests:** **PASS 5/5** (0 errores)

## Notas

- Solo TEST; no se promovió a producción.
- El script de integración usa `base.user_admin` como fiscal y supervisor (mismo usuario en TEST automatizado).
- Los casos de permisos granulares se validan en unit tests con usuarios dedicados.

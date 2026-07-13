# RC6.1 — Retenciones, pagos y reportes DGII

**Entorno:** erp.justech.do / `justech_dev` / `feature/fiscal-standard-consolidation`  
**Producción:** no tocada. **Commit:** pendiente.

## Prechecks

| Check | Resultado |
|-------|-----------|
| Host / DB | vmi3364393 / justech_dev |
| Login | HTTP 200 |
| GL | 0.00 |
| Snapshot | moves=2405, payments=698, reconcile=969, wh_lines=1 |
| Backup | `/opt/odoo-dev/backups/auto-20260713_184356` |

## Causa raíz — 623 vacío

1. Única retención aplicada: pago `PBNK1/2026/00210` → factura `FC/2026/00208`, monto **239.00**, catálogo legacy **`RET5%`**.
2. `RET5%` tenía `affects_623=False` y código fuera de `GOV_CATALOG_CODES` (`RET-GOB-5` / `wh_isr_gov`).
3. Exportador 623 solo buscaba catálogo **por empresa** (`company_id = company`), ignorando globales (`company_id=False`) de RC6.
4. Stamp 623 en pago/factura no reconocía `RET5%`.
5. **No** era por falta de conciliación bancaria: elegibilidad fiscal usa retención contabilizada + fecha en período.

## Correcciones

- `RET5%` → `affects_623=True`, código DGII `07`, rate 5 (metadata catálogo/línea; sin recalcular asientos).
- `GOV_CATALOG_CODES` incluye `RET5%` (reports + payments).
- `_gov_catalog`: empresa → fallback global.
- `_payment_gov_wh_lines` / stamp: `affects_623` **o** código GOV.
- Carga período vacía: mensaje explicativo con empresa/fechas/causas.
- Chatter workflow: `Markup` + `escape` (sin HTML crudo).
- UI: retenciones en pago y factura (campos relacionales + smart button).

## Causa raíz — RPC_ERROR Centro Fiscal

```
_("%(name)s tiene %(rem)s NCF restantes (%.1f%% usado).", ..., pct=...)
TypeError: not enough arguments for format string
```

Placeholders nombrados + `%.1f` posicional mezclados.

**Fix:** `%(pct).1f%%` con `% {...}` + defensas null.

Lint: `tools/lint_odoo_translation_placeholders.py` → PASS en justech_* auditados.

## Validación julio/2026 — JUSTECH

| Reporte | all | valid | incomplete | excluded |
|---------|-----|-------|------------|----------|
| 606 | 0 | 0 | 0 | 0 |
| 607 | 30 | 30 | 0 | 0 |
| 608 | 0 | 0 | 0 | 0 |
| 609 | 0 | 0 | 0 | 0 |
| 623 | 1 | 1 | 0 | 0 |

623: `FC/2026/00208` / 239.00 / fecha retención 2026-07-13 / ref pago PBNK1/2026/00210.

Centro Fiscal: `open_for_user` OK; `run_full_scan` OK en empresas 1–4.

## Integridad

moves 2405 · payments 698 · reconcile 969 · wh_lines 1 · GL 0.00

## Rollback

1. Revert código módulos NCF/reports/payments_withholding.
2. `-u` módulos.
3. Restore backup `auto-20260713_184356` si hace falta.

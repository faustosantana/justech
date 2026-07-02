# Recuperación — Menú reportes DGII (623)

## Problema

El reporte **623 — Retenciones Estado** no aparecía en:

```
Contabilidad → Reportes → Reportes DGII → 623 Retenciones Estado
```

## Causa exacta

**Desincronización entre repositorio y VPS TEST**, no eliminación intencional en código.

El archivo en VPS (`/opt/odoo-projects/hellenia/custom/justech_l10n_do_reports/views/menu.xml`) era una versión antigua que contenía:
- `menu_justech_do_report_606_list` / `607_list` (historial)
- **Sin** `action_justech_do_report_623`
- **Sin** `menu_justech_do_report_623`
- **Sin** `action_justech_do_report_609`

El repositorio en rama 18.10+ ya incluía menú 623 desde Fase 21, pero el `rsync` a `custom/` no había actualizado ese archivo.

Causa secundaria histórica: commit `e4447af` restauró imports de `dgii_623_exporter` y `account_payment_gov` que faltaban tras refactor 18.10.

## Fix (18.12)

1. `rsync -av --delete custom/` en VPS TEST con `menu.xml` actualizado.
2. Upgrade módulo `justech_l10n_do_reports` 19.0.1.11.0.
3. Menús restaurados:

| Reporte | XML ID menú | XML ID acción |
|---------|-------------|---------------|
| 606 | `menu_justech_do_report_606` | `action_justech_do_report_606` |
| 607 | `menu_justech_do_report_607` | `action_justech_do_report_607` |
| 608 | `menu_justech_do_report_608` | `action_justech_do_report_608` |
| 609 | `menu_justech_do_report_609` | `action_justech_do_report_609` |
| **623** | `menu_justech_do_report_623` | `action_justech_do_report_623` |

## Validación TEST

| Check | Estado |
|-------|--------|
| `15_menu_623` | PASS |
| `15_action_623` | PASS |
| `13_623` reporte con retención 5% Gobierno | PASS — 1 línea, RD$500 |
| `15_menu_606/607/608` | PASS |

## Regla de compatibilidad

No se eliminaron menús 606/607/608. El historial fiscal sigue en `menu_justech_do_reports_history`.

## Evidencia

`evidence/phase18-12-regression-recovery-test.json` → tests `13_623`, `15_menu_*`, `15_action_623`

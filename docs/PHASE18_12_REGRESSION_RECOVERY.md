# Fase 18.12 — Recuperación de regresión (pagos / retenciones / 623)

**Entorno:** TEST (`hellenia_test` @ `test.hellenia.cloud`)  
**Rama:** `cursor/phase18-12-regression-recovery-dd85`  
**Módulos:** `hellenia_account` 19.0.1.0.16 · `justech_l10n_do_reports` 19.0.1.11.0  
**Certificación:** `evidence/phase18-12-regression-recovery-test.json` — **44/44 PASS**  
**Producción:** NO promovido · NO tocar `odoo-pecv`

---

## Resumen ejecutivo

| Ítem | Resultado |
|------|-----------|
| **TEST** | **PASS** |
| Abono parcial RD$5,000 / RD$11,800 | Recuperado |
| Detalle de pago (resumen + facturas + retenciones) | Recuperado |
| Reporte / menú 623 | Recuperado |
| 606 / 607 / 608 | PASS — visibles y operativos |
| Rollback requerido | **No** — fixes en rama 18.12 suficientes |

---

## Análisis de regresión (Bloque 1)

### Commits comparados

| Commit | Fase | Estado |
|--------|------|--------|
| `d7e6bcc` | 18.8 PASS | Último ciclo estable con `hellenia_applied_amount` siempre |
| `167cba2` | 18.10 reingeniería | Introduce hook nativo withholding |
| `70df199` | 18.10 fix amount bruto | **Regresión detalle pago sin retención** |
| `e4447af` | imports gov/623 | Restaura exportador 623 (imports rotos en commit previo) |
| `fd93ca4` | 18.10B | Un pago por factura — estable en shell |
| `54a2cd8` / `2fda2d4` | **18.12** | Recuperación completa |

### Dónde se rompió cada cosa

| Problema | Commit / causa exacta |
|----------|----------------------|
| **Abono parcial — detalle invisible** | `70df199` — `_hellenia_apply_withholding_to_payment_vals` retorna sin setear `hellenia_applied_amount` cuando `wh_total == 0`; vista oculta resumen si no hay applied ni wh |
| **Detalle del pago** | `70df199` — mismo early-return; sección "Detalle por factura" no existía |
| **Retenciones en pago sin wh** | `70df199` — resumen `invisible="not hellenia_applied_amount and not hellenia_withholding_total"` |
| **Reporte 623 desaparecido** | **Desincronización deploy VPS** — `custom/justech_l10n_do_reports/views/menu.xml` en TEST no tenía `action_justech_do_report_623` ni `menu_justech_do_report_623` (versión antigua con `606_list`/`607_list`). Código en repo sí lo tenía desde Fase 21 |
| **623 datos** | `e4447af` (fix previo) — `models/__init__.py` no importaba `account_payment_gov` ni `dgii_623_exporter` |

### Archivos con diferencias relevantes

- `hellenia_account/wizards/payment_register_withholding.py` — applied_amount + application lines
- `hellenia_account/wizards/payment_partner_wizard.py` — fuerza `register.amount` al parcial
- `hellenia_account/models/payment_application_line.py` — **nuevo** detalle por factura
- `hellenia_account/views/account_payment_withholding_views.xml` — resumen + detalle + retenciones
- `justech_l10n_do_reports/views/menu.xml` — menú 623/609 restaurado en VPS

---

## Correcciones aplicadas (18.12)

1. `hellenia_applied_amount` persistido **siempre** (con o sin retención).
2. `register.amount` forzado al `amount_to_pay` del wizard si Odoo lo recalcula al residual.
3. Modelo persistente `hellenia.payment.application.line` con sync post-reconciliación.
4. Vista de pago: Resumen aplicación · Detalle por factura · Retenciones aplicadas.
5. Deploy + upgrade `menu.xml` con 623 visible en Contabilidad → Reportes → Reportes DGII.

---

## Evidencia

```bash
bash scripts/run-odoo-shell-env.sh test phase18-12-regression-recovery-test.py PHASE1812 evidence/phase18-12-regression-recovery-test.json
```

**Resultado:** 44/44 PASS · `rollback_required: false`

---

## Criterio PASS (Bloque 8)

Todos los criterios obligatorios cumplidos en certificación automática TEST.

## Continuar vs rollback

**Se puede continuar** sobre rama `cursor/phase18-12-regression-recovery-dd85`.  
No se requiere rollback a `d7e6bcc` — las correcciones 18.12 restauran funcionalidad sin revertir el hook nativo de retenciones 18.10.

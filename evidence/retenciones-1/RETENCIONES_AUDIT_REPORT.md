# RETENCIONES-1 — Auditoría Read-Only

**Fecha:** 2026-07-08
**Ambiente auditado:** TEST (`hellenia_test`) + código fuente `custom/`
**Alcance:** localizar la funcionalidad de pagos y retenciones fiscales dominicanas.
**Modificaciones realizadas en esta fase:** ninguna (solo lectura / cálculo en memoria).

---

## 1. ¿En qué módulo está hoy?

El **motor de retenciones vive en `hellenia_account`** (v19.0.1.0.27).
El **consumo fiscal para DGII 623** vive en `justech_l10n_do_reports` (v19.0.1.13.0),
que **depende de `hellenia_account`** (confirmado en TEST: `reports.dependencies = ['hellenia_account','justech_l10n_do_ncf']`).
La **capa de presentación (UX)** en factura vive parcialmente en `hellenia_ux`.

| Módulo | Rol respecto a retenciones |
|---|---|
| `hellenia_account` | **Motor**: catálogo, líneas persistentes, cálculo, asiento, conciliación, wizard de pago |
| `justech_l10n_do_reports` | **Consumidor 623**: sella campos de retención gubernamental y exporta el 623 |
| `hellenia_ux` | Vista de retenciones en el formulario de factura |
| `hellenia_reports` | Recibo de pago (`report_payment_receipt.xml`) |
| `justech_modules` | Catálogo comercial / licencias (NO tenía entrada propia de retenciones) |

---

## 2. ¿Qué modelos toca?

**Modelos nuevos (propios) — `hellenia_account`:**
- `hellenia.withholding.catalog` — catálogo configurable de retenciones RD (ISR/ITBIS/otros).
- `hellenia.payment.withholding.line` — retención persistente aplicada en un pago (ciclo contable/fiscal).
- `hellenia.payment.application.line` — detalle de aplicación pago ↔ factura (bruto/retenido/neto).

**Modelos extendidos (`_inherit`):**
- `account.payment` (en `hellenia_account`): campos `hellenia_withholding_line_ids`, `hellenia_withholding_total`, `hellenia_net_transfer`, `hellenia_applied_amount`, `hellenia_application_line_ids`, medios de pago (`hellenia_check_*`, `hellenia_card_*`), + hook `_prepare_move_withholding_lines`, `_hellenia_link_partial_reconciles`.
- `account.payment.register` (en `hellenia_account`): `hellenia_withholding_catalog_ids`, `hellenia_withholding_line_ids`, flujo `_create_payment_vals_from_wizard/_batch`, `_init_payments`, `_reconcile_payments`.
- `account.move` (en `hellenia_account`): `hellenia_withholding_line_ids`, `hellenia_withholding_total`.
- `account.payment` + `account.move` (en `justech_l10n_do_reports`): campos `justech_do_gov_withholding_*` / `justech_do_gov_retention_*` (623) y `_justech_stamp_gov_from_withholding`.

**Wizards transitorios:**
- `hellenia.payment.partner.wizard` + `hellenia.payment.partner.wizard.line`.
- `hellenia.payment.withholding.wizard.line`.

Confirmado en TEST: los 3 modelos propios existen; los campos en `account.payment`/`account.move` están presentes.

---

## 3. ¿Qué vistas modifica?

Todas en `hellenia_account/views/` (+ `hellenia_ux`):
- `hellenia_withholding_catalog_views.xml` — tree/form/search/action/menu del catálogo
  (`action_hellenia_withholding_catalog`, `menu_hellenia_withholding_catalog`).
- `account_payment_register_views.xml` — `view_account_payment_register_form_hellenia`.
- `account_payment_withholding_views.xml` — `view_account_payment_form_hellenia_withholding`.
- `account_move_withholding_views.xml` — `view_account_move_form_hellenia_withholding`.
- `payment_partner_wizard_views.xml` — wizard de pago por socio + vistas de lista de pagos.
- `hellenia_ux/views/account_move_withholding_views.xml` — bloque de retenciones en factura.

---

## 4. ¿Qué reportes afecta?

- **DGII 623** (`justech_l10n_do_reports/models/dgii_623_exporter.py`): lee
  `move.justech_do_gov_withholding_amount` y, como respaldo,
  `payment.hellenia_withholding_line_ids` filtrando `catalog_id.code in ('RET-GOB-5','wh_isr_gov')`.
- **DGII 606 / 607**: el catálogo marca `affects_606` / `affects_607` y `dgii_withholding_code`
  por cada retención (columnas de retención en compras/ventas).
- **Recibo/Comprobante de pago**: `hellenia_account/reports/payment_receipt_withholding_templates.xml`
  y `hellenia_reports/report/report_payment_receipt.xml`.

---

## 5. ¿Qué campos agrega?

- **Catálogo** (`hellenia.withholding.catalog`): `code`, `withholding_type` (isr/itbis/other),
  `rate`, `base_type` (untaxed/itbis/total/applied_amount), `tax_id` (impuesto l10n_do amount<0),
  `account_id`, `partner_scope`, `move_scope`, `affects_606/607/623`, `dgii_withholding_code`.
- **Pago** (`account.payment`): `hellenia_withholding_line_ids`, `hellenia_withholding_total`,
  `hellenia_net_transfer`, `hellenia_applied_amount`, `hellenia_application_line_ids`,
  `justech_do_gov_withholding_amount` (623).
- **Factura** (`account.move`): `hellenia_withholding_line_ids`, `hellenia_withholding_total`,
  `justech_do_gov_withholding_amount`, `justech_do_gov_retention_date/ref/ref_type/bank_id`.

---

## 6. ¿Qué lógica fiscal ejecuta?

- **Cálculo de retención** (`catalog.compute_withholding_amount`): base configurada × tasa nominal,
  con escalado proporcional al monto aplicado en pagos parciales.
- **Asiento contable**: `_prepare_move_withholding_lines` genera la línea GL de retención en el
  asiento del pago (hook nativo Odoo 19), con signo según `payment_type`.
- **Conciliación**: `_hellenia_link_partial_reconciles` vincula la línea de retención con la
  conciliación parcial factura ↔ pago.
- **Sellado 623**: `_justech_stamp_gov_from_withholding` (en reports) copia la retención 5% Gobierno
  a los campos 623 del pago y de las facturas conciliadas.
- **Sincronización del catálogo** con impuestos l10n_do: `sync_catalog_from_taxes` (post_init_hook).

**Validación funcional en TEST (cálculo, sin escribir datos)** contra factura de proveedor
`FACTU/2026/07/0012` (base 222 000, ITBIS 39 960):

| Código | Tipo | Base | Tasa | Total | Aplicado 50% |
|---|---|---|---|---|---|
| RET-HON-10 | ISR | base imponible | 10% | 22 200 | 11 100 |
| RET-ITBIS-30 | ITBIS | ITBIS | 30% | 11 988 | 5 994 |
| RET-ITBIS-100 | ITBIS | ITBIS | 100% | 39 960 | 19 980 |
| RET-GOB-5 | ISR | base imponible | 5% | 11 100 | 5 550 |
| RET-ISR-2 | ISR | base imponible | 2% | 4 440 | 2 220 |

El escalado proporcional en pagos parciales funciona correctamente.

---

## 7. ¿Qué relación tiene con DGII?

- Cada retención del catálogo declara `affects_606/607/623` y `dgii_withholding_code`
  (p. ej. 02, 03, 04, 07) para las columnas de retención de los formatos DGII.
- El **623** (retención 5% del Estado) se alimenta desde los pagos con `RET-GOB-5`.
- Los impuestos de retención son los **oficiales l10n_do** (no se inventan tasas):
  `-30% ITBIS (N02-05)`, `-75% ITBIS (N08-10)`, `-100% ITBIS (N07-09)`, `-2%/-10% ISR`, `-5% ISR Gov.`, etc.

## 8. ¿Qué relación tiene con pagos?

- Toda la lógica se dispara desde `account.payment.register` (Registrar pago) y persiste en `account.payment`.
- Calcula bruto aplicado, total retenido y neto transferido; el banco recibe el **neto**.

## 9. ¿Qué relación tiene con facturas?

- La retención se ancla a la(s) factura(s) del pago (`move_id`, `invoice_name`, `ncf`).
- Se refleja en `account.move` (líneas + total) y en el detalle de aplicación por factura.

## 10. ¿Qué relación tiene con contabilidad?

- Genera línea contable de retención en el asiento del pago hacia la `account_id` del catálogo.
- Se vincula a la conciliación parcial factura↔pago (`account.partial.reconcile`).
- Confirmado E2E en TEST (transacción con rollback): ITBIS 18 000 → RET-ITBIS-30 = 5 400 →
  neto 112 600, 1 línea GL de retención (5 400), factura conciliada (residual 0, `paid`).

---

## Observaciones de higiene de datos (no bloqueantes)

- El catálogo tiene **1 032 registros** en la compañía (mayoría duplicados `RET-NONE` archivados
  por ejecuciones repetidas del `post_init_hook`). No afecta el runtime pero conviene depurar.
- Actualmente **no hay retenciones activas** en la compañía de TEST (todas archivadas); el motor
  funciona al activarlas / seedearlas (`sync_catalog_from_taxes`).

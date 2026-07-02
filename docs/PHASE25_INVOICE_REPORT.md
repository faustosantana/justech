# Fase 25 — Reporte paralelo factura fiscal Hellenia

**Versión módulo:** `justech_report_design` 19.0.3.0.0  
**Entorno:** solo `hellenia_test`  
**Estado PROD:** sin cambios

---

## Objetivo

Crear reporte paralelo **Justech PDF — Factura** con diseño aprobado (imagen referencia Fase 25), sin reemplazar `account.report_invoice` ni afectar DGII, contabilidad ni cotización.

---

## Implementación

| Elemento | Valor |
|----------|-------|
| Template | `justech_report_design.report_justech_invoice_document` |
| Cuerpo QWeb | `justech_report_design.justech_invoice_body` |
| Acción | `justech_report_design.action_report_justech_invoice` |
| SCSS | `hellenia_quotation.scss` + `hellenia_invoice.scss` |
| Modelo helpers | `justech_report_design/models/account_move.py` |

### Diseño

1. **Header:** logo izquierda + datos empresa derecha (sin duplicar empresa).
2. **Banda verde:** FACTURA | No. factura, NCF, tipo comprobante.
3. **5 columnas:** cliente, condiciones pago, vendedor, fecha emisión, fecha vencimiento.
4. **Tabla:** #, descripción, cant., P. unit., descuento (si aplica), ITBIS, subtotal.
5. **Inferior:** observaciones izquierda + totales derecha.
6. **Firmas:** entregado / recibido + fecha.
7. **Footer:** barra verde teléfono | correo | web | página X de Y.

### Campos reales

Ver auditoría completa: `docs/PHASE25_INVOICE_FISCAL_FIELD_AUDIT.md`

---

## Instalación TEST

```bash
# En VPS hellenia_test
docker compose exec odoo odoo -d hellenia_test -u justech_report_design --stop-after-init
```

O ejecutar script completo:

```bash
bash scripts/run-phase25-test.sh
```

---

## Uso

1. Abrir factura de cliente (`account.move` out_invoice).
2. **Imprimir → Justech PDF — Factura**.
3. La factura estándar Odoo sigue en **Imprimir → Factura**.

---

## Validación

Script: `scripts/phase25-invoice-report-test.py`  
Evidencia: `evidence/phase25-invoice-report/`

| Check | Descripción |
|-------|-------------|
| PDF genera sin error QWeb | PASS/FAIL |
| Diseño jt-inv-* presente | PASS/FAIL |
| NCF real en PDF | PASS/FAIL |
| Totales coinciden Odoo | PASS/FAIL |
| Factura estándar intacta | PASS/FAIL |
| Cotización oficial intacta | PASS/FAIL |

---

## Rollback

```bash
# Desvincular menú (opcional) — desinstalar módulo NO afecta factura estándar
# Si se desea ocultar sin desinstalar:
docker compose exec odoo odoo shell -d hellenia_test <<'PY'
action = env.ref('justech_report_design.action_report_justech_invoice')
action.write({'binding_model_id': False})
env.cr.commit()
PY
```

La factura estándar `account.account_invoices` no se modifica en esta fase.

---

## Restricciones respetadas

- No PROD
- No reemplazar factura estándar
- No tocar DGII
- No tocar contabilidad (solo lectura)
- No tocar cotizaciones
- No campos inventados
- No xpath frágiles sobre `account.report_invoice_document`

---

## Referencias

- `docs/PHASE25_INVOICE_FISCAL_FIELD_AUDIT.md`
- `evidence/phase25-invoice-report/README.md`
- `custom/justech_report_design/report/invoice/justech_invoice_template.xml`

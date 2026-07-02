# Fase 25B — Corrección diseño factura Justech

**Estado:** `PENDING_USER_VISUAL_APPROVAL`  
**Entorno:** `hellenia_test` únicamente (PROD no tocado)  
**Módulo:** `justech_report_design` v`19.0.3.2.1`  
**Rama:** `cursor/phase25b-invoice-design-dd85`

---

## Cambios aplicados (solo diseño visual)

| Área | Corrección |
|------|------------|
| Banda verde | No. factura, NCF, tipo comprobante y moneda siempre visibles (campos reales Odoo) |
| Meta 5 columnas | Fondo blanco puro; sin `jt-hq-vdiv`; tabla con `border-collapse` e inline `background:#fff` |
| Espaciado | Más padding en banda, meta, tabla y totales |
| Tipografía banda | `letter-spacing: 1px` (evita «F A C T U R A» en wkhtmltopdf) |
| Totales | Mismo bloque `jt-hq-totals` que cotización |

**No modificado:** DGII, contabilidad, compras, inventario, cotizaciones, reporte estándar `account.report_invoice`.

---

## Campos fiscales — fuente Odoo

| Campo PDF | Helper / campo Odoo | Borrador | Publicada |
|-----------|---------------------|----------|-----------|
| No. FACTURA | `account.move.name` | `Borrador` | `INV/2026/…` |
| NCF | `justech_do_ncf` | `—` | `B0100020036` (ej.) |
| Tipo comprobante | `justech_do_document_type_id.name` o `_justech_resolve_document_type()` | Factura de Crédito Fiscal | Igual |
| Moneda | `currency_id.name` | DOP | DOP |
| Fecha emisión | `invoice_date` | dd/mm/yyyy | dd/mm/yyyy |
| Fecha vencimiento | `invoice_date_due` | dd/mm/yyyy o `—` | dd/mm/yyyy |

No se inventan valores. Si el campo no existe en borrador (p. ej. NCF), se muestra `—`.

---

## Evidencia regenerada (TEST)

```
evidence/phase25b-invoice-design/
├── 01_invoice_1_line.pdf / .png
├── 02_invoice_5_lines.pdf / .png
├── 03_invoice_with_discount.pdf / .png
├── 04_invoice_fiscal_b01.pdf / .png
├── validation.json
└── shell.log
```

Regenerar en VPS:

```bash
bash scripts/run-phase25b-invoice-design-test.sh
```

---

## Rollback

1. En TEST: restaurar `justech_report_design` a v`19.0.3.0.0` y `-u justech_report_design`.
2. No afecta factura estándar ni cotizaciones.

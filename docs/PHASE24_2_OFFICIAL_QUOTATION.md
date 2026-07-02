# Fase 24.2 — Oficialización cotización Hellenia

**Versión módulo:** `justech_report_design` **19.0.2.0.0**  
**Estado:** Implementado — pendiente despliegue TEST/PROD y validación operativa  
**Alcance:** Solo cotizaciones (`sale.order`)

---

## 1. Términos y condiciones por defecto

| Requisito | Implementación |
|-----------|----------------|
| Sin texto quemado en XML | Eliminado `_JT_DEFAULT_TERMS` y `get_jt_quotation_terms_display()` |
| Empresa con texto por defecto | Campo `res.company.hellenia_quotation_terms` (`hellenia_reports`) |
| Copia al crear cotización | `default_get` + `create` en `sale.order` → `note` |
| Usuario edita libremente | Campo `note` en formulario (etiqueta: Condiciones PDF Cotización) |
| PDF imprime `doc.note` | `t-field="doc.note"` en bloque CONDICIONES |
| Sin duplicados | Si `note` vacío → bloque CONDICIONES oculto (sin fallback en PDF) |

**Archivos:** `models/sale_order.py`, `report/quotation/hellenia_quotation_template.xml`

---

## 2. Reporte oficial

| Acción | XML ID | Comportamiento |
|--------|--------|----------------|
| **Principal** | `sale.action_report_saleorder` | Apunta a `justech_report_design.report_hellenia_quotation_document` |
| **Respaldo** | `justech_report_design.action_report_saleorder_backup` | `sale.report_saleorder` (hellenia_reports + estándar) |
| Paralelo 24.1 | `justech_report_design.action_report_hellenia_quotation` | Sin binding (fuera del menú Imprimir) |

- No xpath sobre `sale.report_saleorder` desde `justech_report_design`
- `hellenia_reports` permanece instalado
- `sale.report_saleorder` no se elimina

**Archivo:** `data/report_official_data.xml`

---

## 3. Validación

Script: `scripts/phase24-2-official-quotation-test.py` (solo `hellenia_test`)

| Caso | Check |
|------|-------|
| Nueva cotización → condiciones automáticas | `new_order_has_note`, `new_order_note_from_company` |
| Usuario modifica → PDF cambia | `modified_note_in_pdf` |
| Usuario elimina → PDF sin condiciones | `empty_note_hides_cond` |
| Con / sin descuento | `discount_col`, `no_discount_col` |
| Pedido confirmado | `confirmed_order_pdf` |
| Portal | `portal_pdf` |
| Factura / compra sin cambio | `invoice_unchanged`, `purchase_unchanged` |

---

## 4. Rollback (< 2 min)

Ver: `docs/PHASE24_2_OFFICIAL_QUOTATION_ROLLBACK.md`

---

## 5. Fuera de alcance (sin cambios)

Facturas, compras, inventario, pagos, DGII.

---

## Despliegue

```bash
# TEST
docker run ... odoo -d hellenia_test -u justech_report_design --stop-after-init --no-http ...

# Validación
docker exec ... odoo shell -d hellenia_test < scripts/phase24-2-official-quotation-test.py
```

**PROD:** Requiere autorización explícita tras PASS en TEST.

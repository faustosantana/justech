# Fase 24.2 — Roadmap diseño QWeb+SCSS (planificación)

**Estado:** ⏸️ **PENDIENTE — NO EJECUTAR**  
**Bloqueado por:** Aprobación visual explícita de cotización Fase 24.1  
**Entorno objetivo inicial:** TEST (`hellenia_test`)  
**PROD:** No promover hasta checklist dedicado por documento

---

## Contexto

Fase 24.1 estableció el patrón validado para cotización:

| Elemento | Implementación 24.1 |
|----------|---------------------|
| Módulo | `custom/justech_report_design` (limpio, sin heredar `hellenia_reports`) |
| Template propio | `report_hellenia_quotation_document` |
| Estilos PDF | SCSS en `web.report_assets_common` |
| Layout | `web.html_container` — sin `web.external_layout` |
| Reporte | Paralelo — **no reemplaza** estándar Odoo |
| Paperformat | Dedicado por documento |

Fase 24.2 replica ese enfoque a otros documentos corporativos, **uno por uno**, con paquete de revisión y validación TEST antes de cualquier promoción.

---

## Alcance planificado

### 24.2a — Factura

| Ítem | Detalle |
|------|---------|
| Modelo | `account.move` (`move_type` in/out, NC, débito según aplique) |
| Reporte estándar | `account.report_invoice` / `account.report_invoice_document` |
| Acción paralela propuesta | `justech_report_design.action_report_hellenia_invoice` |
| Template propuesto | `justech_report_design.report_hellenia_invoice_document` |
| SCSS propuesto | `static/src/scss/hellenia_invoice.scss` |
| Paperformat | Dedicado (Letter, márgenes a definir con diseño) |

**Consideraciones:**

- Existe herencia en `hellenia_reports/report/report_invoice.xml` (títulos fiscales, NCF, clases `hellenia-invoice-doc`).
- Existe herencia NCF en `justech_l10n_do_ncf`.
- **No mezclar** lógica fiscal DGII/NCF en el módulo de diseño; consumir campos ya expuestos por localización.
- Validar: factura cliente, NC, borrador, cancelada (según política visual).
- **No tocar** flujos contables, retenciones ni reportes 606/607/623.

---

### 24.2b — Orden de compra (PO)

| Ítem | Detalle |
|------|---------|
| Modelo | `purchase.order` (`state = purchase`) |
| Reporte estándar | `purchase.report_purchaseorder` / `purchase.report_purchaseorder_document` |
| Acción paralela propuesta | `justech_report_design.action_report_hellenia_purchase_order` |
| Template propuesto | `justech_report_design.report_hellenia_purchase_order_document` |
| SCSS propuesto | `static/src/scss/hellenia_purchase_order.scss` |

**Consideraciones:**

- Herencia actual en `hellenia_reports/report/report_purchase.xml` (`report_purchaseorder_document_hellenia`).
- Campos: proveedor, referencia, comprador, líneas, totales, términos.
- Estados: confirmada vs cancelada.

---

### 24.2c — RFQ (solicitud de cotización compra)

| Ítem | Detalle |
|------|---------|
| Modelo | `purchase.order` (`state in draft, sent, to approve`) |
| Reporte estándar | `purchase.report_purchasequotation` / `purchase.report_purchasequotation_document` |
| Acción paralela propuesta | `justech_report_design.action_report_hellenia_rfq` |
| Template propuesto | `justech_report_design.report_hellenia_rfq_document` |
| SCSS propuesto | Compartir base con PO o archivo `hellenia_rfq.scss` si el diseño difiere |

**Consideraciones:**

- Mismo modelo que PO; título y banda deben reflejar “Solicitud de cotización” vs “Orden de compra”.
- Herencia actual: `report_purchasequotation_document_hellenia` en `hellenia_reports`.
- Puede reutilizar ~70% del layout PO si el HTML aprobado lo permite.

---

### 24.2d — Albarán (entrega / recepción)

| Ítem | Detalle |
|------|---------|
| Modelo | `stock.picking` |
| Reporte estándar | `stock.report_delivery` / `stock.report_delivery_document` |
| Acción paralela propuesta | `justech_report_design.action_report_hellenia_delivery` |
| Template propuesto | `justech_report_design.report_hellenia_delivery_document` |
| SCSS propuesto | `static/src/scss/hellenia_delivery.scss` |

**Consideraciones:**

- Herencia actual en `hellenia_reports/report/report_stock.xml` (entrada/salida/interno).
- Etiquetas dinámicas: recepción, guía de entrega, movimiento interno.
- También existe `stock.report_picking` — evaluar si el diseño aplica a ambos o solo delivery.
- **No tocar** lógica de inventario ni validaciones de stock.

---

### 24.2e — Portal PDF (evaluación posterior)

| Ítem | Detalle |
|------|---------|
| Estado | Diferido — después de aprobar PDFs backend |
| Problema conocido (24.1) | URL `/report/pdf/{report_name}/{id}?access_token=...` devuelve HTML login para reporte paralelo |
| Opciones a evaluar | Registrar ruta portal, heredar controlador `report`, binding portal en `ir.actions.report`, o exponer solo reporte estándar en portal y diseño en backend |

**Criterio:** No bloquea 24.2a–d si el negocio prioriza impresión interna.

---

## Patrón de entrega por sub-fase

Cada sub-fase (24.2a, 24.2b, …) seguirá el mismo ciclo que 24.1:

1. HTML/CSS aprobado por diseño (Fausto) — copia exacta, sin interpretación
2. QWeb + SCSS en `justech_report_design` (subcarpeta `report/{tipo}/`)
3. Paperformat dedicado
4. Acción de reporte **paralela** (no reemplazar estándar)
5. Script de validación TEST + `validation.json`
6. Paquete descargable en `packages/phase24-2{x}-.../`
7. Revisión visual → TEST PASS → esperar OK antes de siguiente documento

---

## Orden sugerido de ejecución

```
24.1 cotización     ✅ TEST PASS — pendiente aprobación visual
        ↓
24.2a factura       (mayor complejidad fiscal — requiere diseño + campos NCF)
        ↓
24.2b PO            (compras confirmadas)
        ↓
24.2c RFQ           (reutilizar base PO si aplica)
        ↓
24.2d albarán       (logística)
        ↓
24.2e portal PDF    (evaluación transversal)
```

El orden puede ajustarse según prioridad de negocio tras aprobar cotización.

---

## Qué NO hacer en 24.2 (hasta nueva instrucción)

- [ ] Promover a PROD cualquier sub-fase
- [ ] Reemplazar reportes estándar Odoo (`account.report_invoice_document`, etc.)
- [ ] Añadir más herencias en `hellenia_reports` sin entender impacto
- [ ] Tocar DGII, retenciones, contabilidad, pagos
- [ ] Pegar HTML en vistas desde la UI
- [ ] Usar assets web backend/frontend para PDF
- [ ] Ejecutar código antes de aprobación visual de cotización 24.1

---

## Dependencias del módulo (planificado)

```python
# __manifest__.py — evolución prevista
"depends": [
    "sale",           # 24.1 ✅
    "account",        # 24.2a
    "purchase",       # 24.2b, 24.2c
    "stock",          # 24.2d
    # "portal",       # 24.2e — si aplica
]
```

Dependencias de localización (`justech_l10n_do_ncf`) solo como **lectura de campos** en templates, no como herencia cruzada de diseño.

---

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| Duplicar lógica fiscal en QWeb de diseño | Solo `t-field` / helpers existentes; diseño separado de fiscal |
| Conflicto con `hellenia_reports` | Reportes paralelos; no inherit del estándar |
| Factura con múltiples tipos (FC, NC, débito) | Sub-templates o condicionales QWeb por `move_type` |
| RFQ vs PO mismo modelo | Dos acciones reporte, templates distintos |
| Albarán entrada vs salida | Bandas/etiquetas condicionales (como hoy en hellenia_reports) |

---

## Entregables esperados (por sub-fase)

- [ ] QWeb completo en `justech_report_design/report/`
- [ ] SCSS en `static/src/scss/`
- [ ] `data/paperformat_data.xml` (registro adicional)
- [ ] `data/report_action_data.xml` (acción paralela)
- [ ] Script `scripts/phase24-2{x}-...-test.py`
- [ ] `evidence/phase24-2{x}-.../validation.json` con `pass: true`
- [ ] `packages/phase24-2{x}-...-review.zip`
- [ ] Actualización de `PROD_PROMOTION_CHECKLIST.md` (sin ejecutar)

---

## Estado actual

| Fase | Estado |
|------|--------|
| 24.1 Cotización | ✅ TEST PASS — paquete en `packages/phase24-1-hellenia-quotation-review.zip` |
| 24.2a Factura | ⏸️ Planificado |
| 24.2b PO | ⏸️ Planificado |
| 24.2c RFQ | ⏸️ Planificado |
| 24.2d Albarán | ⏸️ Planificado |
| 24.2e Portal PDF | ⏸️ Evaluación posterior |
| PROD | ⛔ Bloqueado |

**Próximo paso inmediato:** Revisión visual de PDFs del ZIP 24.1 por el responsable. Sin cambios de código hasta recibir aprobación.

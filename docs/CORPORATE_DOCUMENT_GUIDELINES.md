# Corporate Document Guidelines — Hellenia ERP

**Fase:** 23  
**Alcance:** Presentación visual únicamente

---

## 1. Principio rector

Todo documento emitido por Hellenia debe percibirse como parte de la misma familia corporativa. Un cliente que reciba cotización, factura y recibo de pago debe identificar inmediatamente la marca.

---

## 2. Documentos cubiertos

| Documento | Reporte Odoo | Template Hellenia |
|-----------|--------------|-------------------|
| Cotización | `sale.action_report_saleorder` | `report_saleorder_document_hellenia` |
| Factura | `account.account_invoices` | `report_invoice_document_hellenia` |
| Nota de crédito | `account.account_invoices` | Misma familia que factura |
| Nota de débito | `account.account_invoices` | Misma familia que factura |
| Orden de compra | `purchase.action_report_purchase_order` | `report_purchaseorder_document_hellenia` |
| RFQ | `purchase.report_purchase_quotation` | `report_purchasequotation_document_hellenia` |
| Delivery slip | `stock.action_report_delivery` | `report_delivery_document_hellenia` |
| Recepción | `stock.action_report_delivery` | `report_delivery_document_hellenia` |
| Recibo de pago | `account.action_report_payment_receipt` | `report_payment_receipt_document_hellenia_visual` |
| Estado de cuenta cliente | `account_followup.action_report_followup` | `report_followup_print_all_hellenia` |
| Estado de cuenta (PDF export) | `account_reports` | `pdf_export_main_hellenia` |

---

## 3. Reglas por documento

### 3.1 Factura / NC / ND

- Título fiscal dinámico según tipo de comprobante (B01, B02, B03, B04)
- Campo **Número de Comprobante Fiscal** (nunca "NCF" visible)
- Leyenda: *Comprobante válido para fines fiscales conforme a la DGII.*
- B02 consumo: *Comprobante de consumo no válido para crédito fiscal.*
- Sin QR (no es facturación electrónica)
- Sin textos en inglés
- Sin bloques técnicos duplicados de `justech_l10n_do_ncf`
- Tabla de líneas con `hellenia-lines-table`

### 3.2 Cotización

- Estructura alineada al documento oficial Hellenia:
  - Encabezado corporativo
  - Datos cliente / vendedor
  - Tabla de productos
  - Bloque **Condiciones comerciales** (validez, pago, ejecutivo)
  - Notas y términos de la orden
- Español en todas las etiquetas

### 3.3 Recibo de pago

Campos obligatorios visibles:

1. Cliente / proveedor
2. Factura afectada
3. Número de Comprobante Fiscal
4. Fecha de pago
5. Método de pago
6. Banco
7. Referencia
8. Monto aplicado
9. Detalle de retenciones (tabla)
10. Total retenido
11. Neto recibido
12. Usuario registrador
13. Fecha y hora de registro

Debe servir como soporte contable impreso.

### 3.4 Orden de compra / RFQ

- Diseño limpio, sin textos innecesarios
- Etiquetas en español
- Misma cabecera y pie que ventas

### 3.5 Delivery slip

- Banner logístico verde con tipo y referencia
- Bloque de información estructurado
- Tabla de productos corporativa
- Zonas de firma: *Entregado por* / *Recibido por*

### 3.6 Estados de cuenta

- Cabecera con logo Hellenia
- Títulos en español
- Tablas con cabecera verde corporativa
- RNC en lugar de "Tax ID"

---

## 4. Idioma

- **100% español** en documentos al cliente/proveedor
- No mostrar etiquetas Odoo en inglés (Invoice Date, Payment Receipt, etc.)

---

## 5. Lo que NO se modifica (Fase 23)

| Área | Estado |
|------|--------|
| Contabilidad | Congelado |
| Pagos / wizard | Congelado |
| Retenciones (lógica) | Congelado |
| Conciliación | Congelado |
| Reportes DGII | Congelado |
| NCF (asignación/secuencia) | Congelado |
| Modelos de negocio | Congelado |

Solo se permiten cambios en: QWeb, SCSS, layouts, paperformat, assets.

---

## 6. Mantenimiento

Al agregar un nuevo reporte PDF:

1. Asignar `paperformat_hellenia_letter`
2. Usar `external_layout_hellenia` (vía layout de compañía)
3. Añadir clase contenedora `hellenia-*-doc`
4. Aplicar `hellenia-lines-table` a tablas de líneas
5. Traducir etiquetas al español
6. Validar visualmente contra factura de referencia
7. Actualizar `PDF_VISUAL_CERTIFICATION.md`

---

## 7. Referencia de color

```
Principal:  #3E4827
Fondo:      #FFFFFF
Prohibido:  azul Odoo, dorado, colores ajenos a marca
```

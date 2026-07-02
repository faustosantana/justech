# Especificación Documentos Comerciales — Hellenia / Justech

**Fase:** 13.5 — Bloque 3  
**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Fecha:** 2026-06-30  
**Estado:** **Especificación de diseño** — implementación en fase posterior  
**Formato papel recomendado:** US Letter (carta 8.5" × 11")

---

## 1. Principios generales

Todos los documentos comerciales Hellenia compartirán:

| Elemento común | Fuente de datos |
|----------------|-----------------|
| Logo empresa | `res.company.logo` |
| Razón social y RNC | `res.company.name`, `res.company.vat` |
| Dirección fiscal | `res.company` partner address |
| Teléfono / email / web | `res.company.phone`, `email`, `website` |
| Encabezado legal | `res.company.report_header` |
| Pie legal | `res.company.report_footer` |
| Fecha emisión | Campo fecha del documento |
| Moneda | `res.currency` (DOP principal) |
| Layout corporativo | `external_layout_hellenia` |

---

## 2. Cotización (Quotation)

**Modelo:** `sale.order` (estado `draft` / `sent`)  
**Reporte Odoo:** `sale.report_saleorder`  
**Título documento:** **COTIZACIÓN** / **QUOTATION**

### 2.1 Encabezado

| Campo | Obligatorio | Fuente |
|-------|-------------|--------|
| Número cotización | Sí | `sale.order.name` |
| Fecha | Sí | `sale.order.date_order` |
| Validez | Sí | `sale.order.validity_date` |
| Vendedor | Sí | `sale.order.user_id` |
| Equipo comercial | Opcional | `sale.order.team_id` |

### 2.2 Cliente

| Campo | Obligatorio | Fuente |
|-------|-------------|--------|
| Cliente | Sí | `partner_id.name` |
| RNC/Cédula | Sí (si disponible) | `partner_id.vat` |
| Dirección entrega | Sí | `partner_shipping_id` |
| Dirección facturación | Sí | `partner_invoice_id` |
| Contacto | Opcional | `partner_id` contact child |
| Teléfono / email | Opcional | `partner_id.phone`, `email` |

### 2.3 Líneas

| Columna | Descripción |
|---------|-------------|
| # | Secuencia |
| Código / SKU | `product_id.default_code` |
| Descripción | `name` |
| Cantidad | `product_uom_qty` + UoM |
| Precio unitario | `price_unit` |
| Descuento % | `discount` (si aplica) |
| Subtotal | `price_subtotal` |

### 2.4 Totales

| Total | Campo |
|-------|-------|
| Subtotal | `amount_untaxed` |
| ITBIS 18% | Desglose por impuesto |
| **Total** | `amount_total` |
| Términos de pago | `payment_term_id` |
| Condiciones comerciales | `note` / términos estándar Hellenia |

### 2.5 Pie

- Validez de la oferta
- Condiciones de entrega
- Firma autorizada (imagen configurable)
- Redes sociales (config empresa)

---

## 3. Orden de Venta (Sales Order)

**Modelo:** `sale.order` (estado `sale`)  
**Reporte Odoo:** `sale.report_saleorder`  
**Título documento:** **ORDEN DE VENTA** / **PEDIDO**

### 3.1 Diferencias respecto a cotización

| Elemento adicional | Fuente |
|--------------------|--------|
| Título "ORDEN DE VENTA" | Estado confirmado |
| Fecha compromiso entrega | `commitment_date` |
| Referencia cliente | `client_order_ref` |
| Estado entrega | Resumen `delivery_status` |
| Almacén origen | `warehouse_id` |

Resto de estructura idéntica a cotización (cliente, líneas, totales, pie).

---

## 4. Factura (Invoice)

**Modelo:** `account.move` (`move_type = out_invoice`)  
**Reporte Odoo:** `account.report_invoice`  
**Título documento:** **FACTURA** / **FACTURA DE CRÉDITO FISCAL**

### 4.1 Encabezado fiscal RD

| Campo | Obligatorio | Fuente |
|-------|-------------|--------|
| **NCF** | Sí | `justech_do_ncf` |
| **Tipo documento** | Sí | `justech_do_document_type_id` (B01/B02) |
| Número factura | Sí | `account.move.name` |
| Fecha factura | Sí | `invoice_date` |
| Fecha vencimiento | Sí | `invoice_date_due` |
| Origen pedido | Opcional | `invoice_origin` |

### 4.2 Cliente

| Campo | Obligatorio |
|-------|-------------|
| Cliente | Sí |
| RNC/Cédula | Sí |
| Dirección fiscal | Sí |

### 4.3 Líneas

| Columna | Descripción |
|---------|-------------|
| Descripción | `name` |
| Cantidad | `quantity` |
| Precio unitario | `price_unit` |
| ITBIS | Impuesto línea |
| Importe | `price_subtotal` |

### 4.4 Totales fiscales

| Total | Campo |
|-------|-------|
| Subtotal gravado 18% | Agrupación impuestos |
| Subtotal exento | Si aplica |
| ITBIS 18% | `amount_tax` |
| **Total a pagar** | `amount_total` |
| Total en letras | Conversión DOP (futuro) |

### 4.5 Pie fiscal

- Leyenda legal DGII / condiciones de pago
- Cuentas bancarias empresa (`res.partner.bank` de company)
- QR verificación (futuro eNCF)
- Código de barras NCF (opcional)

---

## 5. Nota de Crédito (Credit Note)

**Modelo:** `account.move` (`move_type = out_refund`)  
**Reporte Odoo:** `account.report_invoice`  
**Tipo fiscal:** B04 (`justech_do_document_type_id`)  
**Título:** **NOTA DE CRÉDITO**

### 5.1 Campos adicionales

| Campo | Fuente |
|-------|--------|
| NCF nota crédito | `justech_do_ncf` |
| NCF modificado | `justech_do_ncf_modified` / `reversed_entry_id` |
| Factura origen | `reversed_entry_id.name` |
| Motivo | `ref` / razón reversión |

Estructura de líneas y totales igual que factura.

---

## 6. Nota de Débito (Debit Note)

**Modelo:** `account.move` (`move_type = out_invoice` con `debit_origin_id`)  
**Reporte Odoo:** `account.report_invoice`  
**Tipo fiscal:** B03 (`justech_do_document_type_id`)  
**Título:** **NOTA DE DÉBITO**

### 6.1 Campos adicionales

| Campo | Fuente |
|-------|--------|
| NCF nota débito | `justech_do_ncf` |
| NCF modificado | `justech_do_ncf_modified` |
| Factura origen | `debit_origin_id` |
| Motivo incremento | `ref` |

Módulo `account_debit_note` + `justech_l10n_do_ncf` ya soportan la lógica fiscal.

---

## 7. Orden de Compra (Purchase Order)

**Modelo:** `purchase.order` (estado `purchase`)  
**Reporte Odoo:** `purchase.report_purchaseorder`  
**Título:** **ORDEN DE COMPRA**

### 7.1 Encabezado

| Campo | Fuente |
|-------|--------|
| Número OC | `purchase.order.name` |
| Fecha orden | `date_order` |
| Fecha entrega esperada | `date_planned` |
| Comprador | `user_id` |
| Referencia proveedor | `partner_ref` |

### 7.2 Proveedor

| Campo | Fuente |
|-------|--------|
| Proveedor | `partner_id` |
| RNC proveedor | `partner_id.vat` |
| Dirección | `partner_id` contact address |
| Términos de pago | `payment_term_id` |

### 7.3 Líneas

| Columna | Descripción |
|---------|-------------|
| Producto | `product_id` |
| Descripción | `name` |
| Cantidad | `product_qty` + UoM |
| Precio unitario | `price_unit` |
| ITBIS compra | `taxes_id` |
| Subtotal | `price_subtotal` |

### 7.4 Totales

| Total | Campo |
|-------|-------|
| Subtotal | `amount_untaxed` |
| ITBIS | `amount_tax` |
| **Total** | `amount_total` |

### 7.5 Pie

- Condiciones de recepción
- Dirección almacén destino (`picking_type_id.warehouse_id`)
- Firma autorizada compras

---

## 8. RFQ (Solicitud de Cotización a Proveedor)

**Modelo:** `purchase.order` (estado `draft` / `sent`)  
**Reporte Odoo:** `purchase.report_purchasequotation`  
**Título:** **SOLICITUD DE COTIZACIÓN**

Misma estructura que OC con título y nota de que no constituye compromiso de compra.

---

## 9. Documentos adicionales (fase posterior)

| Documento | Prioridad | Módulo |
|-----------|-----------|--------|
| Albarán de entrega | P1 | `hellenia_reports` |
| Orden de recepción | P1 | `hellenia_reports` |
| Recibo de pago / cobro | P1 | `hellenia_reports` |
| Estado de cuenta cliente | P2 | `hellenia_reports` |
| Etiquetas producto | P2 | `stock` estándar + branding |

---

## 10. Matriz resumen

| Documento | Modelo | NCF | ITBIS | Formato |
|-----------|--------|-----|-------|---------|
| Cotización | `sale.order` | No | Desglose | Letter |
| Orden venta | `sale.order` | No | Desglose | Letter |
| Factura | `account.move` | Sí B01/B02 | Sí 18% | Letter |
| Nota crédito | `account.move` | Sí B04 | Sí | Letter |
| Nota débito | `account.move` | Sí B03 | Sí | Letter |
| Orden compra | `purchase.order` | No | Desglose | Letter |
| RFQ | `purchase.order` | No | Desglose | Letter |

---

## 11. Referencias

- [REPORT_ENGINE_ARCHITECTURE.md](REPORT_ENGINE_ARCHITECTURE.md)
- [BRANDING_GUIDE.md](BRANDING_GUIDE.md)
- [NCF_CONFIGURATION.md](NCF_CONFIGURATION.md)
- Módulo fiscal: `custom/justech_l10n_do_ncf/report/report_invoice.xml`

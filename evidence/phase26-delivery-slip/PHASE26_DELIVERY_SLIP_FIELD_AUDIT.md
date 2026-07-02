# Fase 26 — Auditoría de campos: Conduce de Entrega (Justech)

**Base de datos:** `hellenia_test` (Odoo 19)  
**Fecha auditoría:** 2026-07-02 UTC  
**Módulos auditados:** `stock`, `sale`, `sale_stock`, `account` (sin `stock_delivery` en TEST)

---

## Resumen ejecutivo

Los campos necesarios para el Conduce existen en los modelos estándar de Odoo 19. No se requieren campos nuevos ni relaciones inventadas. Las referencias cruzadas entre Cotización, Factura y Entrega se obtienen por campos nativos (`sale_id`, `picking_ids`, `invoice_ids`, `invoice_origin`, `sale_line_id`).

**Campos NO presentes en TEST (documentados, no usar en QWeb sin guard):**

| Modelo | Campo ausente | Alternativa |
|--------|---------------|-------------|
| `stock.picking` | `group_id` | Usar `sale_id` (Odoo 19 / sale_stock) |
| `stock.picking` | `carrier_id` | Omitir transportista si no está instalado `delivery` |
| `account.move` | `picking_ids` | Resolver vía `sale.order` enlazada |
| `account.move` | `stock_move_id` | No usar |

---

## stock.picking

| Requerimiento | Campo Odoo | Tipo | Notas |
|---------------|------------|------|-------|
| Número de Conduce / Picking | `name` | char | Ej. `WH/OUT/00114` |
| Estado | `state` | selection | draft, waiting, confirmed, **assigned** (Listo), **done** (Validado), cancel |
| Orden de venta | `sale_id` | many2one → sale.order | Confirmado en TEST (id 129 → S00128) |
| Cliente | `partner_id` | many2one | Contacto de entrega en salidas |
| Fecha programada | `scheduled_date` | datetime | |
| Fecha efectiva | `date_done` | datetime | Solo cuando `state=done` |
| Responsable | `user_id` | many2one | |
| Almacén origen | `picking_type_id.warehouse_id` o `location_id` | | |
| Ubicación destino | `location_dest_id` | many2one | |
| Observaciones | `note` | html | Editable en formulario |
| Productos (movimientos) | `move_ids` | one2many | Filtrar `product_id` y `state != cancel` |
| Líneas detalle / lotes | `move_line_ids` | one2many | `lot_id`, `lot_name`, `quantity` |
| Origen documental | `origin` | char | Suele contener nombre SO (`S00128`) |

**Factura relacionada:** no hay `invoice_ids` en picking en TEST. Obtener vía `sale_id.invoice_ids`.

---

## stock.move

| Campo | Uso Conduce |
|-------|-------------|
| `product_id` | Código y producto |
| `product_id.default_code` | Columna Código |
| `description_picking` o `product_id.display_name` | Descripción |
| `product_uom_qty` | Cantidad solicitada |
| `quantity` | Cantidad entregada (Odoo 19) |
| `product_uom` | Unidad de medida |
| `sale_line_id` | Enlace a línea de venta |
| `move_line_ids` | Desglose por lote/serie |

---

## stock.move.line

| Campo | Uso |
|-------|-----|
| `quantity` | Cantidad entregada por lote |
| `lot_id` / `lot_name` | Lote o serie |
| `product_uom_id` | UOM |

---

## sale.order

| Requerimiento | Campo |
|---------------|-------|
| Cotización / OV | `name` |
| Cliente | `partner_id` |
| Dirección entrega | `partner_shipping_id` |
| Vendedor | `user_id` |
| Estado | `state` |
| Líneas producto | `order_line` (sin `display_type`, sin anticipos) |
| Cantidad solicitada | `order_line.product_uom_qty` |
| Cantidad entregada | `order_line.qty_delivered` |
| Descripción | `order_line.name` |
| UOM | `order_line.product_uom_id` |
| Entregas | `picking_ids` |
| Facturas | `invoice_ids` (M2M vía sale) |
| Observaciones | `note` (html, editable) |

---

## account.move (factura cliente)

| Requerimiento | Campo |
|---------------|-------|
| Número factura | `name` |
| Cliente | `partner_id` |
| Dirección entrega | `partner_shipping_id` o `partner_id` |
| Vendedor | `invoice_user_id` |
| Estado | `state` |
| Líneas | `invoice_line_ids` (tipo producto) |
| Cantidad | `invoice_line_ids.quantity` |
| Descripción | `invoice_line_ids.name` |
| UOM | `invoice_line_ids.product_uom_id` |
| Origen OV | `invoice_origin` (nombre SO, ej. `S00128`) |
| Observaciones | `narration` (html) |

**OV relacionada:** `search([('name','=', invoice_origin)])` o `invoice_line_ids.sale_line_ids.order_id`.

**Picking relacionado:** `sale_order.picking_ids` (no relación directa factura→picking).

---

## Relaciones documentales (validadas en TEST)

```
sale.order (S00128)
    ├── picking_ids → stock.picking (WH/OUT/00114)  [sale_id en picking]
    └── invoice_ids → account.move (INV/2026/00179)

stock.picking
    └── sale_id → sale.order
    └── factura → sale_id.invoice_ids

account.move
    └── invoice_origin → sale.order.name (cuando existe)
    └── sale.order → picking_ids → stock.picking
```

---

## Evidencia JSON

`evidence/phase26-delivery-slip/audit.json`

# Fase 27 — Auditoría de campos Orden de Compra

**Base de datos:** `hellenia_test` (Odoo 19)  
**Fecha auditoría:** 2026-07-02  
**Módulo:** `justech_report_design` 19.0.7.0.0

## Modelos auditados

| Modelo | Uso en PDF |
|--------|------------|
| `purchase.order` | Cabecera, totales, observaciones |
| `purchase.order.line` | Tabla de productos |
| `res.partner` | Proveedor (vía `partner_id` / `dest_address_id`) |
| `res.company` | Logo y datos empresa (header) |

## Campos `purchase.order` — validados en TEST

| Requisito | Campo real | Estado |
|-----------|------------|--------|
| Número de orden | `name` | OK |
| Estado | `state` | OK |
| Proveedor | `partner_id` | OK |
| Dirección entrega / proveedor | `dest_address_id` o `partner_id` | OK |
| Referencia proveedor | `partner_ref` | OK |
| Fecha de orden | `date_order` | OK |
| Fecha esperada | `date_planned` (cabecera; fallback `line.date_planned`) | OK |
| Comprador | `user_id` | OK |
| Condiciones de pago | `payment_term_id` | OK |
| Moneda | `currency_id` | OK |
| Incoterm | `incoterm_id` + `incoterm_location` | OK |
| Observaciones | `note` | OK (`notes` no existe en Odoo 19) |
| Subtotal | `amount_untaxed` | OK |
| Impuestos | `amount_tax` | OK |
| Total | `amount_total` | OK |

## Campos `purchase.order.line` — validados en TEST

| Requisito | Campo real | Estado |
|-----------|------------|--------|
| Producto | `product_id` | OK |
| Descripción | `name` | OK |
| Cantidad | `product_qty` | OK |
| Unidad | `product_uom_id` | OK (`product_uom` no existe en Odoo 19) |
| Precio unitario | `price_unit` | OK |
| Descuento | `discount` | OK |
| Impuestos | `tax_ids` | OK (`taxes_id` no existe en Odoo 19) |
| Subtotal línea | `price_subtotal` | OK |

## Campos `res.partner` (proveedor)

| Requisito | Campo |
|-----------|-------|
| Nombre | `name` |
| RNC | `vat` |
| Dirección | `street`, `street2`, `city`, `state_id`, `country_id` |
| Teléfono | `phone` |
| Correo | `email` |

## Campos NO inventados

No se usan campos inexistentes. Los siguientes de la especificación genérica **no aplican** en esta instancia:

- `purchase.order.notes` → usar `note`
- `purchase.order.line.product_uom` → usar `product_uom_id`
- `purchase.order.line.taxes_id` → usar `tax_ids`

## Relaciones consultadas (sin modificar)

- `stock.picking` — no usado en PDF OC
- `account.move` — no usado en PDF OC

## Muestra TEST

39 órdenes de compra existentes en `hellenia_test` al momento de la auditoría.

Evidencia JSON: `evidence/phase27-purchase-order/audit.json`

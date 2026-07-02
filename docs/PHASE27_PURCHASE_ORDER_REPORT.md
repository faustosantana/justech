# Fase 27 — Reporte Orden de Compra Hellenia

## Resumen

Reporte PDF paralelo para `purchase.order` con identidad visual Justech/Hellenia (misma familia que Cotización, Factura y Conduce).

**Entorno:** solo `hellenia_test` hasta aprobación visual.  
**Versión módulo:** `justech_report_design` 19.0.7.0.0

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `models/purchase_order.py` | Helpers QWeb (totales, estado, fechas, impuestos) |
| `report/purchase/justech_purchase_order_template.xml` | Plantilla QWeb |
| `static/src/scss/hellenia_purchase_order.scss` | Banda verde y ajustes tabla |
| `data/report_purchase_action_data.xml` | Acción `action_report_justech_purchase_order` |
| `views/purchase_order_views.xml` | Botón header **Orden de Compra PDF** |

## Reportes

| Acción | Nombre menú Imprimir | Reemplaza estándar |
|--------|----------------------|--------------------|
| `justech_report_design.action_report_justech_purchase_order` | **Orden de Compra Hellenia** | No |
| `purchase.action_report_purchase_order` | Estándar Odoo / hellenia_reports | Sin cambios |

## Diseño

1. **Header** — Logo + empresa (sin repetir en cuerpo)
2. **Banda verde** — ORDEN DE COMPRA + 2 columnas (No./Estado/Comprador | Moneda/Fechas)
3. **Proveedor** + **Información de compra**
4. **Tabla** — #, Código, Descripción, Cantidad, Unidad, P.U., Descuento (cond.), Impuesto, Subtotal
5. **Totales** — mismo bloque que cotización/factura
6. **OBSERVACIONES** — campo `note`
7. **Firmas** — Entregado por / Autorizado por / Proveedor
8. **Footer verde** — teléfono, correo, web, página X de Y

## UX

- Botón en formulario OC: **Orden de Compra PDF**
- Menú **Imprimir → Orden de Compra Hellenia**

## Despliegue TEST

```bash
./scripts/run-phase27-purchase-order-test.sh
```

## Rollback TEST

Revertir `justech_report_design` a versión anterior a `19.0.7.0.0` y ejecutar:

```bash
docker compose -f docker/test/docker-compose.yml run --rm odoo \
  -u justech_report_design --stop-after-init
```

## Criterio PASS

- Mismo lenguaje visual que cotización/factura/conduce
- Sin errores QWeb
- Reporte estándar de compras sigue operativo
- Solo TEST hasta aprobación visual del cliente

## Validación TEST (2026-07-02)

| Check | Resultado |
|-------|-----------|
| Módulo `19.0.7.0.0` | PASS |
| 9 escenarios PDF | PASS |
| Vista previa HTML | PASS |
| Reporte estándar Odoo | PASS |
| Botón + menú Imprimir | PASS |
| Columna descuento condicional | PASS |

Evidencia: `evidence/phase27-purchase-order/` y `packages/phase27-purchase-order/phase27-evidence.zip`

**Estado:** validación técnica PASS — **pendiente aprobación visual** del cliente antes de PROD.

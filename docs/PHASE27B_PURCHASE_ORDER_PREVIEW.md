# Fase 27B — Vista previa Orden de Compra Hellenia

## Resumen

Botón **Vista previa** en el formulario `purchase.order` que abre el reporte oficial Hellenia en HTML (nueva pestaña), sin descargar PDF.

**Versión:** `justech_report_design` 19.0.7.2.0

## Implementación

| Componente | Detalle |
|------------|---------|
| Método | `action_preview_purchase_order()` → `/report/html/{report_name}/{id}` |
| Reporte | `purchase.action_report_purchase_order` (mismo que Imprimir) |
| Vista | Botón en header, antes de Imprimir |
| Target | `new` (pestaña nueva, formulario intacto) |

## Sin cambios en

- Diseño PDF/QWeb del reporte
- Lógica de compras, recepciones, facturas proveedor, inventario, contabilidad
- Cotización, factura, conduce

## Despliegue PROD

```bash
./scripts/run-phase27b-purchase-order-preview-prod.sh
```

## Evidencia

`evidence/phase27b-purchase-order-preview-prod/`

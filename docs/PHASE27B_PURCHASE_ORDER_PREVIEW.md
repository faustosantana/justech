# Fase 27B — Vista previa nativa Orden de Compra Hellenia

## Resumen

Botón **Vista previa** en el formulario `purchase.order` que abre el flujo nativo estilo Odoo (portal con iframe, volver a edición, imprimir, descargar PDF).

**Versión:** `justech_report_design` 19.0.7.3.1

## Implementación

| Componente | Detalle |
|------------|---------|
| Botón | Header `purchase.order` → `action_preview_purchase_order()` |
| Acción | `ir.actions.act_url` con `target: self` |
| URL preview | `/my/purchase/{id}/preview?access_token=...` |
| Reporte oficial | `purchase.action_report_purchase_order` (diseño Hellenia Justech) |
| Iframe HTML | `/my/purchase/{id}/jt_report_html` |
| Descargar PDF | `/my/purchase/{id}/jt_report_pdf?download=true` |
| Imprimir | JS `purchase_sidebar.js` (patrón factura) |
| Volver a edición | Banner portal → `/odoo/action-purchase.purchase_rfq/{id}` |

## Archivos clave

- `models/purchase_order.py` — método `action_preview_purchase_order()`
- `controllers/purchase_portal.py` — rutas `/preview`, `/jt_report_html`, `/jt_report_pdf`
- `report/purchase/justech_purchase_order_portal.xml` — plantilla portal dedicada
- `static/src/interactions/purchase_sidebar.js` — resize iframe + print
- `views/purchase_order_views.xml` — botón Vista previa

## Sin cambios en

- Diseño PDF/QWeb del reporte oficial
- Lógica de compras, recepciones, facturas proveedor, inventario, contabilidad
- Cotización, factura, conduce

## Despliegue

```bash
# TEST
./scripts/run-phase27b-po-native-preview.sh test

# PROD (con backup automático)
./scripts/run-phase27b-po-native-preview.sh prod
```

Tras `-u justech_report_design` es obligatorio reiniciar el contenedor Odoo para registrar rutas HTTP.

## Criterio PASS

- Botón **Vista previa** visible en formulario OC
- Preview abre página portal (NO `/report/html/` directo en pestaña suelta)
- Sidebar con Descargar e Imprimir
- Banner volver a edición funcional
- Iframe muestra diseño Hellenia (`jt-po-band`)
- Menú Imprimir → Orden de Compra sigue OK
- Sin QWebError / RPCError / OWLError

## Evidencia

- TEST: `evidence/phase27b-po-native-preview-test/`
- PROD: `evidence/phase27b-po-native-preview-prod/`

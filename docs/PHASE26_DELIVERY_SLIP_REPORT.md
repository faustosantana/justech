# Fase 26 — Conduce de Entrega Justech

## Alcance

Reporte paralelo **Justech PDF — Conduce de Entrega** en `justech_report_design` 19.0.5.0.0.

- Template: `justech_report_design.report_justech_delivery_document`
- Acción principal: `justech_report_design.action_report_justech_delivery` (`stock.picking`)
- Acciones paralelas: desde `sale.order` y `account.move`
- **No reemplaza** `stock.action_report_delivery` ni plantillas estándar.

## Diseño

Mismo lenguaje visual que Cotización y Factura:

- Header logo + empresa
- Banda verde `#3E4827`
- Bloque información limpio (sin cajas)
- Tabla sin precios ni impuestos
- Observaciones, firmas, footer verde

## Impresión

| Origen | Menú Imprimir |
|--------|----------------|
| Entrega (`stock.picking`) | Justech PDF — Conduce de Entrega |
| Cotización / OV (`sale.order`) | Justech PDF — Conduce de Entrega |
| Factura (`account.move`) | Justech PDF — Conduce de Entrega |

## Despliegue

**Solo TEST** hasta aprobación visual:

```bash
./scripts/run-phase26-delivery-slip-test.sh
```

## Documentación

- Auditoría campos: `docs/PHASE26_DELIVERY_SLIP_FIELD_AUDIT.md`
- Evidencia: `evidence/phase26-delivery-slip/`
- Rollback: `evidence/phase26-delivery-slip/Rollback.md`

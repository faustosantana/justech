# UX — Retenciones en wizard de pagos (Fase 18)

## Columna Retenciones

En **Facturas pendientes**, cada fila incluye:

| Columna | Contenido |
|---------|-----------|
| Retenciones | Selector múltiple (tags) |
| Resumen | `Ninguna` o nombres separados por coma |
| Monto retenido | Total RD$ de esa factura |

## Ninguna

- Estado por defecto cuando `withholding_catalog_ids` está vacío
- Resumen muestra literalmente **Ninguna**
- No se generan líneas contables de retención

## Selección múltiple

- El usuario puede marcar una o más retenciones del catálogo
- Cada factura del mismo pago puede tener combinación distinta
- Al seleccionar retenciones, se desmarca implícitamente el estado "Ninguna"

## Detalle

Bloque **Detalle retenciones por factura** muestra por cada línea:

- Factura
- Retención
- Base
- Porcentaje
- Monto retenido
- Cuenta contable

## Español

Sin términos: Withholding, Tax Withholding, Void, Origin NCF, NCF Voided.

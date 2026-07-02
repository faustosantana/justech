# Fase 18 — Motor contable de retenciones por factura

## Resumen

Rediseño del flujo de retenciones RD: **cada factura pendiente** en el wizard de pagos tiene su propia columna **Retenciones**, independiente del resto de facturas del mismo pago.

## Modelo catálogo

`hellenia.withholding.catalog` — configurable, vinculado a impuestos `l10n_do`:

| Campo | Descripción |
|-------|-------------|
| name | Nombre visible (español) |
| code | Código técnico único por compañía |
| tax_id | Impuesto retención l10n_do |
| rate | Porcentaje (desde impuesto) |
| base_type | `untaxed` (base imponible) o `itbis` (ITBIS facturado) |
| account_id | Cuenta contable (repartición impuesto) |
| partner_scope | Cliente / Proveedor / Ambos |
| move_scope | Venta / Compra |
| affects_606 / affects_607 | Impacto reportes DGII |

Sincronización: `sync_catalog_from_taxes()` en post_init y `configure_withholding_reference()`.

## Retenciones mínimas

Reutilizadas de l10n_do cuando existen:

- Retención 5% Gobierno → `-5% ISR Gov.`
- Retención ITBIS 30% → `-30% ITBIS Leg. (N02-05)`
- Retención ITBIS 100% → `-100% ITBIS (N07-09)`
- Retención proveedor informal 10% → `-10% ISR Fee`
- Retención ITBIS informal 75% → `-75% ITBIS (N08-10)`
- Retención ISR 2% → `-2% ISR (N07-07)`
- Retención honorarios 10% → `-10% ISR Rent.`

## UX wizard

- Columna **Retenciones** con widget tags (many2many)
- Por defecto: **Ninguna** (sin selección)
- Resumen y monto retenido por factura
- Detalle expandible bajo la tabla

## Versión

`hellenia_account` **19.0.1.0.5**

# Fase 19.2 — Manejo de errores exportador 606

## Problema resuelto

Antes, el wizard del 606 mostraba una lista plana de 200+ errores cuando el período incluía facturas UAT/Fase 4/Fase 5 incompletas. El export fallaba por completo aunque existieran facturas válidas.

## Controles fiscales en `account.move`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `justech_do_include_in_dgii` | Boolean (default True) | Incluir en reportes DGII Sí/No |
| `justech_do_dgii_exclusion_reason` | Text | Motivo de exclusión fiscal |
| `justech_do_dgii_fiscal_state` | Selection | `valid` / `incomplete` / `excluded` / `cancelled` |

La anulación de NCF (`action_void_ncf`) marca automáticamente `cancelled` y excluye del DGII.

## Clasificación del período

El exportador `justech.do.dgii.606.exporter` clasifica cada compra del período:

| Estado | Criterio |
|--------|----------|
| **Anulado** | `justech_do_ncf_voided` o estatus DGII `2` |
| **Excluido** | `justech_do_include_in_dgii = False` |
| **Incompleto** | Incluido pero falta RNC, tipo id, NCF, impuesto o código retención |
| **Válido** | Incluido y pasa todas las validaciones |

## API del exportador

### `validate_period_606(company, date_from, date_to)`

Retorna:

- `buckets`: conjuntos `all`, `valid`, `incomplete`, `excluded`, `cancelled`
- `errors_by_partner`: errores agrupados por proveedor
- `counts`: totales para resumen

### `format_validation_summary(result)`

Texto corto en español para wizard e historial.

### `export_xlsx(..., moves=None, strict=False)`

- Por defecto exporta solo documentos **válidos**.
- `strict=True` bloquea si hay incompletos (comportamiento legacy).

### `export_errors_xlsx(...)`

Excel con tres hojas:

1. **Errores** — facturas incompletas con detalle
2. **Excluidos** — documentos fuera del DGII + motivo
3. **Validos** — documentos que entrarán al 606

## Wizard mejorado

**Contabilidad → Reportes → Reportes DGII → Generar 606**

1. **Validar período** — muestra resumen (no lista gigante)
2. **Descargar errores (Excel)** — detalle completo
3. **Generar Excel 606** — solo válidos (estado `ok` o `warning`)
4. **Guardar historial** — registra conteos y adjunta reporte de errores

Estados de validación:

| Estado | Significado |
|--------|-------------|
| `ok` | Todos los incluidos son válidos |
| `warning` | Hay incompletos pero existen válidos para exportar |
| `error` | Ningún documento válido para exportar |

## Validaciones exigidas (documentos incluidos)

- RNC/Cédula del proveedor
- Tipo identificación DGII (`justech_do_partner_id_type`)
- NCF
- Impuestos clasificados (ITBIS / ISC)
- Retenciones con código DGII en catálogo
- Fecha dentro del período

## Uso operativo recomendado

1. Marcar como excluidas facturas no reportables (UAT, pruebas, internas).
2. Validar período y revisar resumen.
3. Corregir incompletos reales o excluirlos con motivo documentado.
4. Exportar 606 (solo válidos).
5. Archivar Excel de errores junto al cierre mensual.

# Documentación complementaria — localización DO

Notas técnicas y referencias adicionales a las plantillas DGII.

## Documentos principales

| Documento | Descripción |
|-----------|-------------|
| `docs/DGII_TEMPLATES.md` | Inventario y política de plantillas oficiales |
| `docs/DGII_FORMAT_MAPPING_ANALYSIS.md` | Análisis Fase 17.5 — metodología y hallazgos |
| `docs/DGII_SUPPORTED_FORMATS_MATRIX.md` | Matriz de 33 formatos y estado exportador |
| `docs/DGII_MISSING_FIELDS_BACKLOG.md` | Campos Odoo/Justech faltantes |

## Mapeos JSON (Fase 17.5)

Ruta: `data/localizations/do/mappings/`

- `dgii_606.json` — Compras NG
- `dgii_607.json` — Ventas NG
- `dgii_608.json` — NCF anulados NG
- `dgii_609.json` — Pagos al exterior NG
- `dgii_623.json` — Retenciones del Estado
- `dgii_itbis.json` — Adelantos ITBIS (LOCAL + IMPORTACION)
- `dgii_norma_2_05.json` — Retenciones a terceros

## Análisis machine-readable

`templates_analysis_summary.json` — resumen estructural de los 33 ZIP (regenerable con `scripts/analyze_dgii_templates.py`).

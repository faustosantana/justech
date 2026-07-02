# Evidencia Fase 25 — Factura fiscal Justech

**Fase:** 25  
**Módulo:** `justech_report_design` v19.0.3.0.0  
**Base de datos:** `hellenia_test` únicamente

## Contenido esperado

| Archivo | Descripción |
|---------|-------------|
| `validation.json` | Resultado PASS/FAIL de todas las validaciones |
| `audit.json` | Auditoría de módulos y campos |
| `invoice_1_line.pdf` / `.png` | Factura 1 línea |
| `invoice_multi_line.pdf` | Varias líneas |
| `invoice_discount.pdf` | Con descuento |
| `invoice_no_discount.pdf` | Sin descuento |
| `invoice_ncf_b01.pdf` | NCF fiscal publicado |
| `invoice_b02_consumo.pdf` | Factura consumo |
| `invoice_usd.pdf` | Moneda USD (si aplica) |
| `invoice_observations.pdf` | Observaciones narration |

## Generar evidencia

```bash
bash scripts/run-phase25-test.sh
```

## Criterio PASS

- Diseño coincide con imagen aprobada
- Sin duplicar información de empresa
- Bloque bajo FACTURA: solo cliente, pago, vendedor, fechas
- NCF y tipo comprobante reales
- Totales / ITBIS / descuento coinciden Odoo
- Retenciones solo si existen
- Factura estándar y cotización sin cambios
- Sin errores QWeb

## Rollback

Ver `docs/PHASE25_INVOICE_REPORT.md` sección Rollback.

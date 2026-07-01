# Fase 23.3H — Paperformat cotización (espacio superior)

**Fecha:** 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_reports` 19.0.1.4.3

## Problema

El PDF de cotización tenía ~75 mm de espacio muerto superior causado por:

| Fuente | Valor anterior |
|--------|----------------|
| `paperformat_hellenia_letter.margin_top` | 40 mm |
| `paperformat_hellenia_letter.header_spacing` | 35 mm |
| Hack CSS `margin: -4mm` | Insuficiente |

## Solución

### 1. Nuevo paperformat (solo cotizaciones)

Registro: `hellenia_reports.paperformat_hellenia_quotation`

| Campo | Valor |
|-------|-------|
| Nombre | Hellenia Quotation Paperformat |
| Formato | Letter |
| margin_top | 5 mm |
| margin_bottom | 8 mm |
| margin_left | 8 mm |
| margin_right | 8 mm |
| header_spacing | 0 |
| dpi | 90 |

### 2. Asignación dinámica (sin afectar otros reportes)

`models/ir_actions_report.py`:

- `get_paperformat()` devuelve paperformat cotización si `hellenia_use_quotation_paperformat` en contexto.
- `_render_qweb_pdf()` activa ese contexto solo cuando `sale.report_saleorder` y órdenes en estado `draft`/`sent`.
- Pedidos confirmados, facturas, compras, etc. siguen con `paperformat_hellenia_letter` (40/25/10 mm).

### 3. CSS template

- Eliminado `margin-top: -4mm` en `.hellenia-quote-page`.
- `html, body` y `.hellenia-article` sin padding/margin superior.
- Logo 75×220 px sin cambios.

## Evidencia

`evidence/phase23-3h-paperformat-spacing/`

- `screenshot_before_1_product.png` — antes (23.3G)
- `screenshot_after_1_product.png` — después (23.3H)
- PDFs 1/5/15/25 productos
- `validation.json`

## Criterios PASS

- Sin espacio muerto superior
- Logo visible arriba
- 1 producto = 1 página
- Ancho útil completo
- Otros reportes sin cambio

**No promovido a PROD.**

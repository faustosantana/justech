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

| Archivo | Descripción |
|---------|-------------|
| `screenshot_before_1_product.png` | Antes (23.3G) — espacio muerto ~75 mm arriba |
| `screenshot_after_1_product.png` | Después (23.3H) — logo al borde superior imprimible |
| `quotation_1_product.pdf` | 1 producto, 1 página |
| `quotation_5_products.pdf` | 5 productos, 1 página |
| `quotation_15_products.pdf` | 15 productos, 1 página |
| `quotation_25_products.pdf` | 25 productos, 2 páginas (paginación correcta) |
| `portal_quote_1.pdf` | Portal cliente, 1 página |
| `validation.json` | PASS en `hellenia_test` |

## Resultado TEST (PASS)

| Criterio | Resultado |
|----------|-----------|
| Sin espacio muerto superior | PASS — `margin_top=5`, `header_spacing=0` |
| Logo visible arriba | PASS |
| Empresa alineada arriba derecha | PASS |
| 1 producto = 1 página | PASS |
| 5 / 15 productos | PASS — 1 página cada uno |
| 25 productos | PASS — 2 páginas, condiciones en página 2 |
| Pedido confirmado | PASS — sigue `Hellenia Carta` (40 mm top) |
| Ancho útil completo | PASS |

**No promovido a PROD.**

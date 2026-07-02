# Fase 27 — Orden de Compra Hellenia (TEST)

**Entorno:** `hellenia_test` únicamente — **NO producción**

**Versión:** `justech_report_design` 19.0.7.0.0

## Contenido

| Archivo | Descripción |
|---------|-------------|
| `validation.json` | Resultado validación automatizada |
| `audit.json` | Auditoría de campos reales |
| `ui_evidence.json` | Botón header + menú Imprimir |
| `00_html_preview.html` | Vista previa HTML QWeb |
| `*.pdf` / `*.png` | Muestras PDF por escenario |
| `shell.log` | Log ejecución |

# Escenarios PDF

- `01_one_line` — 1 línea
- `02_five_lines` — 5 líneas
- `03_twenty_lines` — 20 líneas (multipágina)
- `04_with_discount` / `05_no_discount`
- `06_usd` / `07_dop`
- `08_international_vendor` / `09_national_vendor`
- `00_html_preview.html` — vista previa QWeb

Fixtures creados en borrador con `partner_ref=PHASE27-EVIDENCE-*` (solo TEST).

## Rollback

Ver `docs/PHASE27_PURCHASE_ORDER_REPORT.md`

## Estado

Validación técnica **PASS** en `hellenia_test` (ver `validation.json`).

Pendiente **aprobación visual** del cliente antes de PROD.

| Artefacto | Ubicación |
|-----------|-----------|
| ZIP evidencia | `packages/phase27-purchase-order/phase27-evidence.zip` |
| ZIP módulo | `packages/phase27-purchase-order/justech_report_design-v19.0.7.0.0.zip` |

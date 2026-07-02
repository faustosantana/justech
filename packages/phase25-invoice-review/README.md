# Evidencia Fase 25A — Revisión visual factura Justech

**Estado:** `PENDING_USER_VISUAL_APPROVAL`  
**Entorno:** `hellenia_test` únicamente  
**Reporte:** paralelo `Justech PDF — Factura`

## Contenido

| Tipo | Archivos |
|------|----------|
| PDFs | `01_` … `09_` (9 escenarios) |
| PNGs | Primera página de cada PDF + `03_invoice_22_lines_p2.png` |
| JSON | `validation.json`, `audit.json`, `manifest.json` |
| Fuentes | En ZIP: `xml/`, `scss/` |
| Docs | `docs/PHASE25_VISUAL_REVIEW.md`, `docs/PHASE25_VISUAL_AUDIT.md` |

## Escenarios incluidos

1. Factura 1 línea (borrador)
2. Factura 5 líneas (borrador)
3. Factura 22 líneas / 2 páginas (borrador)
4. Factura con descuento
5. Factura sin descuento
6. Factura fiscal B01 publicada con NCF
7. Factura consumo B02
8. Factura gubernamental (toggle retención — sin fila visible en PDF)
9. Nota de crédito B04

## Generar de nuevo

```bash
bash scripts/run-phase25a-visual-review.sh
```

## Revisión visual

Ver matriz PASS/FAIL en `docs/PHASE25_VISUAL_REVIEW.md`  
Ver diferencias y correcciones propuestas en `docs/PHASE25_VISUAL_AUDIT.md`

## Importante

- **No** se implementaron correcciones en esta fase.
- **No** declarar terminado / listo para producción hasta tu aprobación explícita.
- PROD, factura estándar, DGII, contabilidad y cotización: **sin cambios**.

## Rollback

Ver `ROLLBACK.md` en este directorio.

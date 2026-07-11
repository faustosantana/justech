# BUGFIX-QUOTATION-TERMS-1 — Causa raíz

## Síntoma

`AttributeError: 'sale.order' object has no attribute 'jt_quotation_note_for_report'`

Plantilla QWeb: `justech_report_design.hellenia_quotation_body`

Expresión: `t-out="doc.jt_quotation_note_for_report()"`

## Diagnóstico (repo + PROD)

| # | Pregunta | Resultado |
|---|----------|-----------|
| 1 | ¿Dónde debe existir el método? | `custom/justech_report_design/models/sale_order.py` |
| 2 | ¿Existe en `sale.order`? | Sí en disco; **no siempre en el worker HTTP vivo** |
| 3 | ¿Importado en `models/__init__.py`? | Sí (`from . import sale_order`) |
| 4 | ¿Módulo instalado? | Sí (`justech_report_design`) |
| 5 | ¿Dependencia correcta? | `justech_report_design` → `hellenia_reports` |
| 6 | ¿XML sin Python? | Parcial: vista en BD actualizada tras `-u`, worker con Python viejo |
| 7 | ¿`-u` ejecutado? | Sí en PROD (19.0.7.4.1), **no** en TEST hasta este bugfix |
| 8 | ¿Reinicio real tras upgrade? | **No.** Contenedor PROD seguía con `StartedAt` anterior al `-u` |
| 9 | `hasattr(...)` en shell fresco | `True` (proceso nuevo carga Python actual) |

## Causa raíz

Tras HELLENIA-QUOTATION-TERMS-1:

1. Se actualizó la plantilla QWeb en BD para llamar `jt_quotation_note_for_report()`.
2. El método Python sí estaba en disco e importado.
3. El `-u` se ejecutó en un contenedor efímero (`docker compose run --rm`).
4. El contenedor HTTP de Odoo **no se recreó de forma efectiva** (workers con registry/Python previo).
5. Resultado: la vista nueva invocaba un método que el proceso HTTP aún no tenía → Error 500.

No era un fallo de diseño del reporte de facturas/NCF; era un **desfase registry/vista vs proceso HTTP** en cotización.

## Corrección

1. Método `jt_quotation_note_for_report()` robusto y autosuficiente (sanitiza HTML, no lanza por vacío).
2. Campo computado `jt_quotation_note_html` para QWeb (`t-out`).
3. Upgrade controlado + **`docker compose up -d --force-recreate odoo`** en TEST y PROD.
4. Validación `hasattr == True` en proceso post-recreate.

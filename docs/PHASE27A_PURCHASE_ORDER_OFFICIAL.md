# Fase 27A — Orden de Compra oficial Hellenia

## Resumen

`purchase.action_report_purchase_order` (menú **Imprimir → Orden de Compra**) apunta al diseño Justech/Hellenia.

Se eliminó el botón duplicado **Orden de Compra PDF** y la entrada paralela en Imprimir.

**Versión:** `justech_report_design` 19.0.7.1.0

## Cambios

| Antes (Fase 27) | Después (Fase 27A) |
|-----------------|-------------------|
| Botón **Orden de Compra PDF** → Justech | Sin botón |
| Imprimir → **Orden de Compra Hellenia** (paralelo) | Imprimir → **Orden de Compra** (oficial Justech) |
| Imprimir → Orden de Compra (Odoo estándar) | Respaldo técnico sin menú |

## Archivos

- `data/report_official_data.xml` — override `purchase.action_report_purchase_order`
- `data/report_purchase_action_data.xml` — acción Justech sin binding
- Eliminado `views/purchase_order_views.xml`
- Eliminado `action_jt_print_purchase_order` de `models/purchase_order.py`

## Rollback

1. Restaurar backup PROD (`backups/hellenia-prod/<timestamp>/`)
2. O revertir módulo a `19.0.7.0.0` y `-u justech_report_design`

## Despliegue PROD

```bash
./scripts/run-phase27a-purchase-order-official-prod.sh
```

## Evidencia

`evidence/phase27a-purchase-order-official-prod/`

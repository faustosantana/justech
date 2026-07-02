# Rollback — Fase 25A (revisión visual)

Esta fase **no modifica** el reporte. Solo genera evidencia en TEST.

## Ocultar reporte paralelo (opcional)

```python
action = env.ref("justech_report_design.action_report_justech_invoice")
action.write({"binding_model_id": False})
env.cr.commit()
```

## Eliminar facturas de prueba generadas

Las facturas creadas por `phase25a-invoice-visual-review.py` son borradores/publicadas de prueba en `hellenia_test` (IDs ~8151–8159 en ejecución 2026-07-02). Pueden cancelarse/archivarse manualmente si se desea limpiar TEST.

## Restaurar estado anterior

No se requiere rollback de código: el reporte paralelo existía desde Fase 25. Esta fase solo añade documentación y evidencia.

## Verificación

- `account.account_invoices` → reporte estándar Odoo intacto
- `sale.action_report_saleorder` → cotización Justech intacta

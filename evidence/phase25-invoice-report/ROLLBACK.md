# Rollback — Fase 25 Factura fiscal Justech

**Tiempo estimado:** < 1 minuto  
**Impacto:** solo reporte paralelo; factura estándar no se afecta

## Opción A — Ocultar del menú Imprimir (recomendado)

```bash
docker compose exec odoo odoo shell -d hellenia_test
```

```python
action = env.ref("justech_report_design.action_report_justech_invoice")
action.write({"binding_model_id": False})
env.cr.commit()
```

## Opción B — Revertir módulo a versión anterior

```bash
cd /opt/odoo-projects/hellenia
git checkout <commit-anterior> -- custom/justech_report_design
docker compose exec odoo odoo -d hellenia_test -u justech_report_design --stop-after-init
```

## Opción C — Desinstalar módulo (NO recomendado)

Desinstalar `justech_report_design` también afecta la cotización oficial. Usar solo si se migra cotización a otro módulo.

## Verificación post-rollback

1. `account.account_invoices` sigue apuntando a `account.report_invoice_with_payments`
2. `sale.action_report_saleorder` sigue en diseño Justech cotización
3. Menú Imprimir en factura ya no muestra «Justech PDF — Factura» (opción A)

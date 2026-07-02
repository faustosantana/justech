# Rollback — Fase 27 Orden de Compra (TEST)

1. Checkout módulo `justech_report_design` a versión **19.0.6.2.0** (o anterior sin purchase).
2. En VPS TEST:
   ```bash
   cd /opt/odoo-projects/hellenia/docker/test
   docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
     -d hellenia_test -u justech_report_design --stop-after-init --no-http
   docker compose --env-file ../../config/test/.env up -d odoo
   ```
3. Verificar que el menú **Orden de Compra Hellenia** ya no aparece en Imprimir.
4. El reporte estándar `purchase.action_report_purchase_order` no fue modificado por esta fase.

# Rollback — Fase 27A Orden de Compra oficial

1. Restaurar desde backup en `backup_path.txt` (postgres + filestore + custom).
2. Alternativa mínima: checkout `justech_report_design` **19.0.7.0.0** y:
   ```bash
   docker compose -f docker/production/docker-compose.yml run --rm odoo \
     -u justech_report_design --stop-after-init
   ```
3. Verificar menú Imprimir y ausencia/presencia de botón según versión deseada.

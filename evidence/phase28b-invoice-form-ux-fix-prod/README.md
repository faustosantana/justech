# Fase 28B — Corrección UX Factura Cliente (PROD)

**Fecha:** 2026-07-03  
**Entorno:** `hellenia_prod` / https://odoo.hellenia.cloud  
**Resultado validación:** **PASS** (23/23)  
**Healthcheck:** **PASS**

## Backup PROD (pre-despliegue)

```
/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-03_0131
```

Verificado: `postgres_all.sql.gz` (3.5 MB), `filestore.tar.gz` (4.9 MB), `custom.tar.gz`, `docker-compose.yml`, `.env`

## Despliegue

| Item | Valor |
|------|--------|
| Comando | `-u hellenia_ux --stop-after-init` |
| Módulo | `hellenia_ux` **19.0.1.2.0** |
| Alcance | Solo XML/SCSS |

## Orden de pestañas PROD

1. Líneas de factura
2. Apuntes contables
3. Otra información
4. Información Fiscal
5. Retenciones

## Validación PROD

- HTTP login 200 (~0.48 s) ✓
- Pestaña por defecto = Líneas de factura ✓
- Retenciones fuera del header ✓
- Información Fiscal al final ✓
- Crear factura sin/con cliente ✓
- Agregar línea + confirmar ✓
- `justech_report_design` **19.0.7.3.1** sin cambios ✓
- `justech_l10n_do_ncf` **19.0.1.5.1** sin cambios ✓

## Rollback

```bash
bash /opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh \
  /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-03_0131
```

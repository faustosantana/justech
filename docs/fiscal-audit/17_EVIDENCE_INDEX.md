# 17 — Índice de evidencias

## Rutas

- Documentos: `docs/fiscal-audit/`
- Evidencias: `evidence/fiscal-audit/`
- Backup servidor: `/opt/odoo-dev/backups/fiscal-master-audit-20260717_032503`

## Mapa

| Carpeta | Contenido |
|---|---|
| `entorno/` | environment.txt, modules_installed.txt |
| `backup/` | BACKUP_PATH.txt |
| `restore/` | result.txt (PASS) |
| `SQL/` | data_quality, ncf stats, duplicates, crons, fields |
| `codigo/` | (scans locales referenciados en 04) |
| `crons/` | crons.txt |
| `datos/` | (copias SQL calidad) |
| `reportes/` | uso fiscal_report en SQL |
| `multiempresa/` | companies/ranges en data_quality |
| `permisos/` | groups en crons_security / findings |
| `vistas/` | observaciones doc 10 |
| `ORM/` | reserved |
| `logs/` | reserved |

## Archivos SQL clave

- `SQL/data_quality_audit.txt`
- `SQL/ncf_latam_stats.txt`
- `SQL/ncf_fields_and_doctype.txt`
- `SQL/duplicates_detail.txt`
- `SQL/duplicates_scoped.txt`
- `SQL/crons.txt`
- `SQL/environment.txt`
- `SQL/modules_installed.txt`
- `SQL/result.txt`

# Fase 15 — Reporte corrección menús en PRODUCCIÓN

**Fecha:** 2026-06-30  
**Ambiente:** `hellenia_prod` (`https://odoo.hellenia.cloud`)  
**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-06-30_1800`

---

## Flujo ejecutado

```
TEST PASS → Backup PROD → Upgrade módulos → Validación PROD → Healthcheck PASS
```

## Módulos promovidos

| Módulo | Versión/cambio |
|--------|----------------|
| hellenia_ui | 19.0.1.0.4 — `apply_all()`, fix árbol contable |
| justech_l10n_do_base | Menús Localización Dominicana, grupos heredados |
| justech_l10n_do_ncf | Etiquetas español |
| justech_l10n_do_reports | 606/607/608, Auditoría |

## Validación PROD

**Evidencia:** `evidence/phase15-validate-prod.json`  
**Resultado:** `ok: true`

| Criterio | PROD |
|----------|------|
| Contabilidad abre Tablero (no Ajustes) | **PASS** — `first_child: Tablero` |
| Sin duplicados Facturación/Accounting | **PASS** |
| Justech integrado | **PASS** — Localización Dominicana, Reportes DGII, Auditoría |
| it@justech.do menús core | Contactos, Ventas, Contabilidad, Compras, Inventario, Apps, Configuración |
| HTTPS login | **200** |
| Healthcheck completo | **PASS** |

## Rollback

Si necesario: restaurar backup `2026-06-30_1800` desde `/opt/odoo-projects/hellenia/backups/hellenia-prod/`.

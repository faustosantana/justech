# Checklist ejecución PROD — Cotización paralela v19.0.1.1.6

> Copia operativa del plan completo: `docs/PHASE24_1_PROD_PARALLEL_MIGRATION_PLAN.md`  
> ⛔ **NO EJECUTAR** sin autorización final.

---

## Pre-ejecución

- [ ] Autorización escrita recibida
- [ ] Commit `2306747` / módulo v`19.0.1.1.6` en VPS
- [ ] Ventana acordada

## 1. Backup

- [ ] `./scripts/backup-hellenia-prod.sh`
- [ ] Verificar `postgres_all.sql.gz` + `custom.tar.gz`
- [ ] Anotar ruta: `________________________`

## 2. Instalación

- [ ] Copiar solo `custom/justech_report_design/`
- [ ] `grep version` → `19.0.1.1.6`
- [ ] `-i justech_report_design` en `hellenia_prod`
- [ ] Reiniciar `hellenia-prod-odoo-1`
- [ ] Shell: módulo `installed`

## 3. Validación cotización real

- [ ] PDF **Cotización Hellenia (Diseño)** — 1 producto
- [ ] PDF **Cotización Hellenia (Diseño)** — 5+ productos
- [ ] VIS-001: sin borde en condiciones/firmas
- [ ] Guardar evidencia en `evidence/phase24-1-prod-parallel/`

## 4. Reporte estándar

- [ ] **Cotización en PDF** sigue en menú Imprimir
- [ ] PDF estándar genera sin error
- [ ] `jt_inherits` = 0 en reportes sale estándar

## 5. Smoke no regresión

- [ ] Factura PDF
- [ ] Compra o albarán PDF
- [ ] Logs sin QWebException nueva

## 6. Post-instalación (24–48 h)

- [ ] Usuarios informados (Diseño vs estándar)
- [ ] Registro de ejecución completado
- [ ] Monitoreo sin incidentes críticos

## Rollback (si falla)

```bash
docker exec hellenia-prod-odoo-1 odoo shell -d hellenia_prod --no-http <<'PY'
env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()
env.cr.commit()
PY
docker restart hellenia-prod-odoo-1
```

Emergencia: `restore-hellenia-prod.sh <backup_timestamp>`

---

| Campo | Valor |
|-------|-------|
| Fecha | _pendiente_ |
| Ejecutado por | _pendiente_ |
| Autorizado por | _pendiente_ |
| Resultado | _pendiente_ |

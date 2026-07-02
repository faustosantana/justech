# Go-Live — Plan Maestro

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Fase:** 10 — Preparación completa para Go-Live  
**URL objetivo:** https://odoo.hellenia.cloud  
**Estado:** **PREPARADO EN DOCUMENTACIÓN — GO-LIVE NO EJECUTADO**

---

## 1. Resumen

| Fase previa | Estado |
|-------------|--------|
| MVP + Hardening | ✅ |
| Parametrización Fase 8 | ✅ |
| UAT Fase 9 | ✅ APTO PARA PILOTO |
| Fase 10 preparación | ✅ En curso |

**Objetivo Fase 10:** Dejar un checklist ejecutable donde el Go-Live consista únicamente en pasos previamente certificados.

**Regla:** No se ejecutó Go-Live. `odoo-pecv` (Odoo 18) sigue operativo sin cambios.

---

## 2. Resultado por bloque

| Bloque | Descripción | Estado |
|--------|-------------|--------|
| 1 | Auditoría infraestructura | PASS CON OBSERVACIONES |
| 2 | Producción Odoo 19 (plantilla) | PASS CON OBSERVACIONES |
| 3 | Licencia Enterprise | PASS CON OBSERVACIONES |
| 4 | Seguridad | PASS CON OBSERVACIONES |
| 5 | Datos maestros (procedimientos) | PASS |
| 6 | Plan migración | PASS CON OBSERVACIONES |
| 7 | Go-Live checklist | PASS |
| 8 | Plan rollback | PASS |
| 9 | Monitoreo | PASS CON OBSERVACIONES |
| 10 | Soporte post Go-Live | PASS |

**Global:** PASS CON OBSERVACIONES

---

## 3. Backups Fase 10 (triple)

| Ambiente | Timestamp | Verificado |
|----------|-----------|------------|
| DEV | `2026-06-30_1421` | ✅ |
| TEST | `2026-06-30_1421` | ✅ |
| Producción `odoo-pecv` | `2026-06-30_1421` | ✅ |

**Evidencia:** `evidence/phase10-backups-manifest.json`

```bash
./scripts/run-phase10-go-live-prep.sh
```

---

## 4. Arquitectura objetivo

```
                    Internet
                        │
                   Traefik (LE)
                        │
         ┌──────────────┼──────────────┐
         │              │              │
   dev.hellenia    test.hellenia   odoo.hellenia
         │              │              │
   hellenia-dev    hellenia-test   hellenia-prod (futuro)
   Odoo 19 EE      Odoo 19 EE      Odoo 19 EE
         │              │              │
   hellenia_dev    hellenia_test   hellenia_prod

   odoo-pecv (Odoo 18 legacy) — sin cambios hasta corte
```

---

## 5. Documentación Fase 10

| Documento | Propósito |
|-----------|-----------|
| [GO_LIVE_MASTER_PLAN.md](GO_LIVE_MASTER_PLAN.md) | Este documento |
| [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md) | Despliegue stack prod |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Checklist ejecutable |
| [ROLLBACK_PLAN.md](ROLLBACK_PLAN.md) | Rollback completo |
| [MIGRATION_PLAN.md](MIGRATION_PLAN.md) | Migración ordenada |
| [BACKUP_AND_RECOVERY_PLAN.md](BACKUP_AND_RECOVERY_PLAN.md) | Backup/recuperación |
| [PRODUCTION_INFRASTRUCTURE_REPORT.md](PRODUCTION_INFRASTRUCTURE_REPORT.md) | Auditoría infra |
| [ENTERPRISE_LICENSE_AUDIT.md](ENTERPRISE_LICENSE_AUDIT.md) | Licencia EE |
| [POST_GO_LIVE_SUPPORT_PLAN.md](POST_GO_LIVE_SUPPORT_PLAN.md) | Operación post corte |
| [GO_LIVE_EXECUTIVE_SUMMARY.md](GO_LIVE_EXECUTIVE_SUMMARY.md) | Certificación final |

---

## 6. Clasificación proyecto

**APTO PARA GO-LIVE CON OBSERVACIONES**

El Go-Live **no** debe ejecutarse hasta:
1. Aprobación explícita Hellenia / Justech
2. Ejecución checklist [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
3. Cierre observaciones P0 (router Traefik, licencia PROD, SMTP, usuarios)

---

## 7. Restricciones respetadas

| Restricción | Cumplimiento |
|-------------|--------------|
| No Go-Live ejecutado | ✅ |
| No modificar producción actual | ✅ |
| No migrar usuarios reales | ✅ |
| No importar datos reales | ✅ |
| No cambiar DNS productivo | ✅ |
| No activar stack producción | ✅ |

---

**Detenido.** Esperando aprobación explícita para ejecutar Go-Live.

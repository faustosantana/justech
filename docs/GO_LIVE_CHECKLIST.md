# Go-Live Check — Matriz Fase 12

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Referencia operativa:** [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)

---

## Matriz PASS / PASS CON OBS / FAIL

| Área | Criterio | Estado | Evidencia / Nota |
|------|----------|--------|------------------|
| **Infraestructura** | VPS, disco, RAM, Traefik DEV/TEST | PASS CON OBS | Sin swap; prod router pendiente |
| **Usuarios** | Roles ROLE_MATRIX en prod | FAIL | Plantilla lista; no creados |
| **SMTP** | Envío real corporativo | FAIL | Pendiente Hellenia |
| **NCF** | Rangos DGII activos | FAIL | Solo tipos documento; sin rangos reales |
| **Empresa** | RNC, dirección, contacto | **PASS** | `133621282` verificado |
| **Contabilidad** | Plan RD, diarios, ITBIS | **PASS** | `l10n_do` + journals |
| **Inventario** | Módulo + categorías Fase 8 | **PASS** | `stock` instalado |
| **Ventas** | `sale` + equipo Ventas Hellenia | **PASS** | |
| **Compras** | `purchase` + bridge stock | **PASS** | |
| **Localización Justech** | MVP 3 módulos | **PASS** | PHASE6 diseño validado |
| **Backups** | Triple + script prod | **PASS** | `backup-hellenia-prod.sh` plantilla |
| **Rollback** | Plan documentado | **PASS** | ROLLBACK_PLAN.md |
| **DNS** | `odoo.hellenia.cloud` | PASS CON OBS | Sin cambio (regla Fase 12) |
| **SSL** | Let's Encrypt prod | FAIL | Router prod no activo |
| **Licencia** | EE en `hellenia_prod` | FAIL | No registrada (regla Fase 12) |
| **Idioma** | `es_DO` operativo | **PASS** | Fase 11 aplicada |
| **Datos prueba** | Sin pilotos en prod path | PASS CON OBS | Prod = BD nueva limpia |
| **Monitoreo** | Estrategia + logs | PASS CON OBS | Alertas no implementadas |

---

## Conteo

| Estado | Cantidad |
|--------|:--------:|
| PASS | 9 |
| PASS CON OBS | 5 |
| FAIL | 5 |

**FAIL esperados** — todos requieren Go-Live o entregables cliente; no son defectos de desarrollo.

---

## Condición para convertir FAIL → PASS

| FAIL | Acción |
|------|--------|
| Usuarios | Importar `users_import_template.csv` completado |
| SMTP | Configurar según SMTP_CONFIGURATION.md |
| NCF | Cargar rangos según NCF_CONFIGURATION.md |
| SSL | Activar router Traefik post-validación interna |
| Licencia | Registrar código EE solo en `hellenia_prod` |

---

Ver [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) para certificación completa.

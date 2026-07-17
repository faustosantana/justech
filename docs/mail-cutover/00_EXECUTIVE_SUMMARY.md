# 00 — Resumen ejecutivo Pre-Cutover Mail Multiempresa

**Fecha:** 2026-07-17  
**Modo:** SOLO LECTURA — Producción **NO** modificada  
**Dominio Prod:** `justgroup.app` / `31.97.6.178` / DB `justech` / servicio `odoo`

## Veredicto

**GO PARA DESPLIEGUE: NO**

Producción **no** está alineada con el estado validado en DEV. El cutover no puede ejecutarse “tal cual” sin un paso previo de **bump de versión del módulo** y un plan de datos (aliases + templates) bajo ventana controlada.

## Hallazgos críticos

1. **Colisión de versión `19.0.1.1.0`:** Prod ya reporta `justech_mail_outgoing_policy` 19.0.1.1.0 en DB y filesystem, pero el código en disco **no** incluye el P1 company-first (`res_company.py`, `helpdesk_team.py`, migraciones, tests, `depends: helpdesk`). Un `-u` con la misma versión **no re-ejecutará** `migrations/19.0.1.1.0/post-migrate.py`.
2. **4 aliases Helpdesk cruzados** (JUSTECH/Omni/PlugSafe → `just-offices.com`).
3. **Hardcodes Helpdesk** templates 72/80/81/82 → `asistencia@justech.do`.

## Riesgos (conteo)

| Severidad | Cantidad |
|---|---|
| Críticos | **3** |
| Altos | **2** |
| Medios | **2** |
| Bajos | **1** |

## Confirmaciones

- Producción identificada: PASS  
- Fingerprint: generado  
- DEV vs PROD: comparado  
- SMTP / Helpdesk / Alias / Templates: auditados (read-only)  
- Cutover / Rollback / Smoke: documentados (no ejecutados)

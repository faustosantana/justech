# 07 — Cutover Plan (NO EJECUTAR)

## Pre-requisito bloqueante

1. **Bump módulo a `19.0.1.2.0`** (o superior) en el artefacto a desplegar, con `migrations/19.0.1.2.0/post-migrate.py` que reutilice la lógica de alineación de aliases + templates (porque 19.0.1.1.0 ya está marcada en Prod).
2. Autorización expresa por escrito.

## Ventana estimada

- **60–90 minutos** (backup + deploy + upgrade + smoke)
- Preferible: fuera de horario pico Helpdesk/Ventas

## Backups necesarios (antes de tocar Prod)

1. `pg_dump -Fc justech`
2. Filestore `justech`
3. Copia módulo `justech_mail_outgoing_policy` actual
4. Restore test PASS en copia / staging si existe

## Orden exacto (futuro)

1. Congelar cambios mail en Prod  
2. Backup + restore test  
3. Desplegar código **19.0.1.2.0** a `/usr/lib/odoo/custom-addons/justech_mail_outgoing_policy`  
4. `odoo -u justech_mail_outgoing_policy --stop-after-init` (ventana)  
5. Verificar aliases alignment = 0 mismatches  
6. Verificar templates 72–82 sin hardcode  
7. Smoke test 4 empresas (ver 09)  
8. Monitoreo logs SMTP 30–60 min  

## Tiempo estimado por paso

| Paso | Min |
|---|---|
| Backup | 15–25 |
| Deploy código | 5 |
| Upgrade módulo | 5–15 |
| Smoke 4 empresas | 20–30 |
| Buffer/monitor | 15 |

**Total:** ~60–90 min

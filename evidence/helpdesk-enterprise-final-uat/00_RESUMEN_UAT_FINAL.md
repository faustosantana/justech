# UAT FINAL HELPDESK ENTERPRISE — DEV

**Resultado:** PASS  
**Fecha UTC:** 2026-07-16  
**Entorno:** `erp.justech.do` / host `207.244.242.58` / DB `justech_dev` / servicio `odoo-dev`  
**SMTP:** Neutralization → `localhost:1025` (mail-sink)  
**Producción:** no modificada  

## Candidato Git

| Campo | Valor |
|---|---|
| Rama | `feature/helpdesk-enterprise-config` |
| Commit completo | ver `RELEASE.txt` tras push (base `685cf749407c97b5ff6ab423673ce23861a8a60c` + commit UAT) |
| Hellenia | 0 referencias |
| Alcance | evidence + scripts helpdesk únicamente |

## Fase 0

- Backup: `/opt/odoo-backups/helpdesk-final-uat-dev-20260716_122538/`
- PG dump Fc ~51M + filestore ~471M + exports
- Restore test: **PASS** (468 tickets = 468)
- Baseline: tickets 468 / ratings helpdesk 67 / mail 451 / teams 6 / stages 8

## Matriz componentes (Fase 1)

| Componente | Existe | Activo | Uso | Cambio |
|---|---|---|---|---|
| Helpdesk Enterprise | Sí | installed | Tickets/equipos/etapas | Config |
| Customer Ratings / rating | Sí | use_rating en equipos ops | Encuesta | Activar ops |
| Plantilla 74 rating | Sí | Sí | Solo Cerrado | Asignar stage 8 |
| Plantilla 82 resuelto | Sí | Sí | Sin /rate/ | Conservar |
| Plantilla 73 cerrado | Sí | Sí | Conservada | Sin cambio |
| Cron `helpdesk.ir_cron_auto_close_ticket` | Sí | Sí | Resuelto→Cerrado 2 días | Activar/config team |
| Automation 14 reopen | Sí | Sí | Cliente responde en Resuelto → En progreso | Conservar |
| Automation 15 digest | Sí | Sí | Recordatorio agrupado | Mejorar código |
| Automation 11 cierre Esperando cliente | Sí | Sí | Distinto (stage 6, 4 días) | No duplica Resuelto |
| Nuevos modelos | No | — | — | 0 |
| Nuevos cron | No | — | Reutiliza Enterprise | 0 |

## Equipos (Fase 2)

| Empresa | Equipo | use_rating | Acción |
|---|---|---|---|
| JUSTECH | Soporte Justech | True | Operativo |
| JUSTECH | Atención al cliente | True | Operativo |
| Just Office | Atención al cliente | True | Operativo |
| PlugSafe | Atención al cliente | True (3 días) | Operativo |
| Omni | Atención al cliente | True | Operativo |
| JUSTECH | Cotizaciones / Ventas | **False** | Sin encuesta (alias inactivo, 0 miembros) |

## UAT (SAVEPOINT+ROLLBACK)

| Caso | PASS |
|---|---|
| 1 Resuelto sin encuesta | Sí (tmpl 82, ratings 0) |
| 2 Cerrado manual → rating + /rate/ | Sí (tmpl 74, ratings 1) |
| 3 Autoclose 48h | Sí |
| 4 Respuesta cliente → En progreso | Sí (automation 14) |
| 5 Sin segundo rating/token | Sí |
| 6 Sin email → no encolar inválido | Sí |
| Digest 1 correo/empresa (no 1/ticket) | Sí (4 empresas) |
| Multiempresa 4/4 | Sí |
| Regresión tickets/ratings delta 0 | Sí |
| Portal → Cerrado | Sí |
| SMTP sink localhost | Sí |

## Recordatorio agrupado

- **Un correo por empresa** (no mezclar compañías).
- Asunto: `Tickets pendientes de seguimiento — [Fecha] — [Empresa]`
- Resumen + tabla completa + botón ABRIR HELPDESK
- Destinatarios: miembros del equipo + `helpdesk.group_helpdesk_manager` de la compañía (sin hardcode)

## Rollback

Restaurar dump/filestore del backup `helpdesk-final-uat-dev-20260716_122538` o revertir config teams/stages/action 1391.

## Capturas

Ver `screenshots/` (01–09).

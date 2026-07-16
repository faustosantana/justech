# Helpdesk Enterprise — Configuración profesional (DEV)

**Entorno:** `erp.justech.do` / `justech_dev` (`207.244.242.58`)  
**Producción:** no modificada  
**Backup DEV:** `/opt/odoo-backups/helpdesk-enterprise-config-dev-20260716_120058/`  
**Fecha:** 2026-07-16

## Principio

Reutilizar Odoo Enterprise Helpdesk + Customer Ratings. Sin modelos nuevos, sin cron nuevos, sin asistentes nuevos, sin sistemas de correo nuevos.

## Auditoría previa → qué existía / qué faltaba

| Capacidad | Estado previo | Acción |
|---|---|---|
| Customer Ratings (`use_rating`) | Off en equipos | Activar en todos los equipos |
| Plantilla `helpdesk.rating_ticket_request_email_template` (id 74) | Activa, sin stage | Asignar solo a **Cerrado** |
| Stage Resuelto template | Confirmación resuelto (82) | Mantener (sin encuesta) |
| Auto-close Enterprise (`auto_close_ticket` + cron `helpdesk.ir_cron_auto_close_ticket`) | Inactivo / mal apuntado | Activar; `from_stage=Resuelto` → `to_stage=Cerrado`; `auto_close_day=2` (48h) |
| Automated Action 15 (recordatorio) | Existía | Mejorar código a digest único + tabla |
| Automated Action 14 (reabrir) | Existía | Conservar |
| Nuevos modelos / cron / mail systems | — | **No crear** |

## Configuración aplicada (DEV)

### Flujo

Nuevo → Asignado/En proceso → Resuelto → (espera `auto_close_day` días) → Cerrado → encuesta (template 74)

### Stages

- **Resuelto** (4): `fold=False`, template 82 (sin `/rate/`)
- **Cerrado** (8): `fold=True`, template **74** (encuesta)
- **Cancelado** (5): `fold=True`, sequence > Cerrado (portal cierra a Cerrado primero)

### Teams

- `use_rating=True`
- `auto_close_ticket=True`, `from_stage_ids=[Resuelto]`, `to_stage_id=Cerrado`
- `auto_close_day=2` (48h), excepto PlugSafe (company 2 / team 4) = 3 días
- Stage Cerrado añadido a todos los equipos

### Cron

- `helpdesk.ir_cron_auto_close_ticket` **activado** (Enterprise nativo)

### Recordatorio

- Automation 15 + server action 1391: un solo correo digest a `helpdesk.group_helpdesk_manager` (`user_ids`), tabla con columnas pedidas + botón Abrir Helpdesk

## UAT (SAVEPOINT + ROLLBACK) — PASS

| Caso | Resultado |
|---|---|
| 1 Resolver → no encuesta | PASS |
| 2 Cerrar → template 74 | PASS |
| 3 Auto-close 48h → Cerrado | PASS |
| 4 Ticket pendiente → recordatorio | PASS |
| 5 15 tickets → 1 correo | PASS |
| 6 Multiempresa | PASS |
| 7 Portal → Cerrado | PASS |
| 8 Rollback | PASS |

## Rollback

1. Restaurar dump del backup `helpdesk-enterprise-config-dev-20260716_120058`.
2. O revertir: `use_rating=False`, quitar template 74 de Cerrado, desactivar cron auto-close, restaurar código previo de action 1391.

## Producción

**No desplegado.** Requiere aprobación explícita. Aplicar el mismo checklist de configuración (sin código de módulo nuevo obligatorio).

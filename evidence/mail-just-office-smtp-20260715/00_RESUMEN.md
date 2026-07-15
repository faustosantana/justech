# Just Office SRL — correo saliente multiempresa (2026-07-15)

## Declaración (8 puntos)

1. Extender política From/Reply-To multiempresa + `from_filter` Just Office.
2. Misma lógica que Justech; From Just Office = `notificaciones@just-offices.com`.
3. Riesgo bajo; Justech SMTP no modificado.
4. Backup: `/opt/odoo-backups/mail-just-office-smtp-20260715_232800/`
5. Rollback: restaurar `from_filter` id 12; quitar entrada Just Office del JSON o `outgoing_policy_enabled=False`.
6. Archivos: `custom/justech_mail_outgoing_policy/**` únicamente.
7. Módulo: `justech_mail_outgoing_policy` 19.0.1.1.0
8. ~45–60 min

## Configuración aplicada

### SMTP (Producción `justech`)

| ID | Nombre | Usuario | from_filter | active | Cambio |
|---|---|---|---|---|---|
| 11 | Notificaciones | `notifications@justech.do` | `justech.do` | t | **Sin cambio** |
| 12 | SMTP Just Office | `notificaciones@just-offices.com` | `just-offices.com` | t | `from_filter` ampliado a dominio |

### Política

- Parámetro JSON `justech_mail.company_policies` con JUSTECH + Just Office.
- Selección: `record_company_id` → documento → alias domain → From.
- SMTP: selección nativa Odoo por `from_filter` tras reescribir From.

## Pruebas (destinatario interno `fausto@justech.do`)

| Caso | mail id | From resultante | Reply-To | state |
|---|---|---|---|---|
| Just Office SRL + usuario fausto@ | 2658 | `Notificaciones Just Office <notificaciones@just-offices.com>` | `Fausto Santana <fausto@justech.do>` | **sent** |
| JUSTECH S.R.L. + usuario fausto@ | 2659 | `Notificaciones Justech <notifications@justech.do>` | `Fausto Santana <fausto@justech.do>` | **sent** |

SMTP #12 `test_smtp_connection`: **PASS**

## Confirmaciones

- Justech From sigue siendo `notifications@justech.do`.
- SMTP #11 intacto (user/filter/auth).
- Plug Safe / Omni no tocados (SMTP 14 sigue inactivo).
- `justech_managed_services` **no modificado** (worktree aislado).
- Sin secretos en evidencias.

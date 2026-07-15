# Justech Mail Outgoing Policy

## Objetivo

Evitar `554 5.2.252 SendAsDenied` en Microsoft 365 cuando Odoo autentica SMTP con `notifications@justech.do` pero el encabezado **From** es un buzón de usuario.

## Política

| Encabezado | Valor |
|---|---|
| **From** | `Notificaciones Justech <notifications@justech.do>` |
| **Reply-To** | Correo del usuario/partner que generó el mensaje |

## Parámetros del sistema

| Clave | Default |
|---|---|
| `justech_mail.outgoing_policy_enabled` | `True` |
| `justech_mail.force_from` | `Notificaciones Justech <notifications@justech.do>` |
| `justech_mail.apply_domains` | `justech.do` |

Contexto para omitir: `justech_mail_skip_outgoing_policy=True`.

## Alcance

- Solo correo saliente (`mail.mail.send`).
- No toca NCF, e-CF, plantillas ni cola histórica.
- Dominios fuera de `apply_domains` (ej. `just-offices.com`) no se reescriben.

## Rollback

1. Desactivar: `justech_mail.outgoing_policy_enabled = False`
2. O desinstalar / archivar el módulo.

# Justech Mail Outgoing Policy

## Objetivo

Evitar `554 5.2.252 SendAsDenied` en Microsoft 365 cuando el SMTP autentica
con un buzón de notificaciones pero el encabezado **From** es un buzón de usuario.

## Política por empresa

| Empresa | From | Reply-To |
|---|---|---|
| JUSTECH S.R.L. | `Notificaciones Justech <notifications@justech.do>` | Usuario originador |
| Just Office SRL | `Notificaciones Just Office <notificaciones@just-offices.com>` | Usuario originador |

Selección de política (en orden):

1. `mail.message.record_company_id`
2. `company_id` del documento (`model` / `res_id`)
3. `record_alias_domain_id`
4. Dominio del From original
5. Dominio del usuario creador (solo si no hay ambigüedad)

El servidor SMTP se selecciona con el `from_filter` de `ir.mail_server`
después de reescribir el From (mismo mecanismo Odoo nativo).

## Parámetros

| Clave | Uso |
|---|---|
| `justech_mail.outgoing_policy_enabled` | On/off global |
| `justech_mail.company_policies` | JSON multiempresa (preferido) |
| `justech_mail.force_from` / `apply_domains` | Legado Justech (compat) |

Contexto para omitir: `justech_mail_skip_outgoing_policy=True`.

## Escalar (Plug Safe / Omni)

Agregar un objeto al JSON `justech_mail.company_policies` y un
`ir.mail_server` activo con `from_filter` del dominio. Sin deploy de código.

## Rollback

1. `justech_mail.outgoing_policy_enabled = False`
2. O quitar la entrada Just Office del JSON.

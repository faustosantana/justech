# Política permanente From/Reply-To — Producción PASS

Fecha: 2026-07-15 22:54 UTC

## Despliegue

| Campo | Valor |
|---|---|
| Host | `justgroup.app` / `31.97.6.178` |
| DB | `justech` |
| Módulo | `justech_mail_outgoing_policy` **installed** `19.0.1.0.0` |
| Backup | `/opt/odoo-backups/mail-outgoing-policy-install-20260715_225343/` (`justech.dump.fc` + código + ROLLBACK.md) |
| Servicio | `odoo` **active** (reinicio controlado post-install) |

## Prueba interna

| Campo | Valor |
|---|---|
| mail id | 2653 |
| Destinatario | `fausto@justech.do` |
| Before From | `Fausto Santana <fausto@justech.do>` |
| Before Reply-To | `OdooBot <catchall@justech.do>` |
| After From | `Notificaciones Justech <notifications@justech.do>` |
| After Reply-To | `Fausto Santana <fausto@justech.do>` |
| state | **sent** (SMTP server #11) |

## Cola

| state | count |
|---|---|
| exception | 366 (anteriores al 14 jul, sin tocar) |
| sent | 3 |
| cancel | 1 |

## Confirmaciones

- NCF / e-CF / ventas / facturación / Helpdesk: **código no modificado** (solo módulo mail nuevo).
- Secretos: no en Git.
- Rollback rápido: `justech_mail.outgoing_policy_enabled=False`.

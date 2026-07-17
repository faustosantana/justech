# 05 — Template Audit (PROD)

## Literales con `@`

| id | model | email_from |
|---|---|---|
| 45 | iap.account | `iap@odoo.com` (Odoo IAP) |
| 72 | helpdesk.ticket | `Soporte Justech <asistencia@justech.do>` |
| 80 | helpdesk.ticket | idem |
| 81 | helpdesk.ticket | idem |
| 82 | helpdesk.ticket | idem |

## Helpdesk dinámicos (aún alias-first)

| id | email_from |
|---|---|
| 73 | `team_id.alias_email_from or company...` |
| 74 | `team_id.alias_email_from or company...` |

## ¿Prod = DEV?

**NO.**

DEV: 72/73/74/80/81/82 usan `company_id.justech_mail_notification_from` (company-first).  
PROD: hardcodes + alias-first en 73/74.

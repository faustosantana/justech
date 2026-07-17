# 03 — Política de templates

## Antes

Templates 72/80/81/82: hardcode `Soporte Justech <asistencia@justech.do>`.  
Templates 73/74: preferían `team.alias_email_from` (podía ser dominio ajeno).

## Después

Todos usan:

```text
{{ (object.company_id.justech_mail_notification_from
   or object.company_id.email_formatted
   or object.user_id.email_formatted
   or user.email_formatted) }}
```

Campo computado `justech_mail_notification_from` deriva del helper company-first.

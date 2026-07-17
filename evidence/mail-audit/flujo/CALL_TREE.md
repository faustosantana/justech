# Árbol de llamadas — Helpdesk → Cliente (DEV)

```
helpdesk.ticket (company_id, team_id)
  │
  ├─ mail.template.render / _generate_template
  │     email_from ← team.alias_email_from | hardcode | company.email
  │     módulo: mail (core) + datos mail.template
  │
  ├─ mail.thread.message_post / _notify_thread_by_email
  │     crea mail.message
  │     Reply-To ← helpdesk.ticket._notify_get_reply_to → team alias
  │     módulos: mail + helpdesk (Enterprise)
  │
  ├─ mail.mail.create (desde notification)
  │     email_from / reply_to heredados del message
  │
  ├─ mail.mail.send
  │     └─ justech_mail_outgoing_policy.MailMail.send
  │           └─ _justech_apply_outgoing_policy
  │                 └─ _justech_policy_applies  (DEV 19.0.1.0.0)
  │                       aplica solo si From/user domain ∈ justech.do
  │
  └─ ir.mail_server._find_mail_server(email_from)
        DEV: Neutralization localhost:1025 (único active)
        Prod: from_filter por dominio del From
```

## Punto de fallo

Entre `team.alias_email_from` (@just-offices.com en team JUSTECH id=1)  
y `_justech_policy_applies` (no reescribe dominios ajenos).

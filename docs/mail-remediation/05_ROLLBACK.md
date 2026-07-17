# 05 — Rollback

## Cuándo detener

Cualquier correo con empresa/logo/SMTP/Reply-To/alias/template incorrectos, o regresión Helpdesk/CRM/Ventas.

## Procedimiento DEV

1. `systemctl stop odoo-dev`
2. Restaurar dump:  
   `/opt/odoo-dev/backups/mail-remediation-p1-20260717_211909/justech_dev.dump`
3. Restaurar filestore del mismo backup
4. Restaurar módulo desde `.../modules/justech_mail_outgoing_policy`
5. `systemctl start odoo-dev`
6. **No improvisar** nuevas correcciones encima del fallo

## Kill switch sin restore

```text
justech_mail.outgoing_policy_enabled = False
```

(solo desactiva rewrite; no revierte aliases/templates)

# 01 — Arquitectura del sistema de correo (DEV)

## Entorno auditado

| Campo | Valor |
|---|---|
| Host | `vmi3364393` / `207.244.242.58` |
| Dominio | `erp.justech.do` |
| Base | `justech_dev` (PostgreSQL `localhost:5434`) |
| Servicio | `odoo-dev` (active) |
| Conf | `/opt/odoo-dev/conf/odoo-dev.conf` |
| addons_path | `/usr/lib/python3/dist-packages/odoo/addons`, `/usr/lib/odoo/enterprise`, `/usr/lib/odoo/custom-addons`, `/opt/odoo-dev/custom-addons/justgroup/custom_addons` |
| data_dir / filestore | `/opt/odoo-dev/data` → `filestore/justech_dev` |
| Repositorio local | `/Users/faustosantana/Projects/jaios-mail-just-office` |
| Rama | `feature/mail-just-office-smtp` |
| Commit | `f74f2b7c45f01da3aa7f501c1fe4091dac4921e3` |
| Sink SMTP DEV | `odoo-dev-mail-sink` → `localhost:1025` (ir.mail_server id=15 Neutralization) |

**Producción (`justgroup.app` / `31.97.6.178`) NO fue modificada.**

## Módulos relevantes

| Área | Módulos |
|---|---|
| Mail core | `mail` (Odoo) |
| Helpdesk | `helpdesk` (Enterprise) — **no** existe `justech_helpdesk` |
| Política salida | `justech_mail_outgoing_policy` **19.0.1.0.0** en DEV; worktree tiene **19.0.1.1.0** |
| Justech custom | `justech_*` bajo `custom_addons` |
| Just Office | sin módulo propio de mail; identidad vía `res.company` id=3 + dominio `just-offices.com` |

## Flujo canónico Helpdesk → Cliente

```
Usuario / cron / portal
        ↓
helpdesk.ticket (company_id, team_id)
        ↓
mail.template (email_from Jinja / hardcode)
        ↓
mail.thread.message_post / _notify_thread
        ↓
mail.message (email_from, reply_to, record_company_id, alias_domain)
        ↓
mail.mail (email_from, reply_to)  ← justech_mail_outgoing_policy.send()
        ↓
ir.mail_server._find_mail_server(from_filter ↔ From)
        ↓
SMTP (DEV: Neutralization :1025)
        ↓
Cliente
```

## Decisiones por capa (resumen)

Ver `04_HELPDESK_AUDIT.md` y `06_ROOT_CAUSE.md` para evidencia detallada.

| Paso | Quién decide | Compañía típica |
|---|---|---|
| Ticket | `helpdesk.ticket.company_id` ← team | documento |
| From plantilla | `team.alias_email_from` o hardcode | **dominio del alias** (puede ≠ company) |
| Reply-To notify | Helpdesk `_notify_get_reply_to` → alias equipo | alias |
| Policy rewrite | `_justech_policy_applies` (v1.0.0) | solo si dominio ∈ `justech.do` |
| SMTP | `from_filter` vs From | en Prod: servidor del dominio From |
| Logo layout | `record.company_id` | documento (puede divergir del From) |

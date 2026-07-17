# 00 — Resumen ejecutivo — Auditoría forense correo multiempresa

**Fecha:** 2026-07-17  
**Ámbito:** SOLO DEV (`justech_dev` / `erp.justech.do`)  
**Producción modificada:** NO  
**Cambios funcionales / código / SMTP / plantillas / aliases:** NINGUNO

## Problema

Tickets Helpdesk de **JUSTECH** pueden generar correos con identidad de **Just Office** (dominio/remitente).

## Causa raíz (confirmada con evidencia)

**Configuración de alias Helpdesk incorrecta + política de salida incompleta en DEV.**

1. El equipo JUSTECH **«Atención al cliente» (team id=1)** tiene alias `customer-care@just-offices.com` (dominio Just Office), mientras la empresa JUSTECH usa `justech.do`.
2. Las plantillas Helpdesk (p. ej. id 73) usan `object.team_id.alias_email_from` como **From**.
3. Reproducción SAVEPOINT: ticket JUSTECH en team 1 → From renderizado = `"OdooBot" <customer-care@just-offices.com>`.
4. En DEV, `justech_mail_outgoing_policy` **19.0.1.0.0** solo reescribe From si el dominio está en `justech.do`; un From `@just-offices.com` **no se corrige** → el cliente ve Just Office.

## Componente / método / archivo responsables

| Rol | Detalle |
|---|---|
| Disparador de identidad errónea | `helpdesk.team` alias domain mismatch (datos) |
| Quién pone el From del template | `mail.template` Helpdesk `email_from` → `team.alias_email_from` |
| Quién no corrige en DEV | `justech_mail_outgoing_policy` `MailMail._justech_apply_outgoing_policy` / `_justech_policy_applies` (v19.0.1.0.0) |
| Archivo código (DEV) | `/opt/odoo-dev/.../justech_mail_outgoing_policy/models/mail_mail.py` |
| Archivo código (repo worktree 1.1.0) | `custom/justech_mail_outgoing_policy/models/mail_mail.py` |

## Tipo de problema

**Principalmente configuración (aliases)**, amplificado por **código/política** que no fuerza company_id sobre alias, y por **plantillas hardcodeadas** JUSTECH.

## Solución recomendada (NO implementar aún)

1. Realinear aliases de cada `helpdesk.team` al `alias_domain` de su `company_id`.
2. Endurecer política: si hay `record_company_id` / `ticket.company_id`, **no** dejarse llevar por alias domain.
3. Quitar hardcodes `asistencia@justech.do` en plantillas multiempresa.
4. Alinear DEV a política multiempresa 19.0.1.1.0 tras UAT.

## Restore test

**PASS** — backup `/opt/odoo-dev/backups/mail-forensic-audit-20260717_185843`

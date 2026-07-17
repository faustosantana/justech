# 00 — Resumen remediación mail multiempresa (P1)

**Ámbito:** SOLO DEV (`justech_dev`)  
**Producción:** NO modificada  
**Fecha:** 2026-07-17  
**Módulo:** `justech_mail_outgoing_policy` **19.0.1.1.0**

## Resultado

**PASS** — identidad de correo gobernada por `company_id` del documento.

## Cambios

1. Aliases Helpdesk alineados a `company.alias_domain_id`.
2. Política **company-first** vía helper `res.company._get_company_mail_identity()`.
3. Hardcodes `asistencia@justech.do` eliminados en templates 72/73/74/80/81/82.
4. Validación: alias de team ≠ dominio de company → `ValidationError` / bloqueo de envío.
5. Políticas ICP para JUSTECH, Just Office, PlugSafe, Omni.

## Backup

`/opt/odoo-dev/backups/mail-remediation-p1-20260717_211909` — Restore test **PASS**.

## Producción

**NO desplegar** hasta autorización expresa.

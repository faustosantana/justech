# 02 — Auditoría SMTP (DEV)

**Fuente:** `evidence/mail-audit/SQL/02_mail_servers.txt` + consulta live 2026-07-17.

## Servidores `ir.mail_server`

| id | name | smtp_host | from_filter | active |
|---|---|---|---|---|
| 6 | Exchange saliente | smtp.office365.com | fausto@justech.do | **false** |
| 7 | Correo saliente de Fausto Santana | smtp-mail.outlook.com | fausto@justech.do | **false** |
| 11 | Notificaciones | smtp.office365.com | notifications@justech.do | **false** |
| 12 | SMTP Just Office | smtp.outlook.com | administracion@just-offices.com | **false** |
| 14 | Notificaciones Plug Safe | smtp.office365.com | ventas@plugsafeservices.com | **false** |
| 15 | Neutralization | localhost:1025 | (vacío) | **true** |

## Hallazgos

1. En DEV **solo** Neutralization está activo → todo sale al sink; no se valida `from_filter` real.
2. En Prod (inventario histórico, no modificado en esta auditoría) el `from_filter` selecciona servidor por dominio del **From**.
3. Si From = `@just-offices.com` en un ticket JUSTECH, Prod elegiría **SMTP Just Office** aunque el ticket sea company_id=1.
4. `company_id` en `ir.mail_server`: columna no usada / no vinculante en este inventario (selección por `from_filter`).

## Autenticación / remitentes

- JUSTECH notifications: `notifications@justech.do`
- Just Office: `administracion@just-offices.com`
- PlugSafe: `ventas@plugsafeservices.com`

## Conclusión SMTP

SMTP **no es la causa raíz primaria** en DEV (sink único).  
Es un **amplificador en Prod**: el From incorrecto arrastra el servidor incorrecto.

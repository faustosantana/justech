# 03 — SMTP Audit (PROD, read-only)

Fuente: `evidence/mail-cutover/prod/03_smtp.txt`

| id | name | host | port | user | active | from_filter | auth | enc |
|---|---|---|---|---|---|---|---|---|
| 11 | Notificaciones | smtp.office365.com | 587 | notifications@justech.do | **t** | justech.do | outlook | starttls |
| 12 | SMTP Just Office | smtp.outlook.com | 587 | notificaciones@just-offices.com | **t** | just-offices.com | login | starttls |
| 6 | Exchange saliente | smtp.office365.com | 587 | fausto@justech.do | f | fausto@justech.do | outlook | starttls |
| 7 | Fausto Santana | smtp-mail.outlook.com | 587 | fausto@justech.do | f | fausto@justech.do | outlook | starttls |
| 14 | Notificaciones Plug Safe | smtp.office365.com | 587 | ventas@plugsafeservices.com | **f** | ventas@plugsafeservices.com | outlook | starttls |

## Comparación DEV

DEV solo tiene activo **Neutralization** `localhost:1025`.  
PROD envía a Internet real → cualquier From incorrecto durante cutover **llega al cliente**.

## Compatibilidad

- Selección por `from_filter` / dominio: compatible con company-first **si** From queda en dominio correcto.
- PlugSafe SMTP **inactivo** en Prod → riesgo si se fuerza From `@plugsafeservices.com` sin activar servidor.
- Omni: no hay servidor SMTP dedicado visible en inventario.

## company_id en ir.mail_server

Esquema Prod no usa company_id como selector (ver `03b_smtp_schema.txt`); gobierna `from_filter`.

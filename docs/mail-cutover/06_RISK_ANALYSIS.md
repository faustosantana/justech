# 06 — Risk Analysis

## Críticos (3)

1. **Version pin 19.0.1.1.0 sin código P1** → upgrade no corre post-migrate; aliases/templates quedarían sin corregir si solo se copia código y `-u` sin bump.
2. **4 aliases cruzados** en Prod live → identidad Just Office en tickets JUSTECH/Omni/PlugSafe **hoy**.
3. **Hardcodes asistencia@** en templates recibidos/resuelto.

## Altos (2)

1. **SMTP real dual activo** (Justech + Just Office) — errores de From impactan clientes reales (DEV usaba sink).
2. **PlugSafe SMTP inactive** — company-first PlugSafe puede fallar send / elegir servidor incorrecto.

## Medios (2)

1. ICP Prod sin políticas Omni/PlugSafe completas (JSON parcial vs DEV).
2. `mail.default.from=asistencia@justech.do` + catchall justech.do — sesgo JUSTECH global.

## Bajos (1)

1. Template IAP `iap@odoo.com` (igual que DEV; fuera de identidad Justgroup).

## Riesgos Prod no presentes en DEV

- Entrega real a Internet.
- Credenciales Outlook/M365 Send-As por dominio.
- Ausencia de sink / neutralization.
- Clientes reales en Helpdesk con team 1 (customer-care@just-offices.com) si se usa ese equipo.

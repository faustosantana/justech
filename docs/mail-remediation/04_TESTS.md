# 04 — Pruebas

## Automáticas

`custom/justech_mail_outgoing_policy/tests/test_company_mail_identity.py`

- Helper identity × 4 compañías
- Rewrite From por `record_company_id`
- Constraint alias cruzado
- Tickets Helpdesk × 4 compañías

## Validación ORM DEV (2026-07-17)

| Compañía | From domain | Alias domain | PASS |
|---|---|---|---|
| JUSTECH | justech.do | justech.do | Yes |
| PlugSafe | plugsafeservices.com | plugsafeservices.com | Yes |
| Just Office | just-offices.com | just-offices.com | Yes |
| Omni | solutionsomni.com | solutionsomni.com | Yes |

- Hardcodes: 0  
- Alias mismatches: 0  
- Constraint ValidationError: PASS  
- Módulos CRM/Sale/Purchase/Account/Helpdesk/Mail/Portal: installed

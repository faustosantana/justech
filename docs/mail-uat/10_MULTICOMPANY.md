# 10 — Multiempresa

## Identidades (`_get_company_mail_identity`)

| Company | Dominio | From | Alias domain | OK |
|---|---|---|---|---|
| JUSTECH | justech.do | notifications@justech.do | justech.do | PASS |
| PlugSafe | plugsafeservices.com | ventas@plugsafeservices.com | plugsafeservices.com | PASS |
| Just Office | just-offices.com | notificaciones@just-offices.com | just-offices.com | PASS |
| Omni | solutionsomni.com | info@solutionsomni.com | solutionsomni.com | PASS |

## Trap env.company

Active company = Just Office, documento = JUSTECH → From final `notifications@justech.do` (**PASS**).

## Matriz final

| Empresa | Helpdesk | CRM | Sales | Purchase | Invoice | Portal | Usuarios | Automatizaciones |
|---|---|---|---|---|---|---|---|---|
| JUSTECH | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| JUST OFFICE | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| PlugSafe | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Omni | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

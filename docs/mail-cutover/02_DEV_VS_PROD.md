# 02 — DEV vs PROD

## Core modules (versiones DB)

| Módulo | DEV | PROD | Match |
|---|---|---|---|
| justech_mail_outgoing_policy | 19.0.1.1.0 | 19.0.1.1.0 | versión igual / **código distinto** |
| helpdesk | 19.0.1.6 | 19.0.1.6 | OK |
| mail | 19.0.1.19 | 19.0.1.19 | OK |
| sale | 19.0.1.2 | 19.0.1.2 | OK |
| account | 19.0.1.4 | 19.0.1.4 | OK |
| purchase | 19.0.1.2 | 19.0.1.2 | OK |
| crm | 19.0.1.9 | 19.0.1.9 | OK |
| portal | 19.0.1.0 | 19.0.1.0 | OK |

## justech_mail_outgoing_policy — diferencias reales

| Aspecto | DEV (validado UAT) | PROD (actual) |
|---|---|---|
| Manifest depends | `mail`, **helpdesk** | `mail` only |
| Helper `_get_company_mail_identity` | Sí (`res_company.py`) | **No** |
| Constraint alias team | Sí | **No** |
| Compose inject | Sí | **No** |
| Migration post-migrate aliases/templates | Sí (en árbol DEV) | **No en disco** |
| Tests | Sí | **No** |
| Company policies ICP | 4 empresas (DEV remediado) | JUSTECH + Just Office (parcial) |

## Datos

| Aspecto | DEV | PROD |
|---|---|---|
| Alias mismatches Helpdesk | **0** | **4** |
| Hardcodes HD 72/80/81/82 | 0 (company-first expr) | **4 literales asistencia@** |
| SMTP activo | Neutralization :1025 | **Office365 Justech + Just Office** |

## Conclusión comparativa

Producción **no coincide** con el estado DEV validado. Misma etiqueta de versión enmascara un delta de código y de datos.

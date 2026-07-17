# Changelog — justech_mail_outgoing_policy

## 19.0.1.1.0

- Company-first outgoing identity via `res.company._get_company_mail_identity()`.
- Multi-company policies: JUSTECH, Just Office, PlugSafe, Omni.
- Helpdesk alias alignment + constraint (alias domain must match company).
- Remove hardcoded Helpdesk From templates; use company notification From.
- Block send when Helpdesk team alias belongs to another company.
- Composer injects company From from document `company_id` (never `env.company`).

## 19.0.1.0.0

- Política saliente Justech: From fijo `notifications@justech.do`, Reply-To del usuario emisor.

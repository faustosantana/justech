# Quién decide cada header / identidad

Evidencia cruzada: templates SQL, aliases SQL, policy DEV, repro JSON.

| Elemento | Quién decide | Evidencia |
|---|---|---|
| **From** (Helpdesk template 73/74) | `object.team_id.alias_email_from` | template SQL; repro rendered From |
| **From** (templates 72/80/81/82) | Hardcode `asistencia@justech.do` | template SQL |
| **From** (post-policy DEV) | `_justech_apply_outgoing_policy` si `_justech_policy_applies` | código DEV + ICP |
| **Reply-To** (notify) | Helpdesk `_notify_get_reply_to` → alias team | Enterprise helpdesk + decisions JSON |
| **Reply-To** (post-policy) | `_justech_resolve_reply_to` (usuario humano) | código DEV |
| **Sender** | Tipicamente igual / path mail; no custom Justech | core mail |
| **Return-Path** | SMTP / bounce handling Odoo | core; no audit change |
| **Company** (documento) | `helpdesk.ticket.company_id` ← team | mismatch count 0 |
| **Company** (From visible) | **No** company_id — alias domain | team 1 mismatch |
| **Logo** | Layout notification `record.company_id` | decisions JSON |
| **Nombre comercial** | `res.company` del layout vs texto From | divergencia posible |
| **Dominio** | `mail.alias_domain` del team alias | aliases SQL |
| **Layout** | mail notification + company documento | core mail |
| **Alias** | `helpdesk.team.alias_id` | aliases SQL |
| **SMTP** | `ir.mail_server` + `from_filter` vs From | SMTP SQL; DEV sink |
| **Firma** | usuario / partner signature si composer | no root del caso |
| **Reply alias** | team alias / catchall | team 6 catchall |
| **Catchall** | alias vacío + domain; ICP `mail.catchall.domain` vacío en DEV | ICP dump |

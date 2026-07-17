# 01 — Política de aliases Helpdesk

## Regla

`helpdesk.team.alias_id.alias_domain_id` **debe** ser igual a `team.company_id.alias_domain_id`.

Fuente de verdad: **company_id**, no el dominio por defecto del sistema.

## Estado DEV tras remediación

| team_id | company | alias | domain |
|---|---|---|---|
| 1 | JUSTECH | customer-care | justech.do |
| 2 | Just Office | atencion-al-cliente-justoffice-srl | just-offices.com |
| 3 | Omni | atencion-al-cliente-omni-solutions-srl | solutionsomni.com |
| 4 | PlugSafe | atencion-al-cliente-plugsafe-srl | plugsafeservices.com |
| 5 | JUSTECH | asistencia | justech.do |
| 6 | JUSTECH | (catchall) | justech.do |

## Mecanismos

- Migración `migrations/19.0.1.1.0/post-migrate.py` → `_justech_align_alias_domain()`
- Constraint `helpdesk.team._check_justech_alias_matches_company`
- Envío: si alias domain ≠ company domain → mail `state=cancel` + warning

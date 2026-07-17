# 04 — Auditoría Helpdesk

**Fuente:** `evidence/mail-audit/SQL/03_aliases_helpdesk.txt`, `08_tickets_by_team.txt`, `09_repro_results.json`

## Equipos `helpdesk.team`

| team_id | Nombre | company_id | Empresa | alias | alias_domain | ¿Match company domain? |
|---|---|---|---|---|---|---|
| 1 | Atención al cliente | 1 | JUSTECH | customer-care | **just-offices.com** | **NO** (company: justech.do) |
| 2 | Atención al cliente | 3 | Just Office | atencion-al-cliente-justoffice-srl | just-offices.com | OK |
| 3 | Atención al cliente | 4 | Omni | atencion-al-cliente-omni-solutions-srl | **just-offices.com** | **NO** (solutionsomni.com) |
| 4 | Atención al cliente | 2 | PlugSafe | atencion-al-cliente-plugsafe-srl | **just-offices.com** | **NO** (plugsafeservices.com) |
| 5 | Soporte Justech | 1 | JUSTECH | asistencia | justech.do | OK |
| 6 | Cotizaciones / Ventas | 1 | JUSTECH | (vacío) / catchall | **just-offices.com** | **NO** |

## Volumen tickets (DEV)

- Team 5 «Soporte Justech»: ~218 tickets (dominio correcto).
- Team 1 «Atención al cliente» JUSTECH: **0** tickets históricos en snapshot; **sí** reproducible al crear ticket en ese equipo.
- Mismatch `ticket.company_id` vs `team.company_id`: **0** filas.

## Alias domains globales

`mail.alias_domain` incluye `just-offices.com` como dominio usado por varios equipos de otras compañías → riesgo estructural multiempresa.

## Métodos Helpdesk (Enterprise)

| Responsabilidad | Método / campo típico |
|---|---|
| Alias del equipo | `helpdesk.team.alias_id` → `mail.alias` + `alias_domain_id` |
| From computado | `alias_email_from` |
| Reply-To en notificaciones | `helpdesk.ticket._notify_get_reply_to` → alias del team |
| Company del ticket | `company_id` (related/default desde team) |

## Cadena del bug JUSTECH → Just Office

```
team_id=1 (JUSTECH) + alias @just-offices.com
  → template email_from = alias_email_from
  → mail.message.email_from @just-offices.com
  → policy DEV 1.0.0: domain not in justech.do → NO rewrite
  → cliente ve Just Office
```

Si el ticket usa team 5, From = `asistencia@justech.do` → policy reescribe a `notifications@justech.do` → identidad JUSTECH (correcta tras política).

# 03 — Auditoría de plantillas Helpdesk

**Fuente:** `evidence/mail-audit/SQL/04_templates.txt`

## Plantillas `mail.template` modelo `helpdesk.ticket`

| id | Nombre | email_from |
|---|---|---|
| 72 | Ticket Received | **HARDCODE** `Soporte Justech <asistencia@justech.do>` |
| 73 | Ticket Closed | `team.alias_email_from or company.email_formatted or user...` |
| 74 | Ticket Rating | `team.alias_email_from or company.email_formatted or operator...` |
| 76–79 | Custom avisos | vacío (fallback mail.thread / usuario) |
| 80–82 | Copias Received / Resuelto | **HARDCODE** `Soporte Justech <asistencia@justech.do>` |

## Quién decide el From

1. **Primario (73/74):** `object.team_id.alias_email_from`  
   → identidad = **alias del equipo**, no necesariamente dominio de `company_id`.
2. **Hardcode (72/80/81/82):** siempre JUSTECH → fuga inversa (Justech en tickets Omni/PlugSafe/Just Office).
3. **Layout:** `email_layout_xmlid` vacío en estas filas → layout default mail; company del layout suele seguir `record.company_id`.

## Reply-To en plantilla

Campo `reply_to` vacío en todas las listadas → lo decide Helpdesk/mail.notify (`_notify_get_reply_to`), no la plantilla.

## Evidencia reproducción

Ticket id=790 (SAVEPOINT, rollback), team_id=1, company_id=1:

```text
template73_rendered_from = "OdooBot" <customer-care@just-offices.com>
```

Ver `evidence/mail-audit/repro/09_repro_results.json`.

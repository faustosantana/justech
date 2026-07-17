# 08 — Índice de evidencias

## Documentación

| Doc | Ruta |
|---|---|
| Resumen | `docs/mail-audit/00_EXECUTIVE_SUMMARY.md` |
| Arquitectura | `docs/mail-audit/01_MAIL_ARCHITECTURE.md` |
| SMTP | `docs/mail-audit/02_SMTP_AUDIT.md` |
| Plantillas | `docs/mail-audit/03_TEMPLATE_AUDIT.md` |
| Helpdesk | `docs/mail-audit/04_HELPDESK_AUDIT.md` |
| Multiempresa | `docs/mail-audit/05_MULTICOMPANY_AUDIT.md` |
| Causa raíz | `docs/mail-audit/06_ROOT_CAUSE.md` |
| Remediación | `docs/mail-audit/07_REMEDIATION_PLAN.md` |
| Este índice | `docs/mail-audit/08_EVIDENCE_INDEX.md` |

## Evidencia en repo

| Artefacto | Ruta |
|---|---|
| Backup path | `evidence/mail-audit/backup/BACKUP_PATH.txt` |
| Restore PASS | `evidence/mail-audit/restore/result.txt` |
| Companies / SQL exports | `evidence/mail-audit/SQL/01_companies.txt` … |
| SMTP | `evidence/mail-audit/SQL/02_mail_servers.txt` |
| Aliases Helpdesk | `evidence/mail-audit/SQL/03_aliases_helpdesk.txt` |
| Alias domains | `evidence/mail-audit/SQL/03b_alias_domains.txt` |
| Templates | `evidence/mail-audit/SQL/04_templates.txt` |
| Messages recientes | `evidence/mail-audit/SQL/05_recent_helpdesk_messages.txt` |
| Tickets por team | `evidence/mail-audit/SQL/08_tickets_by_team.txt` |
| Repro JSON | `evidence/mail-audit/repro/09_repro_results.json` |
| Código policy DEV | `evidence/mail-audit/codigo/07_mail_mail_policy_dev.py.txt` |
| Call tree / decisiones | `evidence/mail-audit/flujo/CALL_TREE.md` |
| Quién decide qué | `evidence/mail-audit/flujo/WHO_DECIDES.md` |

## Evidencia en servidor DEV

```text
/opt/odoo-dev/backups/mail-forensic-audit-20260717_185843/
  ├── pg dump + filestore + module copies
  ├── restore_test/result.txt → RESTORE_TEST=PASS
  └── exports/*.txt|json
```

## Instrumentación temporal (FASE 6)

- Reproducción vía ORM + render template + simulación `_justech_policy_applies` en SAVEPOINT con **rollback**.
- **No** se dejó logging permanente en código de producción ni DEV.
- **No** se envió correo real fuera del sink Neutralization de DEV (repro dry-run / rollback).

## Garantías

| Ítem | Estado |
|---|---|
| Producción modificada | NO |
| SMTP modificado | NO |
| Plantillas modificadas | NO |
| Aliases modificados | NO |
| Código funcional cambiado | NO |
| Correcciones implementadas | NO |

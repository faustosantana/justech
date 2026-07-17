# 16 — DO NOT TOUCH — Baselines

## Baseline Alertas NCF (congelada)

| Ítem | Valor |
|---|---|
| Commit | `aaea7f5f4730a038f005a3e6010354f9da64963a` |
| Tag | `ncf-alerts-baseline-v1` |
| Módulo / versión | `justech_l10n_do_ncf` **19.0.2.14.0** |
| Doc | `docs/releases/NCF_ALERTS_BASELINE_v1.md` |

### Superficies protegidas

- `_process_company_consolidated_alert`
- `_cron_process_ncf_range_alerts`
- `_primary_alert_user` / nota HTML Markup / consolidación por empresa
- Activity type `mail_activity_data_ncf_range_alert`
- Tests `test_ncf_alerts_consolidated_baseline.py`

### Prohibido sin proceso completo

Modificar alertas, consolidación, responsables, mails NCF, umbrales/cron/HTML de alertas.

### Esta auditoría

**No se modificó código de baseline.**  
Prod no tocada.

## Otras líneas rojas de esta fase

- No `-u` módulos
- No migraciones
- No cambios datos/secuencias/NCF/documentos
- No desactivar crons
- No cerrar actividades
- No enviar correos

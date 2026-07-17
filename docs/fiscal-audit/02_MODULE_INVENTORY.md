# 02 — Inventario técnico de módulos

## Matriz resumida

| Elemento | Módulo | Archivo / ID | Propósito | Estado | Riesgo |
|---|---|---|---|---|---|
| Manifest base | base | `__manifest__.py` 19.0.1.26.0 | Núcleo fiscal DO | activo | bajo |
| Manifest ncf | ncf | `__manifest__.py` 19.0.2.14.0 | Rangos/asignación NCF | activo | medio (dual stack) |
| Tipos comprobante | base | `justech.do.fiscal.document.type` | Catálogo B01–B17 | activo | medio (poco usado en moves) |
| Partner fiscal | base | `res.partner` inherit | RNC/padrón/defaults | activo | medio |
| Company umbrales | base | `res.company` | Alertas NCF thresholds | activo | protegido alertas |
| Rangos NCF | ncf | `justech.do.ncf.range` | Autorización/consumo | activo | medio |
| account.move NCF | ncf | `models/account_move.py` | Asignación/validación | activo | alto (vs LATAM) |
| FDP | base | `fiscal_data_provider.py` | Resolución NCF multi-fuente | activo | alto |
| Alertas consolidadas | ncf | `_process_company_consolidated_alert` | Actividad interna/empresa | **protegido** | baseline |
| Cron alertas | ncf | `ir_cron_justech_do_ncf_range_alerts` | Diario | activo | baseline |
| Cron padrón | base | `ir_cron_justech_rnc_padron_auto_update` | Hourly | **inactivo** | bajo |
| Exporters 606–623 | reports | `dgii_*_exporter.py` | DGII | activo | alto |
| Adel expire seq | l10n_do_accounting | cron 57 | Expira secuencias Adel | activo | alto interferencia |
| e-CF queue | ecf_queue | cron 85 | Cola e-CF 1min | activo | medio |
| Groups fiscal | base/fiscal_admin | security XML | Roles | activo / subpoblado | alto |
| Rules company | ncf/base/reports | ir.rule | Aislamiento | activo | medio |
| Tests baseline | ncf | `test_ncf_alerts_consolidated_baseline.py` | Regresión alertas | activo | protegido |
| hellenia_account | hellenia | withholding legacy | Paralelo retenciones | posiblemente no usado / riesgo | alto si coexiste |

## Dependencias declaradas (núcleo)

- **base:** `account`, `contacts`, `sales_team`, `l10n_do`, `l10n_do_accounting`, `mail`
- **ncf:** `justech_l10n_do_base`, `mail`, `account_debit_note`, `sale`, `purchase`, `sale_purchase`, `bi_convert_purchase_from_sales`
- **reports:** NCF + `justech_fiscal_admin` (+ stack reportes)

## Módulos instalados DEV relacionados (extracto DB)

Ver `evidence/fiscal-audit/entorno/modules_installed.txt`.

Incluye: `justech_l10n_do_*`, `justech_fiscal_admin`, `justech_ecf_*`, `l10n_do`, `l10n_do_accounting`, `l10n_do_reports`, `justech_security_ux`.

## Inventario detallado

El inventario completo de archivos/modelos/crons/tests está en el informe de exploración consolidado en esta carpeta (secciones 03–13) y en evidencia código.

**Baseline:** métodos `_process_company_consolidated_alert` / `_cron_process_ncf_range_alerts` — **NO TOCAR**.

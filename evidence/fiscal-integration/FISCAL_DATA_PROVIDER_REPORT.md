# Informe — Fiscal Data Provider (coexistencia Adel / Justech)

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-07-09 |
| **Módulos** | `justech_l10n_do_base` 19.0.1.7.0, `justech_l10n_do_reports` 19.0.1.15.0 |
| **Alcance** | Solo lectura — **sin migración, sin backfill, sin modificar histórico** |

## Problema detectado

El exportador 606 (y resto de reportes) leía **únicamente** `justech_do_ncf`. Las facturas operadas por **Adel** almacenan el NCF en `l10n_latam_document_number` (ej. `E310000019120`, tipo E31). El 606 reportaba «no tiene NCF» aunque la factura sí lo tenía.

## Solución

Nuevo servicio **`justech.do.fiscal.data.provider`** en `justech_l10n_do_base/services/fiscal_data_provider.py`.

Centraliza toda lectura fiscal con cadena de fallback:

| Prioridad | Capa | Campos |
|-----------|------|--------|
| 1 | Justech | `justech_do_ncf`, `justech_do_document_type_id`, `justech_do_*` |
| 2 | Adel | `l10n_do_origin_ncf`, `l10n_do_income_type`, `l10n_do_expense_type`, `l10n_do_cancellation_type` |
| 3 | l10n_latam | `l10n_latam_document_number`, `l10n_latam_document_type_id` |
| 4 | Odoo estándar | `ref`, `payment_reference`, `name` (solo si formato NCF válido) |
| 5 | — | `NULL` / vacío |

## API del Provider

| Método | Uso |
|--------|-----|
| `get_ncf()` | NCF / e-CF |
| `get_document_number()` | NCF o número documental |
| `get_document_type_prefix()` | B01, E31, … |
| `get_document_type_name()` | Etiqueta tipo comprobante |
| `get_ncf_modified()` / `get_origin_ncf()` | NC/ND |
| `get_income_type_607()` | Columna F — 607 |
| `get_expense_type_606()` | Columna D — 606 |
| `get_cancellation_type()` | 608 |
| `is_voided()` / `get_void_metadata()` | Anulaciones |
| `is_ecf()` | e-CF (prefijo E) |
| `get_foreign_*()` | 609 |
| `get_supported_sources()` | Diagnóstico (`justech`, `adel_latam`, `odoo_standard`, `none`) |

## Módulos soportados (lectura)

| Módulo | Soporte |
|--------|---------|
| `justech_l10n_do_ncf` | Campos Justech nativos |
| `l10n_do_accounting` (Adel) | `l10n_latam_*`, `l10n_do_*` |
| `l10n_latam` / `l10n_do` | Capa LatAm estándar |
| Odoo `account` | Fallback documental |

## Reportes corregidos (usan Provider exclusivamente)

| Reporte | Archivo |
|---------|---------|
| **606** | `dgii_606_exporter.py` |
| **607** | `dgii_607_exporter.py` |
| **608** | `dgii_608_exporter.py` (+ dominio Adel anulaciones) |
| **609** | `dgii_609_exporter.py` |
| **623** | `fiscal_report.py` (líneas preview) |
| Mixin compartido | `dgii_exporter_mixin.py` |
| Preview / CSV / Excel | `fiscal_report.py` |
| Bandeja revisión | `dgii_report_review.py` |

**IT-1:** no implementado (sin cambios).

## Pantallas unificadas (terminología NCF)

| Vista | Cambio |
|-------|--------|
| `account_move_fiscal_compat_views.xml` | `l10n_latam_document_number` → **NCF**; tipo → **Tipo de comprobante fiscal** |
| `justech_l10n_do_ncf/views/account_move_views.xml` | Campo `justech_do_ncf` etiquetado **NCF** |
| `dgii_report_review_views.xml` | Tipo comprobante fiscal; Factura |
| `dgii_report_pending_tray_views.xml` | Idem |
| `fiscal_report.py` (modelo línea) | `document_type` → Tipo comprobante fiscal |

## Evidencia E310000019120

**Validación local (tests):**

- `test_fiscal_data_provider.py` — lectura desde `l10n_latam_document_number`
- `test_fiscal_provider_reports.py::test_607_ecf_invoice_e310000019120` — 607 **sin error NCF**, columna D = `E310000019120`

**Validación en servidor (justech_dev, solo lectura):**

```bash
sudo -u odoo python3 /opt/odoo-dev/scripts/fiscal-provider-smoke.py E310000019120
```

Criterio PASS:
- `provider_ncf` = `E310000019120`
- `606_valid_for_ncf` = true
- `justech_do_ncf` puede seguir vacío (sin modificar factura)

## Despliegue recomendado

1. Healthcheck pre
2. Rsync `justech_l10n_do_base`, `justech_l10n_do_reports`
3. `-u justech_l10n_do_base,justech_l10n_do_reports`
4. Smoke script con NCF real
5. Validar 606/607 en UI (sin generar envío DGII)

**Rollback:** backup estabilizado DEV-2 — solo revertir módulos; datos intactos.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Campo Adel ausente en otros entornos | Provider verifica `_fields` antes de leer |
| 608 sin motivo anulación Adel | Acepta `l10n_do_cancellation_type` como alternativa |
| Prefijo tipo desde LatAm ambiguo | Fallback a primeros 3 chars del NCF |

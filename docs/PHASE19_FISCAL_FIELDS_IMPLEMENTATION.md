# Fase 19 — Implementación campos fiscales P0

**Fecha:** 2026-06-30  
**Rama:** `cursor/phase19-fiscal-fields-606-dd85`

## Objetivo

Implementar los campos fiscales mínimos (P0) detectados en Fase 17.5 para habilitar reportes DGII, comenzando por el formato 606.

## Campos implementados

| Campo | Modelo | Módulo | Estado |
|-------|--------|--------|--------|
| `justech_do_ncf` | `account.move` | `justech_l10n_do_ncf` | **Ya existía** (Fase MVP) — verificado |
| `justech_do_partner_id_type` | `res.partner` | `justech_l10n_do_base` | **Nuevo** — calculado desde RNC/Cédula |
| `justech_do_ncf_modified` | `account.move` | `justech_l10n_do_ncf` | **Nuevo** — auto en NC proveedor |
| `justech_do_dgii_line_status` | `account.move` | `justech_l10n_do_ncf` | **Nuevo** — 1=válido, 2=anulado |
| `justech_do_ncf_cancel_type` | `account.move` | `justech_l10n_do_ncf` | **Nuevo** — códigos 01–10 DGII |
| `dgii_withholding_code` | `hellenia.withholding.catalog` | `hellenia_account` | **Nuevo** — mapeo retenciones |

## Detalle por campo

### `justech_do_partner_id_type`

- Valores: `1` RNC (9 dígitos), `2` Cédula (11 dígitos), `3` Pasaporte (manual)
- Cálculo automático desde `vat` al crear/actualizar
- Método auxiliar: `justech_do_clean_vat()` para exportación sin separadores

### `justech_do_ncf_modified`

- NCF del documento original en notas de crédito/débito (columna F del 606)
- Se completa automáticamente desde `reversed_entry_id.justech_do_ncf`
- Complementa `justech_do_origin_ncf` (existente)

### `justech_do_dgii_line_status`

- Default `1` (válido)
- Pasa a `2` al anular NCF (`action_void_ncf`)
- Excluye líneas anuladas del exportador 606

### `justech_do_ncf_cancel_type`

- Catálogo DGII formato 608 (01–10)
- Capturado en wizard de anulación (`justech.do.ncf.void.wizard`)
- Default sugerido: `04` Corrección de información

### `dgii_withholding_code`

Códigos asignados en `sync_catalog_from_taxes`:

| Código catálogo | dgii_withholding_code |
|-----------------|----------------------|
| RET-HON-10 | 02 |
| RET-INF-ISR-10 | 02 |
| RET-ISR-2 | 03 |
| RET-ITBIS-30 | 02 |
| RET-ITBIS-100 | 03 |
| RET-INF-ITBIS-75 | 04 |
| RET-GOB-5 | 07 |

## Módulos modificados

- `custom/justech_l10n_do_base` → v19.0.1.3.0
- `custom/justech_l10n_do_ncf` → v19.0.1.3.0
- `custom/justech_l10n_do_reports` → v19.0.1.3.0
- `custom/hellenia_account` → v19.0.1.0.8
- `custom/hellenia_ux` → wizard anulación (tipo cancelación)

## Upgrade en DEV/TEST

```bash
# En contenedor Odoo
odoo -u justech_l10n_do_base,justech_l10n_do_ncf,hellenia_account,justech_l10n_do_reports -d <db> --stop-after-init
```

Luego ejecutar `sync_catalog_from_taxes` (post_init o manual desde shell).

## Sin cambios en

- Core Odoo
- Enterprise
- PRODUCCIÓN (hasta PASS TEST + aprobación)

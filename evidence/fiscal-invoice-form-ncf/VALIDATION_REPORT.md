# Validación: NCF histórico Adel en formularios de factura

**Entorno:** `erp.justech.do` / `justech_dev`  
**Fecha:** 2026-07-10  
**Módulo:** `justech_l10n_do_ncf` 19.0.2.2.2  
**Commit:** pendiente de aprobación

## Objetivo

Mostrar tipo de comprobante, NCF y origen fiscal al abrir facturas históricas (Adel/l10n_latam) y nuevas (Justech), vía Fiscal Data Provider.

## Cambios (solo lectura/visualización fiscal)

- Campos computed en `account.move` vía FDP: `justech_fiscal_*`
- Pestaña «Comprobante Fiscal» → grupo «Datos fiscales» (readonly)
- Sin backfill, sin modificar documentos existentes

## Resultado

| Check | Resultado |
|-------|-----------|
| Shell samples (venta/compra marzo B01/B02/E31, NC, Justech) | PASS |
| 4 empresas (PlugSafe, Omni, Just Office, JUSTECH) | PASS |
| Batch 80 docs con fuente NCF → display vacío | 0 |
| Pagos intactos | 738 |
| Form = FDP = PDF (`justech_get_ncf`) | PASS |
| DGII exporters usan FDP | confirmado en código |
| Browser 34/34 | PASS |

## Evidencias

`evidence/fiscal-invoice-form-ncf/` (screenshots + `shell_validation.json` + `visual_validation.json`)

## Rollback

Revertir archivos de `justech_l10n_do_ncf` (models/views) y `-u justech_l10n_do_ncf` en `justech_dev`. Histórico de datos no se tocó.

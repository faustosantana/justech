# Recuperación — Detalle del pago

## Problema reportado

Al abrir un pago registrado no aparecía:
- Factura afectada / NCF
- Monto aplicado
- Total retenido / neto transferido
- Detalle por factura
- Retenciones con asiento contable

## Causa

1. **Commit `70df199`:** `_hellenia_apply_withholding_to_payment_vals` hacía `return` temprano sin retenciones → `hellenia_applied_amount` vacío.
2. **Vista:** `invisible="not hellenia_applied_amount and not hellenia_withholding_total"` ocultaba todo el resumen en pagos sin retención.
3. **No existía** sección "Detalle por factura" persistente.

## Fix (18.12)

### Persistencia
- `hellenia_applied_amount` siempre en vals del pago.
- Nuevo modelo `hellenia.payment.application.line` poblado en `_hellenia_finalize_persistent_lines` y `_hellenia_sync_application_lines`.

### Vista `account_payment_withholding_views.xml`

| Sección | Contenido |
|---------|-----------|
| **Resumen aplicación** | Facturas afectadas, monto aplicado, total retenido, neto transferido |
| **Detalle por factura** | Factura, NCF, fecha, total, aplicado, retenciones, retenido, neto, estado conciliación |
| **Retenciones aplicadas** (pestaña) | Factura, NCF, retención, base, %, monto, cuenta, asiento, reporte fiscal |

### Visibilidad
- `hellenia_show_application_detail` — visible en pagos `posted` o con líneas de aplicación.

## Evidencia TEST

Pagos de prueba con detalle completo tras cerrar y reabrir:

| Test | Pago ejemplo | applied | wh | app_lines | NCF |
|------|--------------|---------|-----|-----------|-----|
| `01_partial_no_wh` | PBNKD/2026/00012 | 5000 | 0 | 1 | ✓ |
| `02_partial_gov` | PBNKD/2026/00014 | 5000 | 211.86 | 1 | ✓ |
| `05_reopen_detail` | — | 11800 | 500 | 1 | ✓ |

Certificación: `05_reopen_detail` PASS — detalle persiste al reabrir.

# Certificación reporte 623 — Fase 18.10

## Alcance

Formato DGII 623 — retenciones del Estado (5% Gobierno).

## Fuente de datos (post 18.10)

1. **Primaria:** `hellenia.payment.withholding.line` con `affects_623=True`
2. **Secundaria:** `account.payment.justech_do_gov_withholding_amount`
3. **Legacy:** líneas impuesto `-5% ISR Gov.` en factura

## Exportador

`justech.do.dgii.623.exporter`:
- `_persistent_gov_lines()` — busca líneas persistentes
- `_has_gov_withholding()` — incluye pagos reconciliados
- `_gov_amount()` — suma líneas persistentes primero
- `classify_moves()` — incluye facturas con líneas persistentes 623

## Campos requeridos por fila 623

| Campo | Fuente |
|-------|--------|
| RNC entidad | `partner.vat` |
| Fecha retención | línea persistente `date` o pago |
| Monto | `amount` línea persistente |
| Referencia pago | `hellenia_payment_reference` / cheque |

## Validación

Caso `12_623` en certificación 18.10:
- Reporte con líneas exportables
- `_has_gov_withholding` = True
- `_gov_amount` >= 500

## Limitaciones conocidas (P0 si fallan)

- Pagos sin pasar por wizard Hellenia: sin líneas persistentes → 623 vacío
- Referencia bancaria obligatoria DGII: sin `hellenia_payment_reference` → documento incompleto
- Período mensual YYYYMM: usar `justech.do.dgii.period`, no YTD

## Estado implementación

**Implementado** lectura desde líneas persistentes.  
**Pendiente validación manual UI** en TEST tras deploy 19.0.1.0.13.

No marcar PASS producción hasta verificación manual del Excel 623 en período actual.

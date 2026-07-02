# Abonos parciales con retenciones

## Comportamiento

El wizard permite editar **Monto a aplicar** por factura. Al cambiar el monto:

- `@api.onchange("amount_to_pay")` recalcula retenciones.
- Si el abono es menor al residual, las retenciones con base `untaxed` / `itbis` / `total` se **prorratean** proporcionalmente: `base × (monto_aplicado / residual)`.
- Base `applied_amount` usa directamente el monto aplicado.

## Casos validados

| Caso | Resultado esperado |
|------|-------------------|
| RD$11,800 abono RD$5,000 sin retención | `payment_state=partial`, residual correcto |
| RD$11,800 abono RD$5,000 + ITBIS 100% | Retención ≈ ITBIS × (5000/11800) |
| Dos facturas: una completa, otra parcial | Dos pagos independientes |
| Retención > monto aplicado | Error de validación |

## Residual y conciliación

- CxC/CxP se concilia por el **monto bruto aplicado** (`amount_to_pay`).
- Banco recibe el **neto** (aplicado − retenciones).
- Estado de factura: `partial` o `paid` según residual restante.

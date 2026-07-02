# Ciclo contable de retenciones

## Modelo persistente: `hellenia.payment.withholding.line`

Campos: pago, factura, NCF, partner, catálogo, base, %, monto, cuenta, moneda, compañía, fecha, afecta 606/607/623, asiento, línea contable, estado.

## Asiento — Venta / cobro

| Cuenta | Débito | Crédito |
|--------|--------|---------|
| Banco/Caja | Neto | |
| Retención por cobrar | Retenido | |
| Cuentas por cobrar | | Bruto aplicado |

## Asiento — Compra / pago

| Cuenta | Débito | Crédito |
|--------|--------|---------|
| Cuentas por pagar | Bruto aplicado | |
| Banco/Caja | | Neto |
| Retención por pagar | | Retenido |

## Cuentas validadas en TEST

| Retención | Cuenta |
|-----------|--------|
| ITBIS 100% | `21030201` |
| Gobierno 5% | `11080302` |

## Validaciones

- Asiento balanceado (D=C)
- `hellenia_applied_amount` = bruto
- `hellenia_net_transfer` = bruto − retenido
- Línea GL vinculada (`move_line_id`)

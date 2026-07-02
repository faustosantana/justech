# Retenciones dominicanas en flujo de pago — Fase 17.1

## Impuestos reutilizados (l10n_do)

| Checkbox UI | Impuesto Odoo | Uso |
|-------------|---------------|-----|
| Retención 5% Gobierno | `-5% ISR Gov.` | sale |
| Retención ITBIS 30% | `-30% ITBIS Leg. (N02-05)` | purchase |
| Retención proveedor informal 10% | `-10% ISR Fee` | purchase |
| Retención ITBIS informal 75% | `-75% ITBIS (N08-10)` | purchase |

**No se inventan tasas.** Se activan vía `hellenia.account.payment.setup.configure_withholding_reference()`.

## Comportamiento

1. El usuario marca una o más retenciones (no automáticas).
2. El sistema calcula base, porcentaje, monto y cuenta contable.
3. Se muestra tabla **Detalle retenciones**.
4. Al registrar, `account.payment.register` reduce el monto del pago y crea líneas `write_off_line_vals` balanceadas.

## Modelos

- `hellenia.payment.withholding.line` — líneas transitorias (wizard partner + register)
- `payment_register_withholding.py` — integración en `account.payment.register`

## Efecto contable

- **CxC/CxP**: se concilia el monto bruto de la factura.
- **Banco/caja**: recibe el neto (total − retenciones).
- **Retención**: cuenta del impuesto (repartición fiscal).

## Validación TEST

Casos 10–13 en `scripts/phase17-1-validate-payments-test.py`.

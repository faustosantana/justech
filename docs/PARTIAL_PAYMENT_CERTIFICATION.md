# Certificación — Abono parcial (Fase 18.13)

## Caso obligatorio

| Campo | Valor |
|-------|-------|
| Factura | RD$10,000 + ITBIS RD$1,800 = **RD$11,800** |
| Monto a aplicar | **RD$5,000** |
| Retención 5% Gobierno (proporcional) | RD$211.86 |

## Resultado TEST (automático)

| Test | Estado |
|------|--------|
| `03_partial_no_wh` | PASS — pago RD$5,000, residual RD$6,800, `partial` |
| `05_partial_gov` | PASS — wh proporcional, GL línea retención, conciliación parcial |

## Mecanismo nativo

1. `custom_user_amount = 5000` en `account.payment.register`.
2. `payment_difference_handling = 'open'`.
3. `payment.amount = 5000` (bruto).
4. `_reconcile_payments` concilia RD$5,000.

## Evidencia

`evidence/phase18-13-final-payment-retention-test.json` → tests `03_*`, `05_*`, `15_partial_reconcile`

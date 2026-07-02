# Validación abonos parciales — flujo nativo Odoo 19

**Fase 19.3 — Certificación TEST**  
**Resultado:** PASS (41/41)  
**Base:** `evidence/phase19-3-partial-payment-fix-test.json`

---

## Regla funcional verificada

| Entrada usuario | `register.amount` | `payment.amount` | Factura |
|-----------------|-------------------|------------------|---------|
| Monto a aplicar RD$5,000 | RD$5,000 | RD$5,000 | `partial`, residual RD$6,800 |
| Monto completo RD$11,800 | RD$11,800 | RD$11,800 | `paid`, residual RD$0 |

---

## Campos nativos Odoo utilizados

| Campo | Rol en parcial |
|-------|----------------|
| `account.payment.register.amount` | Monto bruto a conciliar |
| `custom_user_amount` | Evita que `_compute_amount` resetee al residual |
| `custom_user_currency_id` | Moneda del monto manual |
| `payment_difference_handling` | `'open'` — deja residual sin write-off |
| `account.payment.amount` | Hereda de register via `_create_payment_vals_from_wizard` |

**NO** se crea `account.payment` manualmente — flujo 100% vía `account.payment.register._create_payments()`.

---

## Retenciones proporcionales

Factura RD$11,800 (base RD$10,000 + ITBIS RD$1,800), abono RD$5,000:

| Retención | Cálculo | Monto TEST |
|-----------|---------|------------|
| 5% Gobierno | base × (5000/11800) × 5% | RD$211.86 |
| ITBIS 100% | ITBIS × (5000/11800) × 100% | RD$762.71 |

Banco recibe: monto aplicado − retenciones (hook `_prepare_move_withholding_lines`).

---

## Vista de pago — detalle por factura

Validado en certificación:

- `hellenia_applied_amount` = RD$5,000 (no RD$11,800)
- `hellenia.payment.application.line.applied_amount` = RD$5,000
- `app_not_invoice_total` PASS — detalle no muestra total factura como monto aplicado

---

## Reportes fiscales

| Reporte | Estado |
|---------|--------|
| 607 | PASS — exportador operativo |
| 623 | PASS — movimientos visibles con retención gov |
| PDF recibo | PASS — incluye retenciones |

---

## Regresión

| Escenario | PASS |
|-----------|------|
| Parcial sin retención | ✓ |
| Parcial con retención gov | ✓ |
| Parcial ITBIS 100% | ✓ |
| Completo sin retención | ✓ |
| Proveedor parcial | ✓ |
| Proveedor completo | ✓ |

---

## Listo para PROD

**Sí** — certificación TEST completa.  
**Promoción:** pendiente aprobación explícita del usuario.

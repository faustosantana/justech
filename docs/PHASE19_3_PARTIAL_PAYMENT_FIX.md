# Fase 19.3 — Fix abonos parciales en wizard de pagos

**Fecha:** 2026-07-01  
**Resultado TEST:** PASS (41/41)  
**PROD:** Pendiente aprobación explícita  
**Módulo:** `hellenia_account` 19.0.1.0.21  
**Commit:** `322238e` — rama `cursor/phase19-3-partial-payment-fix-dd85`

---

## Problema

Desde **Clientes → Pagos → Nuevo**, al indicar **Monto a aplicar = RD$5,000** sobre factura RD$11,800:

- El sistema creaba pago por **RD$11,800**
- La factura quedaba **pagada completa** (`paid`)
- Residual esperado RD$6,800 no se respetaba

---

## Causa exacta

### Línea origen del síntoma

`payment_partner_wizard.py` → `action_register_payments()` (antes líneas 432-449):

```python
register_vals = {..., "amount": line.amount_to_pay, ...}
if line.amount_to_pay < abs(move.amount_residual) - 0.01:
    register_vals["custom_user_amount"] = line.amount_to_pay
register = env["account.payment.register"].create(register_vals)
```

### Mecanismo Odoo 19

En `account.payment.register._compute_amount` (Odoo core):

```python
if not wizard.journal_id or not wizard.currency_id or not wizard.payment_date or wizard.custom_user_amount:
    wizard.amount = wizard.amount  # preservar
else:
    wizard.amount = total_amount_values['amount_by_default']  # ← RESIDUAL COMPLETO
```

Al crear el register desde el partner wizard:

1. Se pasaba `amount=5000` pero `custom_user_amount` **no siempre quedaba fijado** en el create (orden de computes / falta de `custom_user_currency_id`).
2. `_compute_amount` **sobrescribía** `amount` con el residual total (RD$11,800).
3. `_create_payment_vals_from_wizard` usa `self.amount` → pago completo.
4. Conciliación total → factura `paid`.

**No era** que `amount_to_pay` del wizard ignorara el valor en todos los casos — el wizard enviaba el monto correcto, pero **el register lo perdía** antes de `_create_payments()`.

---

## Corrección aplicada

### 1. `payment_partner_wizard.py`

| Método nuevo | Función |
|--------------|---------|
| `_effective_amount_to_pay()` | Lee monto aplicado real con flush |
| `_register_vals_for_line()` | Arma vals con `custom_user_amount`, `custom_user_currency_id`, `payment_difference_handling='open'` |

`action_register_payments()` ahora:

- Pasa contexto `hellenia_applied_amount`
- Fuerza write post-create si el register perdió el monto
- Usa `force_save="1"` en vista para `amount_to_pay`

### 2. `models/account_payment_register.py`

Override `create()` que preserva monto parcial y re-fuerza `custom_user_amount` si `_compute_amount` lo resetea.

### 3. `wizards/payment_register_withholding.py`

Retenciones proporcionales usan `custom_user_amount or amount` (no residual como fallback).

### 4. Vista `payment_partner_wizard_views.xml`

`force_save="1"` en `amount_to_pay` para persistir edición inline antes del botón.

---

## Evidencia TEST (41/41 PASS)

| Caso | payment.amount | residual | invoice_state |
|------|----------------|----------|---------------|
| Parcial sin retención | **5,000** | **6,800** | partial |
| Parcial 5% Gobierno | 5,000 | 6,800 | partial (wh=211.86) |
| Parcial ITBIS 100% | 5,000 | 6,800 | partial (wh=762.71) |
| Pago completo | 11,800 | 0 | paid |
| Proveedor parcial/completo | PASS | — | — |
| 607 / 623 / PDF | PASS | — | — |

Archivo: `evidence/phase19-3-partial-payment-fix-test.json`

---

## Promoción a PROD

**NO promovido** — requiere aprobación explícita.

Pasos cuando se apruebe:

1. Backup PROD
2. Upgrade `hellenia_account` 19.0.1.0.21
3. Reiniciar Odoo PROD
4. Ejecutar `phase19-3-partial-payment-fix-test.py` adaptado a `hellenia_prod`
5. Validar pago parcial real en UI

---

## Rollback

Restaurar backup previo a upgrade de `hellenia_account`.

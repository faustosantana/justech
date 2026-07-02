# Arquitectura — Wizard de pagos Hellenia (Fase 20.1)

## Modelos

| Modelo | Rol |
|--------|-----|
| `hellenia.payment.partner.wizard` | Formulario transitorio (cabecera) |
| `hellenia.payment.partner.wizard.line` | Una fila por factura pendiente |
| `account.payment.register` | Wizard nativo Enterprise (un pago por factura) |
| `account.payment` | Pago publicado |

## Flujo nativo

```
Usuario → Vista form (action 650)
       → onchange partner_id → _load_pending_invoices() [ÚNICO punto de carga]
       → Usuario marca apply + amount_to_pay
       → web_save (persiste wizard + líneas tal cual)
       → action_register_payments()
       → Por cada línea seleccionada: account.payment.register → _create_payments()
       → account.payment + conciliación + payment_state en account.move
```

## Reglas invariantes

1. `_load_pending_invoices()` **solo** en `@api.onchange("partner_id", "partner_type", "currency_id")`.
2. `create()` y `write()` del wizard **no** recargan facturas.
3. Líneas nuevas: `apply=False`, `amount_to_pay=0`, sin retenciones.
4. `apply=False` ⇒ `amount_to_pay` debe ser 0 (validado al registrar).
5. Monto del pago = `line.amount_to_pay` (nunca `move.amount_residual` directo).
6. Selección por `partner_id` exclusivamente (nunca por nombre).

## Vista y acciones (sin cambios)

- Vista: `hellenia_account.view_hellenia_payment_partner_wizard_form`
- Acción cliente: `hellenia_account.action_hellenia_register_customer_payment`
- Botón: `action_register_payments`

## Abono parcial Enterprise

Si `amount_to_pay < residual`, se usa `custom_user_amount`, `payment_difference_handling=open` y `force_payment_move` en contexto — patrón estándar Odoo 19 Enterprise para dejar saldo abierto.

## Retenciones

Por línea vía `withholding_catalog_ids` → `withholding_detail_ids` → `hellenia_withholding_line_ids` en `account.payment.register`.

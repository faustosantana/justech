# Lógica de selección — Wizard de pagos Hellenia

**Modelo:** `hellenia.payment.partner.wizard`  
**Módulo:** `hellenia_account` 19.0.1.0.24+

---

## Regla absoluta

El wizard **solo** procesa líneas donde:

```
apply = True
```

Y usa exactamente:

```
amount_to_pay
```

para armar `account.payment.register`.

---

## Flujo de datos

```
Usuario marca Aplicar + Monto a aplicar
        ↓
line_ids (transient) con apply / amount_to_pay persistidos (force_save)
        ↓
action_register_payments()
        ↓
_selected_lines() → filtered(apply=True)
        ↓
Por cada línea seleccionada:
  active_ids = [move.id]   ← UNA factura
  amount = amount_to_pay
  custom_user_amount si parcial
        ↓
account.payment.register → _create_payments()
```

---

## Campos clave

| Campo | Rol |
|-------|-----|
| `apply` | Checkbox obligatorio. `False` = línea ignorada por completo |
| `amount_to_pay` | Monto real a aplicar. Fuente de verdad para el pago |
| `amount_residual` | Solo lectura / referencia. No se usa como monto de pago |
| `withholding_catalog_ids` | Solo se procesan retenciones de líneas con `apply=True` |

---

## Carga de facturas pendientes

`_load_pending_invoices()`:

- Busca facturas `not_paid` / `partial` del partner
- Crea una línea por factura con:
  - `apply = False` (usuario debe marcar explícitamente)
  - `amount_to_pay = residual` (visible al marcar Aplicar)

**No** marca todas las facturas como seleccionadas.

---

## Onchange `apply`

| Estado | Comportamiento |
|--------|----------------|
| `apply=False` | `amount_to_pay=0`, retenciones limpiadas |
| `apply=True` sin monto | `amount_to_pay = residual` |
| `apply=True` con retenciones | Recalcula detalle proporcional |

---

## Validaciones en `action_register_payments`

1. Ninguna línea marcada → `Debe seleccionar al menos una factura.`
2. Línea marcada con monto ≤ 0 → error por factura
3. Monto > residual → error (no se trunca silenciosamente)
4. Retención > monto → error

---

## Persistencia UI (Odoo 19)

En listas editables del wizard transitorio:

```xml
<field name="apply" force_save="1"/>
<field name="amount_to_pay" force_save="1"/>
```

Sin `force_save` en `apply`, el checkbox desmarcado **no se guardaba** antes de ejecutar el botón — causa raíz del bug en producción.

---

## Contexto `account.payment.register`

Por cada factura seleccionada:

```python
active_model = "account.move"
active_ids = [invoice.id]  # solo esa factura
```

Nunca se pasan todas las facturas pendientes del partner en `active_ids`.

---

## Enterprise (PROD)

- Abonos parciales: `force_payment_move=True` solo si `is_partial`
- Pago completo: sin `force_payment_move` (cuenta banco del diario)
- Setup bancario asigna `payment_account_id` al `default_account_id` del diario

---

## Anti-patrones prohibidos

- Iterar `line_ids` sin filtrar `apply`
- `apply=True` por defecto en todas las líneas
- Recargar facturas sobrescribiendo selección del usuario sin necesidad
- Crear `account.payment` manualmente saltando el register
- Usar residual completo cuando el usuario digitó monto parcial

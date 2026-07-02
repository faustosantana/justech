# Análisis del flujo contable de pagos — Odoo 19

**Fase 18.10 — Bloque 1 obligatorio**  
**Fuente:** `odoo/odoo` branch `19.0` (módulo `account`)  
**Ámbito:** Solo TEST — sin cambios en producción

---

## 1. Modelos y responsabilidades

| Modelo | Rol en el ciclo de pago |
|--------|-------------------------|
| `account.payment.register` | Wizard transitorio: calcula monto, diferencia, write-off, crea pagos |
| `account.payment` | Registro persistente del cobro/pago; genera `account.move` |
| `account.move` | Asiento contable del pago (y de la factura) |
| `account.move.line` | Líneas: banco, CxC/CxP, retención, write-off |
| `account.partial.reconcile` | Conciliación parcial entre líneas de factura y pago |
| `account.reconcile.model` | Plantillas de conciliación automática (no usado en retenciones manuales) |

---

## 2. Creación de pagos desde factura

### 2.1 Entrada

- Acción **Registrar pago** sobre `account.move` (factura publicada).
- Contexto: `active_model=account.move`, `active_ids=[invoice_ids]`.
- `default_get()` carga `line_ids` (líneas CxC/CxP con residual > 0).

### 2.2 Batches (`_compute_batches`)

Agrupa líneas por:
- Compañía, partner, tipo (inbound/outbound), moneda, cuenta bancaria.

`can_edit_wizard = True` solo si hay **un batch**. Con múltiples batches el wizard no es editable.

### 2.3 `_create_payments()` — método central

```
edit_mode = can_edit_wizard AND (len(lines) == 1 OR group_payment)

SI edit_mode:
    payment_vals = _create_payment_vals_from_wizard(batch)
SINO:
    payment_vals = _create_payment_vals_from_batch(batch)  # un pago por factura

_init_payments(to_process)   → account.payment.create()
_post_payments()             → action_post()
_reconcile_payments()        → reconcile() CxC/CxP
```

**Métodos que NO deben reemplazarse:**
- `_create_payments` (completo) — rompe conciliación y posting
- `_reconcile_payments` — rompe `account.partial.reconcile`
- `_post_payments` — rompe estados del pago

**Métodos seguros para heredar:**
- `_create_payment_vals_from_wizard(batch_result)` — inyectar campos y líneas persistentes
- `_create_payment_vals_from_batch(batch_result)` — **obligatorio** si `edit_mode=False`
- `_init_payments(to_process)` — post-create, antes de posting
- `_reconcile_payments(to_process)` — llamar `super()` y luego enlazar trazabilidad

---

## 3. `_create_payment_vals_from_wizard` (Odoo 19)

Construye el diccionario `create_vals` del pago:

```python
payment_vals = {
    'amount': self.amount,           # monto banco (liquidez)
    'payment_type': inbound|outbound,
    'destination_account_id': CxC/CxP,
    'write_off_line_vals': [],       # diferencias / descuentos
}
```

### Diferencia de pago (`payment_difference`)

| Modo | Comportamiento |
|------|----------------|
| `open` | Pago parcial; factura queda con residual |
| `reconcile` + write-off | Crea línea en `write_off_account_id` |
| Early payment discount | Líneas EPD automáticas |

### Write-off manual

```python
write_off_line_vals.append({
    'name': label,
    'account_id': cuenta,
    'partner_id': partner,
    'currency_id': moneda,
    'amount_currency': sign * monto,
    'balance': convertido,
})
```

---

## 4. `account.payment.create()` — asiento contable

Odoo 19 separa **write-off** y **withholding** en `_prepare_move_lines_per_type`:

```python
write_off_lines = write_off_line_vals or []
withholding_lines = self._prepare_move_withholding_lines({})  # hook extensible

# Si ambos existen, write_off se descarta (no se combinan)
if withholding_lines and write_off_lines:
    write_off_lines = []

liquidity = amount (neto banco)
counterpart = -(liquidity + write_off + withholding)  → CxC/CxP bruto
```

### Hook nativo para retenciones (Odoo 19)

```python
def _prepare_move_withholding_lines(self, default_values):
    return []  # base vacío — aquí inyecta Hellenia
```

**Decisión Fase 18.10:** usar este hook en lugar de `write_off_line_vals` para retenciones RD, evitando doble contabilización y alineación con el motor nativo.

### Secuencia en `create()`

1. `super().create(vals)` — crea pago + One2many persistentes
2. `_generate_journal_entry(write_off_line_vals=...)` — genera `account.move`
3. `_prepare_move_withholding_lines` lee líneas persistentes ya creadas

---

## 5. Conciliación

`_reconcile_payments` busca:
- Líneas del pago en CxC/CxP (`_get_valid_payment_account_types`)
- Líneas de factura a conciliar (`to_reconcile`)

Llama `.reconcile()` → crea `account.partial.reconcile`.

La factura queda `paid` o `partial` según residual.

**Retención:** la conciliación es por el **monto bruto aplicado** (CxC/CxP), no solo el neto bancario. El asiento del pago ya incluye la línea de retención que completa el balance.

---

## 6. Esquema contable RD

### Cobro cliente (inbound) con retención Gobierno 5%

| Cuenta | Débito | Crédito |
|--------|--------|---------|
| Banco (liquidez) | Neto recibido | |
| Retención por cobrar | Monto retenido | |
| CxC cliente | | Total aplicado |

### Pago proveedor (outbound) con retención ITBIS

| Cuenta | Débito | Crédito |
|--------|--------|---------|
| CxP proveedor | Total aplicado | |
| Banco | | Neto pagado |
| Retención por pagar | | Monto retenido |

---

## 7. Pagos parciales

- Wizard: `amount` < residual → `payment_difference_handling = 'open'`
- Conciliación parcial → `account.partial.reconcile` con monto parcial
- Retención proporcional: base y monto según `amount_to_pay / amount_total`

---

## 8. Pagos múltiples (varias facturas)

- `group_payment=True` + `edit_mode=True` → **un** `account.payment`
- `_create_payment_vals_from_wizard` con monto total neto
- Conciliación de todas las líneas CxC/CxP seleccionadas
- Cada retención debe llevar `move_id` de su factura (no un solo move del batch)

---

## 9. Causa raíz del fallo previo (RD$0 retenido)

| # | Causa | Impacto |
|---|-------|---------|
| 1 | Solo se heredaba `_create_payment_vals_from_wizard`, no `_from_batch` | Pagos con `edit_mode=False` sin retención |
| 2 | Retención vía `write_off_line_vals` paralelo al hook `_prepare_move_withholding_lines` | Riesgo de conflicto en Odoo 19 |
| 3 | Persistencia solo en `create vals` sin hook en `_init_payments` | Líneas ausentes → `hellenia_withholding_total = 0` |
| 4 | `_payment_batch_result` inexistente | `finalize` sin factura correcta en multi-factura |
| 5 | Un pago por factura en wizard multi | UX y totales inconsistentes con expectativa |
| 6 | Scripts PASS en savepoint sin validar UI/deploy | Falsa certificación |

---

## 10. Métodos heredados en Hellenia (Fase 18.10)

| Método | Módulo | Acción |
|--------|--------|--------|
| `_create_payment_vals_from_wizard` | `payment_register_withholding` | Inyecta líneas persistentes, reduce `amount` al neto |
| `_create_payment_vals_from_batch` | `payment_register_withholding` | Idem para modo batch |
| `_init_payments` | `payment_register_withholding` | Fallback persistencia + link move lines |
| `_reconcile_payments` | `payment_register_withholding` | Link `partial_reconcile_id` |
| `_prepare_move_withholding_lines` | `payment_withholding_line` | Líneas contables de retención |
| `_create_payment_vals_from_wizard` | `account_payment_gov` | Campos 623 en pago/factura |

**No reemplazados:** `_create_payments`, `_post_payments`, `_generate_journal_entry`.

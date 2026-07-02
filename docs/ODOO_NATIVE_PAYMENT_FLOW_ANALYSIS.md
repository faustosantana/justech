# Análisis del flujo nativo de pagos — Odoo 19 Enterprise

**Fase 18.13 — Bloque 1 obligatorio**  
**Fuente verificada:** contenedor TEST `odoo:19.0` — `/usr/lib/python3/dist-packages/odoo/addons/account/`  
**Ámbito:** Solo TEST — sin cambios en producción

---

## 1. Modelos y responsabilidades

| Modelo | Archivo | Rol |
|--------|---------|-----|
| `account.payment.register` | `wizard/account_payment_register.py` | Wizard transitorio: monto, diferencia, write-off, creación de pagos |
| `account.payment` | `models/account_payment.py` | Registro persistente; genera y sincroniza `account.move` |
| `account.move` | `models/account_move.py` | Asiento del pago y de la factura |
| `account.move.line` | `models/account_move_line.py` | Líneas: banco, CxC/CxP, retención, write-off |
| `account.partial.reconcile` | `models/account_partial_reconcile.py` | Conciliación parcial entre factura y pago |

---

## 2. Métodos nativos analizados (Odoo 19)

### 2.1 `account.payment.register`

| Método | Línea aprox. | Función |
|--------|--------------|---------|
| `_compute_amount` | ~476 | Calcula monto por defecto; respeta `custom_user_amount` |
| `_onchange_amount` | ~709 | Si monto ≠ presets → `custom_user_amount = amount` |
| `_compute_payment_difference` | — | `residual - amount` |
| `_compute_payment_difference_handling` | ~862 | Parcial → `'open'`; EPD → `'reconcile'` |
| `_create_payment_vals_from_wizard` | ~991 | `amount`, `write_off_line_vals`, destino CxC/CxP |
| `_create_payment_vals_from_batch` | ~1077 | Un pago por factura (batch mode) |
| `_init_payments` | ~1109 | `account.payment.create(create_vals)` |
| `_post_payments` | — | `action_post()` |
| `_reconcile_payments` | ~1185 | `line.reconcile()` por cuenta CxC/CxP |
| `_create_payments` | ~1216 | Orquesta init → post → reconcile |

### 2.2 `account.payment`

| Método | Línea aprox. | Función |
|--------|--------------|---------|
| `create` | ~891 | Pop `write_off_line_vals`; crea pago; genera asiento |
| `_prepare_move_withholding_lines` | ~283 | **Hook vacío** — extensión para retenciones |
| `_prepare_move_lines_per_type` | ~311 | Arma banco + contraparte + write-off + **withholding** |
| `_prepare_move_line_default_vals` | ~393 | Wrapper de líneas del asiento |
| `_seek_for_lines` | ~164 | Clasifica: liquidez / contraparte / write-off |
| `_synchronize_to_moves` | ~995 | Re-sincroniza asiento tras cambios |
| `action_post` | ~1126 | Publica pago y asiento |

### 2.3 Campos clave del wizard

| Campo | Uso en pago parcial |
|-------|---------------------|
| `amount` | Monto bruto aplicado → pasa a `payment.amount` |
| `custom_user_amount` | Flag de override manual; evita que compute sobrescriba |
| `payment_difference_handling` | `'open'` = dejar residual (abono parcial) |
| `write_off_line_vals` | Lista transitoria para diferencias contables |
| `writeoff_account_id` | Cuenta de contraparte para diferencia reconciliada |

---

## 3. Cómo Odoo registra un pago parcial

1. Usuario abre **Registrar pago** sobre factura con residual RD$11,800.
2. Usuario edita `amount` a RD$5,000.
3. `_onchange_amount` detecta diferencia → setea `custom_user_amount = 5000`.
4. `payment_difference > 0` → `payment_difference_handling = 'open'`.
5. `_create_payment_vals_from_wizard`:
   - `'amount': 5000`
   - `'write_off_line_vals': []` (sin write-off en parcial abierto)
6. `_reconcile_payments` concilia solo RD$5,000.
7. Factura queda `payment_state = 'partial'`, residual RD$6,800.

**Requisito Hellenia:** al crear register desde partner wizard, forzar `custom_user_amount` si `amount < residual`.

---

## 4. Cómo Odoo registra un pago completo

1. `amount` = residual total.
2. `payment_difference = 0`.
3. Conciliación total → factura `paid`.

---

## 5. Cómo Odoo maneja diferencias (`payment_difference_handling`)

| Modo | Cuándo | Efecto |
|------|--------|--------|
| `open` | Parcial sin descuento | Residual queda abierto; sin write-off |
| `reconcile` | EPD o write-off manual | `write_off_line_vals` con cuenta contraparte |

---

## 6. Cómo Odoo crea líneas write-off

Solo si `payment_difference_handling == 'reconcile'`:

```python
payment_vals['write_off_line_vals'].append({
    'name': self.writeoff_label,
    'account_id': self.writeoff_account_id.id,
    'amount_currency': write_off_amount_currency,
    'balance': converted_balance,
})
```

En `account.payment.create()`, `write_off_line_vals` se extrae de vals y se pasa a generación del asiento.

**Conflicto con retenciones (Odoo 19):**

```python
# _prepare_move_lines_per_type
if withholding_lines and write_off_lines:
    write_off_lines = []  # mutuamente excluyentes
```

Por eso Hellenia usa `_prepare_move_withholding_lines` y **no** `write_off_line_vals` para retenciones.

---

## 7. Cómo Odoo concilia facturas

`_reconcile_payments`:
1. Filtra líneas CxC/CxP del pago (posted, no reconciliadas).
2. Une con líneas de factura del batch.
3. Por cada cuenta: `(payment_lines + invoice_lines).reconcile()`.
4. Crea `account.partial.reconcile` con monto aplicado.

---

## 8. Asiento contable nativo con retención (hook Odoo 19)

### Fórmula en `_prepare_move_lines_per_type`

**Cobro (inbound):**
```
liquidity_amount_currency = amount - withholding
counterpart_amount_currency = -(liquidity + write_off + withholding) = -amount (bruto)
```

**Resultado contable cobro con retención:**
```
D Banco          neto  (amount - wh)
D Retención      wh
C CxC            amount (bruto aplicado)
```

**Pago proveedor (outbound):**
```
D CxP            amount (bruto)
C Banco          neto
C Retención      wh
```

### Regla crítica para Hellenia

> **`payment.amount` = bruto aplicado a factura**, NO neto banco.  
> Odoo resta la retención de la línea de liquidez automáticamente.

Reducir `payment.amount` al neto causa doble descuento y CxC incompleta.

---

## 9. Dónde inyectar retención sin romper el flujo

| Punto | Acción correcta | Incorrecto |
|-------|-----------------|------------|
| `_create_payment_vals_from_wizard` | Inyectar `hellenia_withholding_line_ids` persistentes + `hellenia_applied_amount` | Reducir `amount` al neto |
| `account.payment.create` | Líneas persistentes en vals **antes** de generar asiento | Crear líneas solo después del post |
| `_prepare_move_withholding_lines` | Devolver líneas GL retención | Usar `write_off_line_vals` para retención |
| `_init_payments` | Fallback persistencia + re-sync si falta GL | Reemplazar `_create_payments` |
| `_reconcile_payments` | `super()` + stamp fiscal + sync detalle | Omitir `super()` |
| Parcial | `custom_user_amount` + `amount` bruto | Forzar residual completo |

---

## 10. Referencia oficial: `l10n_account_withholding_tax`

Odoo Community/Enterprise incluye módulo de referencia que extiende el mismo hook:

- `account.payment._prepare_move_withholding_lines` ← lee `withholding_line_ids`
- `account.payment.register._create_payment_vals_from_wizard` ← pasa líneas al pago
- `amount` permanece bruto; banco = neto

Hellenia replica este patrón con `hellenia.payment.withholding.line` persistente.

---

## 11. Tres caminos de pago — requisitos 18.13

| Camino | Wizard nativo | Extensión Hellenia requerida |
|--------|---------------|------------------------------|
| A. Factura → Pagar | `account.payment.register` | Selector catálogo retenciones en register |
| B. Clientes → Pagos → Nuevo | `hellenia.payment.partner.wizard` | Cálculo server-side de retenciones |
| C. Proveedores → Pagos → Nuevo | Idem B | Idem |

Los tres deben converger en el mismo pipeline: register → payment vals → `_prepare_move_withholding_lines` → reconcile.

---

## 12. Conclusión para diseño 18.13

El diseño actual **puede** cumplir el ciclo nativo si:

1. Las líneas persistentes existen **en `create_vals`** del pago.
2. `payment.amount` = bruto; retención vía hook nativo.
3. `custom_user_amount` en abonos parciales.
4. Stamp fiscal (623) **después** de `_reconcile_payments`, no antes.
5. Totales almacenados desde líneas persistentes, no solo compute UI.
6. 623 lee líneas persistentes con filtro unificado (`affects_623` OR `GOV_CATALOG_CODES`).

No se requiere rollback de arquitectura; se requiere **cerrar el ciclo nativo** correctamente.

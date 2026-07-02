# Guard servidor — Selección facturas wizard de pagos

**Módulo:** `hellenia_account` 19.0.1.0.25+  
**Modelo:** `hellenia.payment.partner.wizard`

---

## Problema

En UI (Contabilidad → Clientes → Pagos → Nuevo), el usuario marcaba **una sola** factura pero el sistema creaba pagos para **todas**.

Las pruebas shell con `line.write()` pasaban; la UI real fallaba.

---

## Causa raíz real

1. **`_load_pending_invoices()`** cargaba `amount_to_pay = residual completo` en **todas** las líneas aunque `apply=False`.
2. El listado editable **no siempre persistía** el estado del checkbox antes de ejecutar el botón.
3. Líneas no seleccionadas conservaban **monto > 0** en BD; combinado con estados `apply` inconsistentes, el riesgo de procesar facturas no deseadas era alto.

No bastaba `force_save` en `apply` ni `apply=False` por defecto (v19.0.1.0.24).

---

## Guardas implementadas (v25)

### 1. Carga sin monto preasignado

```python
"apply": False,
"amount_to_pay": 0.0,
```

El residual solo se copia al marcar **Aplicar** (`_onchange_apply`).

### 2. `write()` en línea

Si `apply=False` → fuerza `amount_to_pay=0` y limpia retenciones.

### 3. `_enforce_server_selection_guard()`

Antes de pagar, anula montos/retenciones en líneas no marcadas.

### 4. `_selected_line_ids_sql()`

Lee `apply=TRUE` **directo de PostgreSQL** — no confía solo en caché ORM/UI.

### 5. Validaciones duras

- Sin líneas seleccionadas → error
- `len(payments) == len(selected_lines)`
- `active_ids = [invoice.id]` (una factura por register)
- Un solo pago creado por register

### 6. Vista

- `amount_to_pay` **readonly** si `not apply`
- Retenciones **readonly** si `not apply`

### 7. Log debug (TEST/diagnóstico)

Contexto `hellenia_debug_payment_selection=True` registra wizard, líneas, `active_ids`, pagos.

---

## Flujo correcto

```
Cargar facturas → apply=False, amount=0
Usuario marca A → onchange → amount=residual → usuario edita 5000
Guard servidor → apply=False en B,C → amount=0 forzado
_selected_line_ids_sql() → solo A
register(active_ids=[A]) → un pago 5000
```

---

## Anti-patrones prohibidos

- Precargar `amount_to_pay=residual` sin `apply=True`
- Procesar `line_ids` sin filtrar `apply`
- Confiar solo en el checkbox visual sin guard en servidor
- `active_ids` con todas las facturas del partner

# Fase 19.6 — Fix selección facturas wizard de pagos

**Fecha:** 2026-07-01  
**Resultado TEST:** **PASS** (24/24)  
**PROD:** Pendiente aprobación explícita  
**Módulo:** `hellenia_account` **19.0.1.0.24**  
**Rama:** `cursor/phase19-6-selected-invoices-fix-dd85`  
**Commit:** `1a18461`

---

## Problema crítico

Desde **Clientes → Pagos → Nuevo**, con 3 facturas pendientes:

- Usuario marcaba **solo 1** factura
- Monto a aplicar = RD$5,000
- Al registrar: **3 pagos**, las 3 facturas pagadas completas (RD$11,800 c/u)
- Checkbox **Aplicar** y monto parcial ignorados

---

## Causa exacta

### 1. Todas las facturas marcadas por defecto

```python
# payment_partner_wizard.py — HelleniaPaymentPartnerWizardLine
apply = fields.Boolean(default=True)  # línea 14 (antes)

# _load_pending_invoices()
"apply": True,  # línea 320 (antes)
"amount_to_pay": abs(move.amount_residual),
```

Al abrir el wizard, **las 3 facturas** quedaban con `apply=True` y monto = residual completo.

### 2. Checkbox sin `force_save`

```xml
<!-- payment_partner_wizard_views.xml (antes) -->
<field name="apply" string="Aplicar"/>
```

En listas editables Odoo 19, al desmarcar **Aplicar** el valor `False` **no persistía** al pulsar «Registrar pago». Las líneas seguían con `apply=True` en base transitoria.

### 3. `action_register_payments` confiaba en datos no guardados

```python
selected = self.line_ids.filtered(lambda l: l.apply and l.amount_to_pay > 0)
```

La lógica era correcta en código, pero procesaba **todas** las líneas porque `apply` seguía `True` para B y C.

**Línea origen del síntoma:** `_load_pending_invoices()` línea 320 (`apply: True`) + vista sin `force_save` en `apply`.

---

## Corrección aplicada

| Cambio | Archivo |
|--------|---------|
| `apply` default `False` | `payment_partner_wizard.py` |
| `_load_pending_invoices`: `apply=False` | `payment_partner_wizard.py` |
| `force_save="1"` en checkbox Aplicar | `payment_partner_wizard_views.xml` |
| `_selected_lines()` con `flush_recordset` | `payment_partner_wizard.py` |
| `_onchange_apply`: limpia monto/retenciones si `apply=False` | `payment_partner_wizard.py` |
| Error si monto > residual (no truncar) | `_effective_amount_to_pay()` |
| Mensajes de error explícitos | `action_register_payments()` |

---

## Validación TEST — 7 casos

| Caso | Escenario | Resultado |
|------|-----------|-----------|
| 1 | Solo A, RD$5,000 parcial | 1 pago, A partial, B/C not_paid |
| 2 | A parcial + B completo, C sin marcar | 2 pagos, C not_paid |
| 3 | Ninguna seleccionada | Error claro |
| 4 | apply con monto 0 | Error claro |
| 5 | monto > residual | Error claro |
| 6 | Parcial + retención 5% Gobierno | WH RD$211.86, A partial |
| 7 | Retención en factura NO seleccionada | B not_paid, 1 pago sin WH de B |

**Evidencia:** `evidence/phase19-6-selected-invoices-partial-payment-test.json`

---

## Evidencia caso 1 (crítico)

```json
{
  "payments_created": 1,
  "payment_amount": 5000.0,
  "A_state": "partial",
  "A_residual": 6800.0,
  "B_state": "not_paid",
  "C_state": "not_paid"
}
```

---

## PROD

**No promovido** — requiere aprobación explícita tras TEST PASS.

Pasos pendientes (Bloque 7):

1. Backup PROD
2. Promover rama `cursor/phase19-6-selected-invoices-fix-dd85`
3. Upgrade `hellenia_account` → 19.0.1.0.24
4. Reiniciar Odoo
5. Validar escenario 3 facturas / 1 seleccionada / RD$5,000

---

## Referencias

- `docs/PAYMENT_WIZARD_SELECTION_LOGIC.md`
- `scripts/phase19-6-selected-invoices-partial-payment-test.py`

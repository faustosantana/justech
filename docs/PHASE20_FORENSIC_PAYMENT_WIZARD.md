# Fase 20 — Investigación forense wizard de pagos (PROD)

**Backup pre-investigación:** `backups/hellenia-prod/2026-07-01_1248`  
**Módulo PROD:** `hellenia_account` 19.0.1.0.23  
**Logging forense:** desplegado temporalmente (sin fix funcional)

---

## 1. Auditoría vista (Parte 1)

| Campo | Valor demostrado |
|-------|------------------|
| **view_id** | 1730 |
| **xml_id** | `hellenia_account.view_hellenia_payment_partner_wizard_form` |
| **name** | `hellenia.payment.partner.wizard.form` |
| **model** | `hellenia.payment.partner.wizard` |
| **inherit_id** | *(ninguno)* |
| **priority** | 16 |
| **module** | `hellenia_account` |
| **active** | true |

**Otras vistas del wizard:** ninguna (0 herencias, 0 reemplazos).

**Acciones:**
- `hellenia_account.action_hellenia_register_customer_payment` (id 650) → `hellenia.payment.partner.wizard`
- `hellenia_account.action_hellenia_register_vendor_payment` (id 651)

**Botón Nuevo en lista pagos:** hereda `account.view_account_payment_tree` vía `hellenia_account.view_account_payment_tree_customer_hellenia` (id 1731).

**hellenia_ux:** uninstalled — no hay wizard alternativo.

---

## 2. Auditoría modelo (Parte 2)

| Campo | Valor |
|-------|-------|
| **Modelo** | `hellenia.payment.partner.wizard` |
| **Archivo** | `custom/hellenia_account/wizards/payment_partner_wizard.py` |
| **Clase** | `HelleniaPaymentPartnerWizard` |
| **_inherit** | ninguno (TransientModel propio) |
| **Registro** | `hellenia_account.model_hellenia_payment_partner_wizard` |

Líneas: `hellenia.payment.partner.wizard.line` — misma archivo, clase `HelleniaPaymentPartnerWizardLine`.

---

## 3. Auditoría botón (Parte 3)

| Campo | Valor |
|-------|-------|
| **Vista** | id 1730, arch footer |
| **Button** | `<button name="action_register_payments" type="object" string="Registrar pago"/>` |
| **Método** | `action_register_payments` |
| **Clase** | `HelleniaPaymentPartnerWizard` |
| **Archivo** | `payment_partner_wizard.py` |
| **Línea PROD v23** | 462 |

---

## 4. Carga de facturas — valores demostrados (Parte 4)

### ANTES de `_load_pending_invoices`
- Sin líneas (`line_ids` vacío)

### DESPUÉS de `_load_pending_invoices` (log PROD partner 22)

```
HELLENIA_FORENSIC [after_load_pending_invoices]
partner=SMOKE P13.4 CF(22)
lines=[{
  invoice: INV/2026/00002,
  orm_apply: False,      ← apply NO es True en servidor
  orm_amount: 11800.0,   ← amount_to_pay = residual COMPLETO
  residual: 11800.0
}]
```

### ¿Quién pone apply=True?

**Nadie en Python al cargar.** `apply=False` en línea 325.

`apply=True` aparece solo tras interacción UI:
- Log `line_onchange_apply` cuando usuario marca checkbox
- Log `before_web_save`: `{'apply': True, 'amount_to_pay': 5000}`

### ¿Quién pone amount_to_pay=11800?

**`_load_pending_invoices()` líneas 324-327:**

```python
"apply": False,
"amount_to_pay": abs(move.amount_residual),  # ← AQUÍ
```

### UI con múltiples facturas (TEST, mismo patrón de código)

Playwright Fase 19.11 en TEST (v25, mismo `amount_to_pay=residual` en servidor):
- **checked=3, total=3** al cargar cliente con 3 facturas
- Captura: `evidence/phase19-11/screenshots-test/05-apply-checkboxes-on-load.png`

### UI PROD 1 factura (Playwright v4)

- **checked=0** pero **amount=RD$11,800** visible en columna Monto
- `payment_total=RD$0.00` (compute filtra por apply)

---

## 5. Cadena de ruptura demostrada (Parte 5 — logs)

### Flujo UI real v6 (PROD, partner 22, parcial RD$5,000)

| Etapa | apply | amount_to_pay | Evidencia |
|-------|-------|---------------|-----------|
| after_load_pending | **False** | **11800** | log 13:01:45 |
| line_onchange_apply (UI marca) | **True** (virtual+real) | **11800** | log 13:01:52 |
| line_onchange_amount_to_pay | **True** (2 líneas!) | **5000** + virtual **11800** | log 13:01:53 |
| **before_web_save** | **True** | **5000** | UI envía correcto |
| **after_create** (create hook) | **False** | **11800** | **_load_pending_invoices RESETEA** |
| before_action_register | **False** | **11800** | selected_ids=**[]** |
| Resultado UI | Error | — | "Debe seleccionar al menos una factura" |

### Punto de ruptura #1 (carga)

**Archivo:** `payment_partner_wizard.py`  
**Clase:** `HelleniaPaymentPartnerWizard`  
**Método:** `_load_pending_invoices`  
**Línea:** **326** — `amount_to_pay: abs(move.amount_residual)`

Efecto: UI muestra monto completo en todas las filas aunque `apply=False`. Con varias facturas, Odoo 19 marca visualmente todos los checkboxes (TEST: 3/3).

### Punto de ruptura #2 (create destruye selección UI)

**Archivo:** `payment_partner_wizard.py`  
**Clase:** `HelleniaPaymentPartnerWizard`  
**Método:** `create` → `_load_pending_invoices`  
**Líneas:** **264-266** y **330**

`web_save` envía `apply=True, amount=5000` pero `create()` vuelve a llamar `_load_pending_invoices()` que **borra** `line_ids` del payload y recrea con `apply=False, amount=11800`.

### Punto de ruptura #3 (pago múltiple histórico)

Cuando UI muestra **todas marcadas** (TEST 3/3) y `web_save` envía **todas** con `apply=True` y `amount_to_pay=11800`:

- Si `create()` no resetea (versiones anteriores) **o** si `_selected_lines()` procesaba líneas con `amount_to_pay>0` sin filtrar `apply`
- `action_register_payments` itera cada línea seleccionada → N pagos × RD$11,800

En v23 actual `_selected_lines` filtra solo `apply=True` (línea 460). Tras reset de create, selected=[] → error. Los pagos históricos PBNKD/00001-00007 se crearon con código/flujo anterior o con partner incorrecto (id 23 sin facturas vs 22).

### Dato PROD adicional: partners duplicados

`SMOKE P13.4 CF` existe 3 veces (id 21, 22, 23). Solo id **22** tiene factura pendiente. Autocomplete por defecto selecciona id **23** → wizard vacío → confusión operativa.

---

## 6. Playwright PROD (Parte 6)

| Captura | Archivo | Hallazgo |
|---------|---------|----------|
| Wizard carga 1 factura | `v4-04-on-load.png` | checked=0, amount=11800 visible |
| Usuario marca + 5000 | `v5-06-5000.png` | Total RD$5000 correcto en UI |
| Tras Registrar | `v6-07-after.png` | Error: "Debe seleccionar al menos una factura" |
| Pagos | `v6-07-after.png` (fondo) | 4 pagos erróneos previos RD$11,800 c/u |

**Multi-factura todas marcadas:** evidencia TEST `phase19-11/screenshots-test/05` (mismo defecto de carga).

---

## 7. Fix aplicado

**NINGUNO** — solo investigación y logging temporal.

---

## 8. Commit

Pendiente en rama `cursor/phase20-forensic-payment-wizard-dd85` (documentación + scripts Playwright + logging).

---

## 9. Veredicto

**NO PASS** — el wizard no cumple ningún criterio de validación final.

# Fase 19.1 — Fix crítico: `hellenia_payment_reference` en PRODUCCIÓN

**Fecha:** 2026-07-01  
**Resultado TEST:** PASS  
**Resultado PROD:** PASS

---

## Problema

Al aplicar un pago desde **Clientes → Pagos → Nuevo** en PRODUCCIÓN:

```
ValueError: Invalid field 'hellenia_payment_reference' in 'account.payment.register'
```

**Ubicación:** `payment_partner_wizard.py` → `action_register_payments()` → línea `.create(register_vals)`

---

## Causa exacta

| Factor | TEST | PROD |
|--------|------|------|
| `hellenia_ux` | **installed** | **uninstalled** |
| `hellenia_payment_reference` en `account.payment.register` | ✓ (vía hellenia_ux) | ✗ |
| `hellenia_payment_reference` en `account.payment` | ✓ (vía hellenia_ux) | ✗ |

El wizard `hellenia.payment.partner.wizard` (módulo `hellenia_account`) envía en `_register_vals_common()`:

- `hellenia_payment_reference`
- `hellenia_card_auth` / `hellenia_card_batch`
- `hellenia_check_number` / `hellenia_check_bank_id` / `hellenia_check_date`

Esos campos estaban definidos **solo en `hellenia_ux`**, no en `hellenia_account`. La certificación Fase 18.13 pasó en TEST porque `hellenia_ux` está instalado allí; PROD no lo tiene.

**No fue:** upgrade incompleto ni registry sin reinicio — fue **dependencia implícita no declarada** sobre un módulo no instalado en PROD.

---

## Corrección aplicada (Opción A)

Campos movidos a **`hellenia_account`** (módulo promovido a PROD):

### `account.payment.register` (`models/account_payment_register.py`)

- Campos de referencia y método de pago
- `_hellenia_extra_payment_vals()` — propaga valores al `account.payment` creado
- Override `_create_payment_vals_from_wizard` / `_create_payment_vals_from_batch`

### `account.payment` (`models/payment_withholding_line.py`)

- Campos persistentes: referencia, tarjeta, cheque
- Flags computados: `hellenia_is_card`, `hellenia_is_check`, `hellenia_is_transfer`, `hellenia_is_cash` (requeridos por exportador 623)

**Versión:** `hellenia_account` 19.0.1.0.19 → **19.0.1.0.20**

---

## Validación TEST

Script: `scripts/phase19-1-payment-reference-prod-fix.py`

| Caso | Resultado |
|------|-----------|
| Campos en register | PASS |
| Campos en payment | PASS |
| Pago sin retención | PASS |
| Pago parcial | PASS |
| Retención 5% Gobierno | PASS |
| Retención ITBIS 100% | PASS |
| move_id / asiento / conciliación | PASS |
| Exportador 607 | PASS |
| Exportador 623 | PASS |

---

## Promoción PROD

1. Backup: `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_*`
2. Upgrade `hellenia_account` 19.0.1.0.20
3. Reinicio Odoo PROD
4. Validación `phase19-1-payment-reference-prod-fix.py` en `hellenia_prod`

---

## Rollback

```bash
bash scripts/restore-hellenia-prod.sh /opt/odoo-projects/hellenia/backups/hellenia-prod/<backup-dir>
```

---

## Evidencia

- `evidence/phase19-1-payment-reference-prod-fix.json`

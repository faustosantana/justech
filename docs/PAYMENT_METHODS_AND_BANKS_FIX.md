# Corrección bancos y métodos de pago — Fase 16

**Cliente:** Hellenia, S.R.L.  
**Módulo:** `hellenia_account` v19.0.1.0.1  
**Ambiente objetivo:** TEST (`hellenia_test`) → PROD tras PASS  
**Fecha:** 2026-06-29

---

## 1. Síntoma reportado

En el wizard de cobro/pago de Odoo:

1. No aparecían las cuentas bancarias de la empresa (López de Haro DOP/USD).
2. Los métodos de pago no mostraban etiquetas en español (Transferencia, Efectivo, Tarjeta, Cheque).
3. El diario bancario legacy `BNK1` existía sin vínculo a `res.partner.bank`.

---

## 2. Causa raíz

| # | Causa | Evidencia |
|---|-------|-----------|
| 1 | **`account.journal.bank_account_id` sin vincular** en `BNK1` | Las cuentas `res.partner.bank` (4040043811 DOP, 4010461048 USD) existían en el partner de la empresa, pero el diario no tenía `bank_account_id` → Odoo no ofrece la cuenta en pagos ni conciliación |
| 2 | **Un solo diario `BNK1` para dos monedas** | Configuración Fase 3.5 creó métodos en `BNK1`/`CSH1` sin separar DOP/USD |
| 3 | **Métodos genéricos en inglés** | Líneas `Manual Payment` / `Checks` sin renombrar a español |
| 4 | **Error instalación `hellenia_account`** | `payment_type` escrito en `account.payment.method.line.create()` — campo *related* de solo lectura en Odoo 19 → `ParseError` en `payment_setup.xml` |

**No es un bug de core ni Enterprise.** Es configuración incompleta + bug en setup custom.

---

## 3. Corrección aplicada

### 3.1 Módulo `hellenia_account`

| Componente | Acción |
|------------|--------|
| `payment_bank_setup.py` | Crea diarios **BNKD** (DOP) y **BNKU** (USD); vincula `bank_account_id`; renombra métodos; desactiva `BNK1` si vacío |
| `account_move_line.py` | Campo related `justech_do_ncf` en líneas del wizard |
| `account_payment_register_views.xml` | Lista facturas con NCF, fecha, vencimiento, residual |
| `post_init_hook` | Ejecuta setup idempotente tras instalar |
| Dependencia | `l10n_do_check_printing` para método **Cheque** |

### 3.2 Diarios resultantes

| Código | Nombre | Tipo | Moneda | Cuenta bancaria |
|--------|--------|------|--------|-----------------|
| **BNKD** | Banco López de Haro DOP | bank | DOP | 4040043811 |
| **BNKU** | Banco López de Haro USD | bank | USD | 4010461048 |
| **CSH1** | Caja / Efectivo | cash | DOP (compañía) | — |
| BNK1 | Banco (legacy) | bank | — | Desactivado si sin movimientos |

### 3.3 Métodos de pago (español)

| Método | Diario(s) | Dirección | Código Odoo |
|--------|-----------|-----------|-------------|
| Efectivo | CSH1 | Entrada / Salida | `manual` |
| Transferencia | BNKD, BNKU | Entrada / Salida | `manual` |
| Tarjeta | BNKD, BNKU | Entrada | `manual` |
| Cheque | BNKD, BNKU | Salida | `check_printing` |

---

## 4. Despliegue TEST

```bash
cd /opt/odoo-projects/hellenia
git fetch origin cursor/phase16-payments-banks-dd85
git checkout cursor/phase16-payments-banks-dd85
bash scripts/run-phase16-payments-test.sh
```

Evidencia esperada: `evidence/phase16-payments-test.json` con `"ok": true`.

---

## 5. Promoción PROD (solo tras PASS TEST)

```bash
APPROVE_PROMOTION=1 bash scripts/promote-phase16-payments-prod.sh
```

Requisitos: backup PROD automático + misma rama/commit + validación `phase16-payments-prod.json`.

---

## 6. Archivos de referencia

- `config/company/banks.yaml` — cuentas López de Haro
- `config/company/payment_methods.yaml` — métodos esperados
- `scripts/phase16-validate-payments-test.py` — suite automatizada

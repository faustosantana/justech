# Fase 18.7 — Corrección OWL Error en Pagos

**Ambiente:** TEST (`hellenia_test` @ `test.hellenia.cloud`)  
**Módulo:** `hellenia_account` **19.0.1.0.11**  
**Fecha:** 2026-07-01 UTC  
**Resultado:** **TEST PASS — 9/9**

---

## Error reportado

```
"account.payment"."hellenia_invoice_display" field is undefined.
```

OwlError / RPC_ERROR al abrir formulario de pagos en TEST.

---

## Causa exacta

**Registry desincronizado entre workers web y código Python tras deploy Fase 18.6.**

1. La vista XML `account_payment_withholding_views.xml` se cargó en la BD referenciando `hellenia_invoice_display`.
2. El modelo Python `account_payment_withholding.py` existía en disco pero los **workers Odoo en ejecución** no habían recargado el registry tras el upgrade parcial.
3. `odoo shell` (proceso nuevo) sí veía los campos; la UI web (workers antiguos) no.

**No era:** campo inexistente en código, import faltante en `__init__.py`, ni vista huérfana permanente. El código de Fase 18.6 era correcto; faltaba **upgrade + reinicio** coordinado.

---

## Corrección aplicada

| Acción | Detalle |
|--------|---------|
| Versión | `19.0.1.0.10` → `19.0.1.0.11` |
| Vista XML | Campos auxiliares `invisible="1"` en `<sheet>` para modificadores OWL |
| Deploy TEST | Sincronización completa `custom/hellenia_account` |
| Upgrade | `button_immediate_upgrade()` en `hellenia_account` |
| Reinicio | `docker compose restart odoo` en stack TEST |

---

## Campos finales en `account.payment`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `hellenia_applied_amount` | Monetary | Monto bruto aplicado a factura |
| `hellenia_withholding_line_ids` | One2many | Líneas persistentes de retención |
| `hellenia_withholding_total` | Monetary (computed, stored) | Total retenido |
| `hellenia_net_transfer` | Monetary (computed, stored) | Neto transferido banco/caja |
| `hellenia_invoice_display` | Char (computed) | Facturas afectadas (resumen) |

Modelo relacionado: `hellenia.account.payment.withholding`

---

## Vistas corregidas

- `views/account_payment_withholding_views.xml`
  - Campos auxiliares invisible en sheet (OWL)
  - Grupo «Resumen aplicación» con factura, aplicado, retenido, neto
  - Pestaña «Retenciones aplicadas» con detalle NCF/base/%/monto/cuenta

---

## Pruebas ejecutadas (TEST)

| # | Prueba | Resultado |
|---|--------|-----------|
| 1 | Upgrade módulo 19.0.1.0.11 | PASS |
| 2 | Campos en registry | PASS |
| 3 | `get_views` form sin excepción | PASS |
| 4 | Leer pago sin retenciones | PASS |
| 5 | Leer pago con retenciones | PASS |
| 6 | Pestaña retenciones con NCF | PASS |
| 7 | Factura pagada → smart button pago | PASS |
| 8 | Asiento balanceado | PASS |
| 9 | Wizard pagos (regresión) | PASS |

### Regresión adicional

| Fase | Resultado |
|------|-----------|
| 18.4 cálculo retenciones | PASS |
| 18.5 606/607 | PASS (all_pass) |
| 18.6 pagos/abonos parciales | PASS (23/23) |

---

## Comando revalidación

```bash
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env restart odoo
cd /opt/odoo-projects/hellenia
bash scripts/run-odoo-shell-env.sh test phase18-7-payment-owl-error-test.py PHASE187 evidence/phase18-7-payment-owl-error-test.json
```

---

## Conclusión

| Pregunta | Respuesta |
|----------|-----------|
| **TEST PASS / FAIL** | **PASS** |
| **Listo para continuar validación retenciones** | **Sí** |
| **Promover a producción** | **No** — requiere aprobación explícita |

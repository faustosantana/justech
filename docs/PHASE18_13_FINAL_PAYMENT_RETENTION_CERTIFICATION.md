# Fase 18.13 — Certificación final pagos y retenciones

**Entorno:** TEST (`hellenia_test`)  
**Rama:** `cursor/phase18-13-native-payment-rebuild-dd85`  
**Resultado:** **89/89 PASS**  
**Evidencia:** `evidence/phase18-13-final-payment-retention-test.json`  
**Producción:** NO promovido

---

## Resumen

| Ítem | Resultado |
|------|-----------|
| **TEST** | **PASS** |
| Abono parcial RD$5,000 / RD$11,800 | PASS |
| Total retenido visible y almacenado | PASS |
| Detalle pago (resumen + facturas + retenciones) | PASS |
| Tres caminos de pago | PASS |
| 606 / 607 / 623 | PASS |
| Asiento GL con línea retención | PASS |
| Conciliación parcial y total | PASS |
| PDF recibo | PASS |
| Rollback requerido | **NO** |

---

## Causa raíz

1. Register borraba líneas de retención del partner wizard al rebuild sin catálogos.
2. UI compute sin cálculo server-side de montos.
3. Stamp fiscal 623 antes de conciliación.
4. Parcial sin `custom_user_amount`.
5. Register desde factura sin selector de retenciones.

---

## Métodos Odoo analizados

Ver `docs/ODOO_NATIVE_PAYMENT_FLOW_ANALYSIS.md`:

- `account.payment.register._create_payment_vals_from_wizard`
- `account.payment.register._init_payments` / `_reconcile_payments`
- `account.payment._prepare_move_withholding_lines`
- `account.payment._prepare_move_lines_per_type`
- `account.payment.create`

---

## Módulos desplegados TEST

- `hellenia_account` 19.0.1.0.18
- `justech_l10n_do_reports` 19.0.1.12.0

---

## Ciclo cerrado

```
Wizard → Pago → Asiento (GL retención) → Conciliación → Factura → Recibo PDF → 606/607/623
```

---

## Recomendación

**Continuar** sobre rama 18.13. Arquitectura nativa validada. Validación manual en UI TEST recomendada antes de cualquier promoción futura.

# Payment Wizard Final Fix — Fase 17.1

## Problema

Desde **Contabilidad → Clientes → Pagos** (y Proveedores → Pagos), al crear un pago el sistema abría `account.payment` vacío. **No cargaba facturas pendientes** del cliente/proveedor seleccionado.

El flujo **Factura → Pagar** sí funcionaba porque usa `account.payment.register` con `active_ids` de la factura.

## Causa raíz

| Flujo | Modelo | Facturas pendientes |
|-------|--------|---------------------|
| Factura → Pagar | `account.payment.register` | Sí (vía `active_ids`) |
| Menú → Pagos → Nuevo | `account.payment` | No |

## Solución

Nuevo wizard `hellenia.payment.partner.wizard` (módulo `hellenia_account` v19.0.1.0.3):

1. Se abre desde **Registrar cobro** / **Registrar pago** en las listas de pagos.
2. Al seleccionar cliente/proveedor carga automáticamente facturas con `payment_state` en `not_paid` / `partial`.
3. Tabla con: aplicar, factura, NCF, fechas, moneda, total, pendiente, monto a aplicar.
4. Soporta pago total, parcial y múltiple (DOP/USD).
5. Delega el registro a `account.payment.register` por factura con retenciones.

## Archivos

- `custom/hellenia_account/models/payment_partner_wizard.py`
- `custom/hellenia_account/views/payment_partner_wizard_views.xml`
- `custom/hellenia_account/security/ir.model.access.csv`

## Validación

```bash
bash scripts/run-phase17-1-test.sh
```

Evidencia: `evidence/phase17-1-full-validation.json`

# Fase 6.5 — Revisión Contable

**Principio:** El NCF es capa fiscal sobre contabilidad estándar — sin asientos manuales innecesarios.  
**Fecha:** 2026-06-30

---

## 1. Resumen

**La integración contable es correcta.** El módulo no crea `account.move.line` adicionales, no modifica impuestos, no interviene pagos ni conciliaciones. Solo enriquece `account.move` antes de `action_post()`.

**Calificación contabilidad:** **A+**

---

## 2. Modelos estándar — matriz de impacto

| Modelo | ¿Modificado? | ¿Crea registros? | Evaluación |
|--------|--------------|------------------|------------|
| `account.move` | ✅ Campos + pre-post hook | No líneas extra | ✅ |
| `account.move.line` | ❌ | No | ✅ |
| `account.payment` | ❌ | No | ✅ |
| `account.partial.reconcile` | ❌ | No | ✅ |
| `account.tax` | ❌ | No | ✅ |
| `account.journal` | ✅ Config campos | No | ✅ |
| `stock_account` / `stock.move` | ❌ | No | ✅ |
| `sale.order` | ❌ | No | ✅ |
| `purchase.order` | ❌ | No | ✅ |
| `stock.picking` | ❌ | No | ✅ |

---

## 3. Flujo de publicación

```
draft invoice
    → _justech_assign_ncf_before_post()  [solo metadata fiscal]
    → super().action_post()              [Odoo genera asiento estándar]
    → posted (CxC/CxP/impuestos/inventario según config estándar)
```

**Validado en DEV:** débitos = créditos (118.0 = 100 + 18% ITBIS), línea `asset_receivable` presente.

---

## 4. Notas de crédito y débito

| Tipo | Mecanismo Odoo | Impacto Justech |
|------|----------------|-----------------|
| `out_refund` | `_reverse_moves` | B04 asignado en pre-post ✅ |
| Debit note | `debit_origin_id` + `out_invoice` | B03 por ref ✅ (no E2E) |
| `in_refund` | estándar | **Sin lógica NCF** — gap fiscal |

---

## 5. Anulación NCF (`action_void_ncf`)

- Marca `justech_do_ncf_voided=True`
- **No reversa** el asiento contable
- **No cancela** la factura (`button_cancel`)

✅ Correcto para anulación **fiscal** (reporte 608) distinta de anulación contable.  
⚠️ Usuario debe entender que void NCF ≠ cancelar factura.

**Recomendación producto:** documentar y/o bloquear void si factura ya pagada.

---

## 6. Compras B11/B13

- NCF asignado automáticamente en `in_invoice`
- Asiento CxP generado por Odoo estándar
- **CxP no assertada** en tests pero flujo respeta `purchase` → `account.move`

---

## 7. Pagos y conciliaciones

Sin override de:
- `account.payment.register`
- `_reconcile_plan`
- `action_register_payment`

**Sin regresión detectada** — capa fiscal no interfiere post-posting.

---

## 8. Inventario y valoración

Módulos MVP no tocan `stock.valuation.layer` ni `account.move` de stock.

Facturas con productos almacenables (`consu` + `is_storable`) validadas en DEV sin alteración de flujo stock.

---

## 9. Impuestos (ITBIS)

- Impuestos aplicados en líneas de factura estándar
- Reportes calculan ITBIS desde `tax_line_id.name` — **no modifica** impuestos contables
- Riesgo: reporte DGII incorrecto si impuesto no se llama "ITBIS", no contabilidad

---

## 10. Anti-patrones ausentes (verificado)

| Anti-patrón | Presente |
|-------------|----------|
| `account.move.create` manual para fiscal | ❌ No |
| Líneas contables manuales en Python | ❌ No |
| Override de `_post` / `_sync_invoice | ❌ No |
| Modificación de `balance` en líneas | ❌ No |

---

## 11. Conclusión

Integración contable **ejemplar** para una localización fiscal: metadata antes del post, cero interferencia con el motor contable Odoo.

**Calificación:** **A+**

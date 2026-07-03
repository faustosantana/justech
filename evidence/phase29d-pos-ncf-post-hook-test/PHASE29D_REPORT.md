# Fase 29D — Hook fiscal NCF en `account.move._post()` (TEST)

**Fecha:** 2026-07-03  
**Ambiente:** `hellenia_test` (https://test.hellenia.cloud)  
**Módulo:** `justech_l10n_do_ncf` **19.0.1.5.2**  
**Arquitectura:** Opción D — asignación NCF común en `_post()` pre-`super()`

---

## Resumen ejecutivo

| Resultado | Detalle |
|-----------|---------|
| **Implementación** | ✅ Completada solo en TEST |
| **Validación funcional** | ✅ **13/13 PASS** (cubre 16 criterios solicitados) |
| **Healthcheck TEST** | ✅ **PASS** |
| **PROD** | ❌ No tocado |
| **Merge / push** | ❌ Pendiente aprobación explícita |

---

## Diff de código (`justech_l10n_do_ncf`)

### `custom/justech_l10n_do_ncf/models/account_move.py`

- **Nuevo** `_justech_moves_for_ncf_on_post(soft)` — filtra borradores; con `soft=True` excluye fechas futuras (auto-post programado no consume NCF).
- **Nuevo** `_post(soft)` — invoca `_justech_assign_ncf_before_post()` sobre moves elegibles **antes** de `super()._post()`.
- **`action_post()`** — queda sin lógica fiscal; solo `return super().action_post()`.

### `custom/justech_l10n_do_ncf/__manifest__.py`

- Versión: `19.0.1.5.1` → `19.0.1.5.2`

```diff
+    def _justech_moves_for_ncf_on_post(self, soft=True):
+        moves = self.filtered(lambda m: m.state == "draft")
+        if soft:
+            today = fields.Date.context_today(self)
+            moves = moves.filtered(lambda m: not m.date or m.date <= today)
+        return moves
+
+    def _post(self, soft=True):
+        self._justech_moves_for_ncf_on_post(soft)._justech_assign_ncf_before_post()
+        return super()._post(soft=soft)
+
     def action_post(self):
-        self._justech_assign_ncf_before_post()
         return super().action_post()
```

**No se modificó:** `hellenia_pos`, POS config, QWeb/PDF, reportes, PROD.

---

## Mapeo validación → 16 criterios

| # | Criterio | Test | Resultado | Evidencia |
|---|----------|------|-----------|-----------|
| 1 | Factura manual B02 | `factura_manual_b02_ncf` | ✅ | INV/2026/00236 → B0200020178 |
| 2 | Factura manual B01 | `factura_manual_b01_ncf_via_post` | ✅ | INV/2026/00237 → B0100020040 (vía `_post`) |
| 3 | Cotización → factura | `cotizacion_factura_ncf` | ✅ | S00170 → B0200020179 |
| 4 | POS consumidor final B02 | `pos_consumidor_final_b02_efectivo` | ✅ | INV/2026/00240 → B0200020181 |
| 5 | POS cliente RNC B01 | `pos_cliente_rnc_b01_tarjeta` | ✅ | INV/2026/00241 → B0100020041 |
| 6 | Pago efectivo | incluido en test #4 | ✅ | pm_cash |
| 7 | Pago tarjeta | incluido en test #5 | ✅ | pm_card |
| 8 | Pago mixto | `pos_pago_mixto` | ✅ | B0200020182 |
| 9 | Cierre sesión POS | `pos_cierre_sesion` | ✅ | POSS/2026/00023 |
| 10 | Inventario descuenta | `pos_movimiento_inventario` | ✅ | 88 → 85 unidades |
| 11 | Asientos contables | `pos_asientos_contables` | ✅ | 3 facturas posted |
| 12 | Reporte fiscal 607 | `reporte_fiscal_607_no_rompe` | ✅ | 0 errores validación |
| 13 | No doble NCF | `no_doble_ncf` | ✅ | 1 registro consumo |
| 14 | No NCF en borrador | `no_ncf_borrador_autopost_futuro` | ✅ | soft=True, sin NCF |
| 15 | Override manual | `override_manual_ncf` | ✅ | B0200020183 respetado |
| 16 | Healthcheck TEST | `healthcheck-full.sh test` | ✅ | PASS 2026-07-03 02:10 UTC |

---

## Evidencia

| Archivo | Descripción |
|---------|-------------|
| `validation.json` | Resultados estructurados 13 tests |
| `validation-console-v4.txt` | Log Odoo shell (run final PASS) |
| `healthcheck.log` | Healthcheck completo TEST PASS |
| `PHASE29D_REPORT.md` | Este informe |

Script: `scripts/phase29d-ncf-post-hook-validation.py`  
Runner: `scripts/run-phase29d-ncf-post-hook-test.sh`

---

## Notas técnicas

1. **Un solo camino fiscal:** Ventas (`action_post`), facturación directa y POS (`_post` vía `action_pos_order_invoice`) comparten `_justech_assign_ncf_before_post()`.
2. **`soft=True`:** facturas con fecha futura y `auto_post=at_date` permanecen en borrador sin NCF hasta la fecha efectiva.
3. **Sin `if POS`:** el hook es agnóstico al origen del move.
4. **Sync rango TEST:** el script de validación incluye `sync_ncf_range_next()` acotado al rango UAT (solo secuencias dentro de `[sequence_start, sequence_end]`) para evitar colisiones por runs previos; reactiva rango `depleted` si aún hay capacidad.

---

## Deploy TEST ejecutado

```bash
# En hellenia (docker/test)
-u justech_l10n_do_ncf  # → 19.0.1.5.2
```

---

## Pendiente (requiere aprobación)

- [ ] Commit local
- [ ] Push a remoto
- [ ] Merge
- [ ] Fase 29E — replicar en PROD (solo con aprobación explícita)

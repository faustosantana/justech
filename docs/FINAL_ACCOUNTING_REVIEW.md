# Revisión Contable Final — Fase 11

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Referencias:** Fase 6.5, UAT Fase 9, `DOMINICAN_ACCOUNTING_CERTIFICATION.md`

---

## 1. Resumen y calificación

| Dimensión | Calificación |
|-----------|:------------:|
| Integridad asientos | **A+** |
| CxC / CxP | **A** |
| ITBIS ventas/compras | **A** |
| Retenciones | **B** (escenario UAT pendiente) |
| Pagos / cobros | **A** |
| Conciliaciones | **B+** |
| Valoración inventario | **A** (estándar) |
| Costo de ventas | **A** (estándar) |
| NC / ND contables | **A** |
| Reversiones | **A** |

**Calificación contable global: A (93/100)**

**Principio validado:** El módulo Justech actúa como capa fiscal sobre contabilidad Odoo estándar — **no altera líneas de asiento ni impuestos**.

---

## 2. Asientos automáticos

### 2.1 Venta con ITBIS 18%

```
Débito  CxC (asset_receivable)     118.00
Crédito Ingresos (income)          100.00
Crédito ITBIS por pagar             18.00
```

**Validado:** UAT block2 `balanced: true`, `itbis: true`.

### 2.2 Compra con ITBIS

Flujo estándar `purchase` → `account.move` — sin intervención custom en líneas.

**Validado:** UAT block3 `balanced: true`.

### 2.3 Nota de crédito (out_refund)

Mecanismo `_reverse_moves` estándar + metadata B04 Justech.

**Validado:** UAT block4 `credit_balanced: true`.

### 2.4 Nota de débito

`debit_origin_id` + factura adicional — asiento incremental estándar.

**Validado:** UAT block5 PASS.

---

## 3. Cuentas por cobrar y pagar

| Escenario | Estado UAT | Observación |
|-----------|------------|-------------|
| Factura cliente abierta | ✅ | |
| Cobro total | ✅ | 50 cobros |
| Saldo residual cero | ✅ | |
| Factura proveedor | ✅ | |
| Pago proveedor | ✅ | 50 pagos |
| Antigüedad saldos | ⚠️ | Reporte estándar — validar contador |

---

## 4. ITBIS

| Tipo | Fuente | Estado |
|------|--------|--------|
| 18% ventas | `l10n_do` | ✅ Confirmado |
| 16/9/8/18/exento compras | `l10n_do` | ✅ 37 impuestos |
| Reporte impuestos | `l10n_do.tax_report` | ✅ |
| Libro 606/607 ITBIS columnas | Justech MVP | ✅ Por nombre "ITBIS" — frágil |

---

## 5. Retenciones

| Retención | Configurada `l10n_do` | UAT específico |
|-----------|----------------------|----------------|
| ISR proveedor | ✅ 12 retenciones | ⚠️ No ejecutado |
| ITBIS retenido | ✅ | ⚠️ No ejecutado |

**Recomendación pre-Go-Live:** 1 escenario compra con retención en piloto o sesión contador.

---

## 6. Pagos y conciliaciones

| Componente | Override Justech | Estado |
|----------|------------------|--------|
| `account.payment` | No | ✅ |
| `account.payment.register` | No | ✅ |
| `account.partial.reconcile` | No | ✅ |
| Conciliación bancaria | Estándar | ⚠️ OBS UAT |

---

## 7. Inventario y costo de ventas

| Flujo | Mecanismo | Estado |
|-------|-----------|--------|
| Entrada compra → stock valorado | `stock_account` | ✅ |
| Salida venta → COGS | Automático | ✅ |
| Ajuste inventario | Manual | ⚠️ Procedimiento operativo |

**Sin override** en `stock.move` ni `stock.valuation.layer` por módulos Justech.

---

## 8. Anulación fiscal vs contable

| Acción | Efecto contable | Efecto fiscal |
|--------|-----------------|---------------|
| `action_void_ncf` | **Ninguno** | Marca NCF anulado → 608 |
| `button_cancel` factura | Reversa asiento | No automático en MVP |
| `button_draft` | Estándar Odoo | NCF ya asignado — bloqueado |

**Riesgo operativo:** Usuario confunde void NCF con cancelación contable.

**Mitigación documentada:** `ADMINISTRATOR_GUIDE.md` — reforzar en capacitación Go-Live.

---

## 9. Efectos contables incorrectos — búsqueda activa

| Área investigada | Hallazgo |
|------------------|----------|
| Doble asiento por NCF | ❌ No existe |
| ITBIS duplicado | ❌ No detectado |
| CxC negativa anómala | ❌ No en UAT |
| Desbalance post 200 movimientos | ❌ No |
| NC sin reversión | ❌ No |

**Conclusión:** No se identifican efectos contables incorrectos en el alcance UAT.

---

## 10. Pendientes contables pre-Go-Live

| # | Pendiente | Prioridad |
|---|-----------|-----------|
| 1 | Firma / validación plan cuentas contador | P0 |
| 2 | Escenario retenciones compra | P1 |
| 3 | Conciliación bancaria muestra | P1 |
| 4 | Política void NCF vs factura pagada | P1 |

---

## 11. Certificación bloque 5

| Clasificación | **PASS** |
|---------------|----------|
| Nota | **A (93/100)** |
| Bloqueante contable Go-Live | **No** |

---

**Sin cambios contables en Fase 11.**

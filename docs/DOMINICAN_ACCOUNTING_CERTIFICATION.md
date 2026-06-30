# Certificación Contable — República Dominicana (DAFC Bloques A, C, D, E, F)

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` — Odoo `19.0-20260619` Enterprise On-Premise  
**Fecha certificación:** 2026-06-30T05:04:50Z  
**Backup restauración:** `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0502`  
**Script:** `scripts/certify-phase5-dafc.py`  
**Restricción:** Sin modificación de configuración — solo auditoría y transacciones de laboratorio.

---

## Resumen

| Bloque | Área | Estado |
|--------|------|--------|
| A | Plan contable | **PASS** |
| C | Diarios | **PASS** |
| D | Cuentas clave | **PASS CON OBSERVACIONES** |
| E | Pruebas funcionales | **PASS** |
| F | Reportes contables | **PASS** |

---

## Bloque A — Plan contable

**Total cuentas:** 289  
**Numeración:** 100% códigos numéricos (formato DGII/NIIF 8 dígitos)  
**Diario diferencial cambiario:** `CAMBI`

### Distribución por tipo (`account_type`)

| Tipo | Cantidad |
|------|----------|
| expense | 95 |
| liability_non_current | 49 |
| asset_current | 37 |
| asset_non_current | 17 |
| asset_fixed | 16 |
| equity | 16 |
| income | 12 |
| liability_payable | 10 |
| expense_direct_cost | 8 |
| asset_receivable | 8 |
| asset_prepayments | 6 |
| expense_depreciation | 6 |
| asset_cash | 4 |
| income_other | 4 |
| equity_unaffected | 1 |

### Distribución por prefijo de código

| Prefijo | Clasificación | Cantidad |
|---------|---------------|----------|
| 1xx | Activos | 88 |
| 2xx | Pasivos / patrimonio | 59 |
| 4xx | Ingresos | 16 |
| 5xx | Costos directos | 8 |
| 6xx | Cuentas de orden | 99 |
| Otros | — | 19 |

### Cuentas inventario (muestra)

| Código | Nombre |
|--------|--------|
| 11050100 | Inventory of merchandise or finished products |
| 11050200 | Raw Materials Inventory |
| 11050300 | Inventory in Transit |
| 11050400 | Materials and Supplies Inventory |
| 11050500 | Fuel Inventory |

### Cuentas puente / tránsito

- 1 cuenta con referencia transit/puente en nombre
- 11050300 Inventory in Transit — cuenta puente inventario

**Conclusión A:** Plan contable RD cargado, estructura coherente, sin modificaciones requeridas en Fase 5.

---

## Bloque C — Diarios

| Código | Nombre | Tipo | Secuencia |
|--------|--------|------|-----------|
| INV | Sales | sale | 5 |
| FACTU | Purchases | purchase | 6 |
| BNK1 | Bank | bank | 7 |
| MISCE | Miscellaneous Operations | general | 9 |
| CSH1 | Efectivo | cash | 10 |
| CABA | Cash Basis Taxes | general | 10 |
| CAMBI | Exchange Difference | general | 10 |
| STJ | Inventory Valuation | general | 10 |
| TAX | Tax Returns | general | 10 |

**Verificado:** ventas, compras, caja, banco, inventario (STJ), ajustes (MISCE), diferencial cambiario (CAMBI).

---

## Bloque D — Cuentas contables clave

Cuentas por defecto vía propiedades de partner empresa y plan `do`:

| Rol | Código | Nombre | Estado |
|-----|--------|--------|--------|
| Clientes (C×C) | 11030201 | Accounts Receivable from Customers | ✅ |
| Proveedores (C×P) | 21010200 | Accounts Payable to Local Suppliers | ✅ |
| Inventario | 11050100 | Inventory of merchandise or finished products | ✅ |
| Costo de ventas | 51010100 | Cost of Goods | ✅ |
| Ingresos | 4101xxxx | Cuentas income (varias por rubro) | ✅ |
| ITBIS adelantado | 11080101 | ITBIS Paid on Purchases of Local Good | ✅ |
| ITBIS por pagar | 2103xxxx | Retenciones / impuestos por pagar | ✅ (estructura) |
| Banco | 11010201 | Bank | ✅ |
| Caja | 11010100 | Cash (efectivo) | ✅ |
| Resultados | equity_unaffected | Current Year Earnings | ✅ |

**Observación:** La búsqueda automática por nombre en inglés no localizó todas las etiquetas en primera pasada; las cuentas existen en el plan con códigos verificados manualmente.

---

## Bloque E — Pruebas funcionales (laboratorio)

**Prefijos datos:** `PHASE5-VEND`, `PHASE5-CUST`, `PHASE5-LAB-001`  
**Producto:** almacenable (`consu` + `is_storable=True`)

### Flujo ejecutado

```
Compra (3 uds × 10 000) → Recepción → Factura proveedor → Pago
    → Cotización → Confirmación → Entrega (1 ud) → Factura cliente → Cobro
```

### Resultados

| Paso | Estado | Evidencia |
|------|--------|-----------|
| RFQ/PO | ✅ | `draft` → `purchase` |
| Recepción | ✅ | picking `done` |
| Factura proveedor | ✅ | `FACTU/2026/06/0003` — 35 400 DOP — `posted` |
| Pago proveedor | ✅ | `payment_state: paid` |
| Cotización | ✅ | `draft` |
| Confirmación venta | ✅ | `sale` |
| Entrega | ✅ | `done` |
| Factura cliente | ✅ | `INV/2026/00003` — 23 600 DOP — `posted` |
| Cobro cliente | ✅ | `payment_state: paid` |

### Asientos contables

| Documento | Líneas | Balanceado | Total |
|-----------|--------|------------|-------|
| FACTU/2026/06/0003 | 3 | ✅ | 35 400.00 |
| INV/2026/00003 | 3 | ✅ | 23 600.00 |

### Inventario

| Métrica | Valor |
|---------|-------|
| Antes | 0.0 |
| Después recepción | +3.0 |
| Después entrega | 2.0 |
| Delta neto flujo | +2.0 (compra 3 − venta 1) ✅ |

### Reportes verificados disponibles post-flujo

- Trial Balance
- General Ledger
- Balance sheet (formato RD `l10n_do_bs`)
- Profit and loss (formato RD `l10n_do_pl`)

---

## Bloque F — Reportes contables

| Reporte solicitado | Disponible | Nombre en sistema |
|--------------------|------------|-------------------|
| Balance General | ✅ | Balance Sheet + `l10n_do_bs` |
| Estado de Resultados | ✅ | Profit and Loss + `l10n_do_pl` |
| Balance de Comprobación | ✅ | Trial Balance |
| Mayor General | ✅ | General Ledger |
| Libro Diario | ✅ | Journal Report |
| Flujo de Caja | ✅ | Cash Flow Statement |
| Antigüedad C×C | ✅ | Aged Receivable |
| Antigüedad C×P | ✅ | Aged Payable |
| Ganancia por producto | ⚠️ | No como `account.report` estándar |
| Valoración de Inventario | ⚠️ | Reporte dedicado no en `account.report` |
| Movimientos de Inventario | ⚠️ | Vistas stock (no certificado en esta fase) |

**Total `account.report` instalados:** 25

---

## Matriz contable (Bloque J parcial)

| Área | Estado |
|------|--------|
| Plan contable | PASS |
| Diarios | PASS |
| Cuentas clave | PASS CON OBSERVACIONES |
| Flujo E2E con pagos | PASS |
| Reportes EE estándar | PASS |

---

**Evidencia JSON:** `PHASE5_DAFC ok: true` — bloques A, C, D, E, F  
**Fiscal (impuestos, NCF, DGII):** [DOMINICAN_FISCAL_CERTIFICATION.md](DOMINICAN_FISCAL_CERTIFICATION.md)

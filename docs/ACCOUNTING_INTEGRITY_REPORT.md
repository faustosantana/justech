# Informe de integridad contable — Hellenia PROD

**Fecha:** 2026-07-01  
**Base:** `hellenia_prod`

---

## Checks automáticos

| Check | Resultado | Detalle |
|-------|-----------|---------|
| Asientos posted balanceados | **PASS** | 9/9 |
| YTD débito = crédito | **PASS** | 94,400.00 |
| Pagos sin `move_id` | **PASS** | 0 |
| Pagos draft con asiento | **PASS** | 0 |
| Retenciones sin cuenta | **PASS** | 0 |
| Retenciones sin línea GL | **PASS** | 0 |
| Retenciones sin factura | **PASS** | 0 |
| Conciliaciones huérfanas | **PASS** | 0 |
| NCF duplicados | **PASS** | 0 |
| Facturas posted sin NCF | **PASS** | 0 |
| Líneas AML huérfanas | **PASS** | 0 |

---

## Saldos por tipo de cuenta (posted)

| Tipo | Saldo RD$ |
|------|-----------|
| asset_cash | 17,560.00 |
| asset_current | 5,500.00 |
| asset_receivable | 47,200.00 |
| income | -60,000.00 |
| liability_non_current | -10,260.00 |
| **Suma algebraica** | **0.00** |

Ecuación período abierto: Activos **70,260** = Pasivos **10,260** + Resultado no cerrado **60,000**.

---

## Hallazgos

### Menores

1. **INV/2026/00003** — `payment_state=in_payment` con `amount_residual=0.00`. Montos cuadran; solo etiqueta de estado desactualizada.
2. **SMOKE P13.4 CF** — partner sin RNC en 5 facturas posted (riesgo fiscal, no contable).
3. **Sin operaciones proveedor** — CxP y 606 no ejercitados con datos reales.

### Críticos

**Ninguno** en integridad contable estructural (asientos, pagos, retenciones GL, conciliación).

---

## Inventario movimientos posted

| Documento | Tipo | Estado pago | Total | Residual | NCF |
|-----------|------|---------------|-------|----------|-----|
| INV/2026/00001 | out_invoice | not_paid | 11,800 | 11,800 | B0200009900 |
| INV/2026/00002 | out_invoice | not_paid | 11,800 | 11,800 | B0200009901 |
| INV/2026/00003 | out_invoice | in_payment | 11,800 | 0 | B0200009902 |
| INV/2026/00004 | out_invoice | not_paid | 11,800 | 11,800 | B0200009903 |
| INV/2026/00005 | out_invoice | not_paid | 11,800 | 11,800 | B0200009904 |
| INV/2026/00006 | out_invoice | paid | 11,800 | 0 | B0200009905 |
| PBNKD/2026/00001 | entry | — | 5,000 | 0 | — |
| PBNKD/2026/00002 | entry | — | 6,800 | 0 | — |
| PBNKD/2026/00003 | entry | — | 11,800 | 0 | — |

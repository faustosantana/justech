# Matriz de elegibilidad 623

Una retención entra al 623 si cumple **todas**:

| # | Criterio | Campo / fuente |
|---|----------|----------------|
| 1 | Empresa del reporte | `company_id` |
| 2 | Fecha retención en período | `justech.payment.withholding.line.date` o stamp `justech_do_gov_retention_date` |
| 3 | Importe > 0 | `amount` / `justech_do_gov_withholding_amount` |
| 4 | Catálogo Gobierno | `affects_623` **o** código en `RET-GOB-5`, `wh_isr_gov`, `RET5%` |
| 5 | Factura cliente publicada | `account.move` out_invoice posted vinculada |
| 6 | No anulada | estado fiscal ≠ cancelled |
| 7 | No excluida manualmente | `justech_do_include_in_dgii` / exclusion_reason |

**No excluye:** conciliación bancaria pendiente (`treasury_bank_state=bank_pending`).

## Caso PBNK1 / FC/2026/00208

| Criterio | Resultado |
|----------|-----------|
| Elegible | **Sí** |
| Motivo | RET5% alineada a 623, amount 239, fecha 2026-07-13 |
| Acción | Ninguna — aparece como válida al Cargar período |
| Banco | Pendiente — **no bloquea** 623 |

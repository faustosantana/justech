# Fase 19 — Estado campos faltantes post-P0

Actualización respecto a `docs/DGII_MISSING_FIELDS_BACKLOG.md` tras implementar campos P0.

## Resueltos (P0)

| Campo | Estado |
|-------|--------|
| `justech_do_ncf` | ✅ Existía en `justech_l10n_do_ncf` |
| `justech_do_partner_id_type` | ✅ Implementado Fase 19 |
| `justech_do_ncf_modified` | ✅ Implementado Fase 19 |
| `justech_do_dgii_line_status` | ✅ Implementado Fase 19 |
| `justech_do_ncf_cancel_type` | ✅ Implementado Fase 19 |
| `dgii_withholding_code` | ✅ Implementado Fase 19 en catálogo |

## Pendientes para exportador 606 completo (P1)

| Campo | Impacto 606 |
|-------|-------------|
| `justech_do_expense_type_606` | Columna D — actualmente default `02` |
| `justech_do_payment_method_dgii` | Columna Z — inferida desde pagos |

## Pendientes P2 (columnas avanzadas 606)

- `justech_do_itbis_proportionality` (col P)
- `justech_do_itbis_cost` (col Q)
- `justech_do_itbis_advance` (col R)
- `justech_do_itbis_perceived_purchase` (col S)
- `justech_do_isr_perceived_purchase` (col V)
- `justech_do_isc_amount` (col W)
- `justech_do_legal_tip` (col Y)

## Pendientes otros formatos

### 607 Ventas

- `justech_do_income_type_607`
- `justech_do_sale_payment_breakdown` (cols R–X)
- Campos percepción/retención ventas

### 608 Anulados

- Exportador usa `justech_do_ncf_cancel_type` ✅ (campo listo)
- Falta exportador 608 layout oficial

### 609 Pagos exterior

- Todos los campos `justech_do_foreign_*`

### 623 Retenciones Estado

- Campos `justech_do_state_*`

### ITBIS / Norma 2-05

- ITBIS IMPORTACION aduanas
- Norma 2-05 exportador (campo identificación retención parcialmente cubierto vía `dgii_withholding_code`)

## Listo para siguiente fase

Con P0 implementado:

1. **607 exportador** — requiere P1 desglose formas de venta
2. **608 exportador** — campos P0 suficientes para piloto
3. **Norma 2-05** — `dgii_withholding_code` disponible

## Producción

**NO promover** hasta:

- TEST PASS script Fase 19
- Validación contable manual del Excel 606
- Aprobación explícita del cliente

# Plan de migración — Índice único NCF v2.0 (SQL)

**Estado:** DOCUMENTADO — **NO APLICAR** sin aprobación explícita del propietario.

## Contexto

| Capa | Estado Sprint 2 |
|------|-------------------|
| Python duplicados v2.0 | ✅ Activo (`ncf_duplicate_service` + `duplicate_scope`) |
| Índice SQL v1 | ⚠️ Activo — `(company_id, justech_do_ncf)` en posted |

El índice v1 impide que dos documentos **posted** de la misma empresa compartan el mismo
string NCF, incluso cuando pertenecen a módulos fiscales distintos (venta vs compra con
emisor distinto). La auditoría v2.0 demostró que 6 de 10 “duplicados” v1 eran falsos positivos.

## Objetivo v2.0

Permitir coexistencia fiscalmente válida de:

- Venta `B01…` emitido por la empresa
- Compra con NCF del proveedor (mismo string, distinto emisor RNC)

Mantener unicidad real:

- **Ventas:** `(company_id, move_type ∈ ventas, justech_do_ncf)`
- **Compras:** `(company_id, move_type ∈ compras, partner_id, justech_do_ncf)`

## Script propuesto (NO EJECUTAR)

```sql
-- PRE: backup completo BD + validación duplicados v2.0 en lab

DROP INDEX IF EXISTS account_move_justech_do_ncf_company_uniq;

CREATE UNIQUE INDEX account_move_justech_do_ncf_sale_uniq
ON account_move (company_id, justech_do_ncf)
WHERE state = 'posted'
  AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
  AND justech_do_ncf_voided IS NOT TRUE
  AND move_type IN ('out_invoice', 'out_refund', 'out_receipt');

CREATE UNIQUE INDEX account_move_justech_do_ncf_purchase_uniq
ON account_move (company_id, partner_id, justech_do_ncf)
WHERE state = 'posted'
  AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
  AND justech_do_ncf_voided IS NOT TRUE
  AND move_type IN ('in_invoice', 'in_refund', 'in_receipt');
```

## Pre-requisitos antes de aplicar

1. Ejecutar `find_duplicate_groups_v2()` en **justech_ncf_lab** y **clon justech_dev** — 0 grupos reales pendientes de decisión fiscal.
2. Validar histórico: GL, conciliaciones, pagos sin cambio.
3. Aprobación escrita del propietario.
4. Ventana de mantenimiento en lab → erp.justech.do clon → nunca directo en Producción.

## Rollback SQL

```sql
DROP INDEX IF EXISTS account_move_justech_do_ncf_sale_uniq;
DROP INDEX IF EXISTS account_move_justech_do_ncf_purchase_uniq;

CREATE UNIQUE INDEX IF NOT EXISTS account_move_justech_do_ncf_company_uniq
ON account_move (company_id, justech_do_ncf)
WHERE state = 'posted'
  AND justech_do_ncf IS NOT NULL AND justech_do_ncf != '';
```

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Duplicados reales ya en histórico | Auditoría v2.0 + resolución manual previa |
| ORM `init()` recrea índice v1 | Actualizar `account_move.init()` en mismo release |
| Performance inserts | Índices parciales acotados por move_type |

## Decisión

**Esperar aprobación explícita.** Sprint 2 cierra con Python v2.0 + este plan documentado.

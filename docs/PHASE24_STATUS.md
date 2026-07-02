# Estado Fase 24 — Reportes Justech

**Última actualización:** 2026-07-02 (Fase 24.2 oficialización cotización v19.0.2.0.0)

---

## Fase 24.1 — Cotización (TEST → PROD paralelo)

| Ítem | Estado |
|------|--------|
| Módulo `justech_report_design` | ✅ v`19.0.1.1.6` en TEST |
| Aprobación visual | ✅ **Aprobado** (VIS-001 cerrado) |
| Flujo vertical 24.1H | ✅ CONDICIONES / FIRMAS separados |
| Plan migración PROD paralelo | ✅ `docs/PHASE24_1_PROD_PARALLEL_MIGRATION_PLAN.md` |
| Ejecución PROD paralelo | ✅ **Completada** 2026-07-02 — v`19.0.1.1.6` en `hellenia_prod` |
| Evidencia PROD | `evidence/phase24-1-prod-parallel/` |
| Formato oficial cotización | ✅ **Implementado** 24.2 — v`19.0.2.0.0` (pendiente despliegue TEST/PROD) |

---

## Fase 24.2 — Oficialización cotización (solo cotizaciones)

| Ítem | Estado |
|------|--------|
| Condiciones empresa → `note` al crear | ✅ `models/sale_order.py` |
| PDF solo `doc.note` (sin XML quemado) | ✅ template QWeb |
| `sale.action_report_saleorder` → diseño Justech | ✅ `data/report_official_data.xml` |
| Respaldo estándar en menú | ✅ `action_report_saleorder_backup` |
| Rollback documentado | ✅ `docs/PHASE24_2_OFFICIAL_QUOTATION_ROLLBACK.md` |
| Validación automatizada | ✅ `scripts/phase24-2-official-quotation-test.py` |
| Despliegue TEST/PROD | ✅ v`19.0.2.0.1` — corrección 24.2A PROD (2026-07-02) |

### Marco acordado (24.2 cotización oficial)

- **Cotización oficial** bajo `custom/justech_report_design` v19.0.2.0.0
- Botón **Cotización en PDF** → diseño Justech
- Respaldo **Cotización en PDF (Respaldo)** → `sale.report_saleorder`
- **Sin xpath** sobre reporte estándar desde justech_report_design
- **Sin tocar** facturas, compras, inventario, pagos, DGII

### Fuera de alcance 24.2 (otros documentos)

- Facturas
- Notas de crédito
- Recibos de pago
- Órdenes de compra / RFQ
- Albaranes / picking
- Portal / correo heredan `sale.action_report_saleorder` (diseño Justech tras despliegue)

---

## Siguiente acción

1. Desplegar `-u justech_report_design` en **hellenia_test** y ejecutar `phase24-2-official-quotation-test.py`
2. Tras PASS TEST: autorizar despliegue PROD
3. Informar usuarios: **Cotización en PDF** = diseño nuevo; **Respaldo** = diseño anterior

**Doc implementación:** `docs/PHASE24_2_OFFICIAL_QUOTATION.md`  
**Rollback:** `docs/PHASE24_2_OFFICIAL_QUOTATION_ROLLBACK.md`

---

## Referencias rápidas

| Recurso | Ruta |
|---------|------|
| ZIP cotización | `packages/phase24-1-hellenia-quotation-review.zip` |
| Propuesta 24.2 | `docs/PHASE24_2_JUSTECH_REPORT_DESIGN_PROPOSAL.md` |
| Plan PROD paralelo | `docs/PHASE24_1_PROD_PARALLEL_MIGRATION_PLAN.md` |
| Checklist ejecución PROD | `packages/phase24-1-hellenia-quotation-review/PROD_PARALLEL_MIGRATION_CHECKLIST.md` |
| Checklist PROD (legado) | `packages/phase24-1-hellenia-quotation-review/PROD_PROMOTION_CHECKLIST.md` |
| Oficialización 24.2 | `docs/PHASE24_2_OFFICIAL_QUOTATION.md` |
| Rollback 24.2 | `docs/PHASE24_2_OFFICIAL_QUOTATION_ROLLBACK.md` |
| Rama Git | `cursor/phase24-2-official-quotation-dd85` |

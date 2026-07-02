# Estado Fase 24 — Reportes Justech

**Última actualización:** 2026-07-02 (aprobación visual v19.0.1.1.6)

---

## Fase 24.1 — Cotización (TEST → PROD paralelo)

| Ítem | Estado |
|------|--------|
| Módulo `justech_report_design` | ✅ v`19.0.1.1.6` en TEST |
| Aprobación visual | ✅ **Aprobado** (VIS-001 cerrado) |
| Flujo vertical 24.1H | ✅ CONDICIONES / FIRMAS separados |
| Plan migración PROD paralelo | ✅ `docs/PHASE24_1_PROD_PARALLEL_MIGRATION_PLAN.md` |
| Ejecución PROD | ⛔ **Bloqueada** — pendiente autorización final |
| Formato oficial (reemplazo estándar) | ⛔ **No autorizado** — fase futura |

---

## Fase 24.2 — Localización visual de reportes Justech

| Ítem | Estado |
|------|--------|
| Enfoque paquete central | ✅ **Aprobado** |
| Propuesta técnica | ✅ `docs/PHASE24_2_JUSTECH_REPORT_DESIGN_PROPOSAL.md` |
| Implementación | ⛔ **Bloqueada** hasta OK visual 24.1 |

### Marco acordado (24.2)

- **Localización visual** de reportes impresos bajo `custom/justech_report_design`
- Reportes **paralelos primero** — menú `Justech — …` convive con estándar Odoo
- **Diseño común** compartido (header, banda, tablas, footer)
- **SCSS común** en `web.report_assets_common`
- **Paperformat común** Justech (variante compacta para cotización si aplica)
- **Sin xpath frágiles** — templates propios + `web.html_container`
- **Sin PROD** hasta checklist explícito
- **Sin reemplazar** reportes estándar hasta aprobación por documento

### Fuera de alcance hasta nueva instrucción

- Facturas
- Notas de crédito
- Recibos de pago
- Órdenes de compra / RFQ
- Albaranes / picking
- Portal PDF
- Promoción a PROD

### Primera oleada de implementación (cuando se desbloquee)

1. Refactor fundación: partials QWeb comunes + SCSS base unificado
2. Cotización 24.1 migrada al esqueleto común
3. Menú: `Justech — Cotización` (+ pedido venta si se define en diseño)

---

## Siguiente acción

**Responsable:** autorizar ejecución del plan PROD paralelo (`docs/PHASE24_1_PROD_PARALLEL_MIGRATION_PLAN.md`).

**Agente / desarrollo:** en espera de `APPROVE_PROMOTION=1` o autorización escrita equivalente.

Tras instalación PROD paralela:

1. Validar cotización real + reporte estándar
2. Monitoreo 48h
3. Decisión futura: formato oficial (Fase 24.1I — no planificada aún)

---

## Referencias rápidas

| Recurso | Ruta |
|---------|------|
| ZIP cotización | `packages/phase24-1-hellenia-quotation-review.zip` |
| Propuesta 24.2 | `docs/PHASE24_2_JUSTECH_REPORT_DESIGN_PROPOSAL.md` |
| Plan PROD paralelo | `docs/PHASE24_1_PROD_PARALLEL_MIGRATION_PLAN.md` |
| Checklist ejecución PROD | `packages/phase24-1-hellenia-quotation-review/PROD_PARALLEL_MIGRATION_CHECKLIST.md` |
| Checklist PROD (legado) | `packages/phase24-1-hellenia-quotation-review/PROD_PROMOTION_CHECKLIST.md` |
| Rama Git | `cursor/phase24-1h-vis001-border-fix-dd85` |

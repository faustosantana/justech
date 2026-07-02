# Estado Fase 24 — Reportes Justech

**Última actualización:** 2026-07-02

---

## Fase 24.1 — Cotización (TEST)

| Ítem | Estado |
|------|--------|
| Módulo `justech_report_design` | ✅ Desplegado en TEST |
| Validación automática | ✅ `pass: true` (v19.0.1.1.4) |
| Auditoría 24.1G | ✅ VIS-001 cerrado — `ready_for_official: true` (técnico) |
| Paquete revisión | ✅ `packages/phase24-1-hellenia-quotation-review.zip` (regenerado) |
| Aprobación visual | ⏳ **Pendiente — revisar ZIP regenerado** |
| PROD | ⛔ Bloqueado |

**Bloqueante para código nuevo:** revisión visual final del ZIP 24.1.

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

**Responsable:** revisar visualmente `packages/phase24-1-hellenia-quotation-review.zip`

**Agente / desarrollo:** en espera — sin commits de implementación 24.2.

Tras OK visual:

1. Desbloquear Oleada 1 (fundación + cotización)
2. Mantener factura/compra/pago/inventario en planificación únicamente

---

## Referencias rápidas

| Recurso | Ruta |
|---------|------|
| ZIP cotización | `packages/phase24-1-hellenia-quotation-review.zip` |
| Propuesta 24.2 | `docs/PHASE24_2_JUSTECH_REPORT_DESIGN_PROPOSAL.md` |
| Checklist PROD | `packages/phase24-1-hellenia-quotation-review/PROD_PROMOTION_CHECKLIST.md` |
| Rama Git | `cursor/phase24-1-report-design-dd85` |

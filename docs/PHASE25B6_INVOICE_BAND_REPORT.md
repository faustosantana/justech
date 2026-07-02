# Fase 25B.6 — Informe header fiscal definitivo

**Estado:** `PENDING_USER_VISUAL_APPROVAL`  
**Módulo:** `justech_report_design` v`19.0.3.7.0`  
**Rama:** `cursor/phase25b6-invoice-band-dd85`

---

## Qué se modificó (solo header fiscal)

| Cambio | Detalle |
|--------|---------|
| Estructura | Eliminadas tablas anidadas; bloque fiscal con `div` + `float` (sin celdas visibles) |
| Altura banda | Restaurado padding cotización (`11px 14px`); `line-height: 1.22` |
| Distribución | 2 columnas 46% + 46% con 8% de aire entre ellas |
| Alineación | Etiquetas `inline-block` 148px; valores en columna común |
| NCF | Etiqueta normal; valor con `jt-inv-ncf-strong` solo si NCF real |
| Separador | Solo línea FACTURA \| meta (igual `jt-hq-band-num` cotización) |

**Archivos:** `justech_invoice_template.xml`, `hellenia_invoice.scss`, `__manifest__.py`

---

## Sin regresiones

No se tocó: logo, empresa, cliente, pago, vendedor, tabla, totales, footer, firmas, lógica fiscal, DGII, cálculos.

---

## Evidencia

`evidence/phase25b6-invoice-band/` · ZIP: `packages/phase25b6-invoice-band/phase25b6-invoice-band.zip`

Regenerar: `bash scripts/run-phase25b6-invoice-band-test.sh`

---

## Auditoría visual (vs. cotización)

- Banda más compacta que 25B.5: sí  
- Sin apariencia de tabla interna: sí  
- Columnas 3+3 balanceadas con aire: sí  
- Etiquetas/valores alineados: sí  

**Pendiente:** aprobación visual del usuario.

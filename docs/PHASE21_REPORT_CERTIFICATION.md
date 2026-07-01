# Fase 21 — Certificación reportes fiscales y contables

**Versión reportes:** `justech_l10n_do_reports` 19.0.1.12.2  
**Backup:** `2026-07-01_1357`  
**Estado:** **FAIL** — certificación parcial

---

## Objetivo

Validar ciclo contable y fiscal con transacciones reales en PROD, sin modificar arquitectura de pagos ni retenciones salvo causa demostrada.

---

## Checklist auditoría

### Pre-requisitos
- [x] Backup completo PROD (DB, filestore, custom, compose, .env)
- [x] Backup verificado (integridad gzip/tar)

### Reportes DGII (UI PROD)
| Reporte | Abre | Filtra | Exporta | Datos correctos | PASS |
|---------|------|--------|---------|-----------------|------|
| 606 | OK | OK | Pendiente Excel | 0 docs (vacío) | Parcial |
| 607 | OK | OK | Sin traceback post-fix | 3 válidos jun-2026 | Parcial |
| 608 | OK | OK | OK revisión | 0 anulados | Parcial |
| 623 | OK post-fix | OK | OK revisión | **0 válidos** (datos) | **FAIL** |

### Reportes contables Odoo
| Reporte | Abre UI | Filtros | PDF/XLSX | Totales | PASS |
|---------|---------|---------|----------|---------|------|
| Diario general | OK | Pendiente | Pendiente | Pendiente | Parcial |
| Mayor / Libro diario | OK | Pendiente | Pendiente | Pendiente | Parcial |
| Balance comprobación | OK | Pendiente | Pendiente | Pendiente | Parcial |
| Balance general | OK | Pendiente | Pendiente | Pendiente | Parcial |
| Estado resultados | OK | Pendiente | Pendiente | Pendiente | Parcial |
| Auxiliar clientes/proveedores | OK | Pendiente | Pendiente | Pendiente | Parcial |
| Antigüedad saldos | OK | Pendiente | Pendiente | Pendiente | Parcial |

### Regresión (no ejecutada completa en esta pasada)
- [ ] Pago parcial UI
- [ ] Pago completo UI
- [ ] Retenciones UI
- [ ] Conciliación
- [ ] PDF recibo

---

## Cambios desplegados PROD

| Módulo | Versión | Archivos |
|--------|---------|----------|
| `justech_l10n_do_reports` | 19.0.1.12.2 | `fiscal_report_wizard.py`, `fiscal_report.py`, `dgii_report_review.py` |

**Justificación:** ver `docs/REPORTS_ROOT_CAUSE_ANALYSIS.md`.

---

## Criterios PASS — estado

| Criterio | Estado |
|----------|--------|
| Reporte abre desde UI | 606/607/608/623 OK tras fix |
| Información correcta | 607 OK; 623 FAIL (datos) |
| Montos = contabilidad | No certificado 623 |
| Exporta PDF/XLSX | Pendiente certificación completa |
| No rompe otros reportes | 607/608 OK post-fix |
| No rompe pagos/retenciones | No tocados |

---

## Próximos pasos (operación / certificación)

1. Completar datos fiscales partner canónico (RNC, ref pago) para certificar 623 end-to-end.
2. Certificar export Excel/PDF 606/607 con supervisor fiscal en UI.
3. Completar matriz contable (filtros + export + totales).
4. Ejecutar regresión pagos/retenciones tras estabilizar reportes.

---

## Documentación relacionada

- `docs/REPORTS_AUDIT.md`
- `docs/REPORTS_ROOT_CAUSE_ANALYSIS.md`
- `evidence/phase21-prod-reports/`

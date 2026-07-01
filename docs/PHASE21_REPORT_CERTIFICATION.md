# Fase 21 — Certificación reportes fiscales y contables

**Versión reportes:** `justech_l10n_do_reports` 19.0.1.12.2  
**Backup:** `backups/hellenia-prod/2026-07-01_1357`  
**Fecha certificación:** 2026-07-01  
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
| 606 | OK | OK | OK revisión | 0 docs (vacío) | Parcial |
| 607 | OK | OK | OK post-fix | 3 válidos jun-2026 | Parcial |
| 608 | OK | OK | OK revisión | 0 anulados | Parcial |
| 623 | OK post-fix | OK | OK revisión | **0 válidos** (datos) | **FAIL** |

### Reportes contables Odoo
| Reporte | Abre UI | Filtros | PDF/XLSX btn | Totales SQL | PASS |
|---------|---------|---------|--------------|-------------|------|
| Diario general | OK | Pendiente | Visible | Pendiente | Parcial |
| Mayor / Libro diario | OK | Pendiente | Visible | Pendiente | Parcial |
| Balance comprobación | OK | Pendiente | Visible | OK (70,800) | Parcial |
| Balance general | OK | Pendiente | Visible | Pendiente | Parcial |
| Estado resultados | OK | Pendiente | Visible | Pendiente | Parcial |
| Auxiliar clientes | OK | Pendiente | Visible | Pendiente | Parcial |
| Auxiliar proveedores | Pendiente | — | — | — | Pendiente |
| Antigüedad saldos | OK | Pendiente | Visible | Pendiente | Parcial |

### Regresión (no ejecutada completa)
- [ ] Pago parcial UI
- [ ] Pago completo UI
- [ ] Retenciones UI
- [ ] Conciliación
- [ ] PDF recibo

---

## Correcciones desplegadas PROD

| Módulo | Versión | Archivos | Justificación |
|--------|---------|----------|---------------|
| `justech_l10n_do_reports` | 19.0.1.12.2 | `fiscal_report_wizard.py` | Wizard rechazaba `report_type=623` |
| | | `fiscal_report.py` | Faltaba `_get_exportable_lines()` |
| | | `dgii_report_review.py` | Override filtro líneas válidas |

Detalle: `docs/REPORTS_ROOT_CAUSE_ANALYSIS.md`

**No modificados:** wizard pagos, retenciones, conciliación.

---

## Criterios PASS — estado

| Criterio | Estado |
|----------|--------|
| Reporte abre desde UI | 606/607/608/623 OK tras fix |
| Información correcta | 607 OK; 623 FAIL (datos) |
| Montos = contabilidad | 623 no certificado (540 vs 500; sin RNC) |
| Exporta PDF/XLSX | Botones visibles; descarga no certificada |
| No rompe otros reportes | 607/608/623 OK post-fix |
| No rompe pagos/retenciones | No tocados |

---

## Hallazgo 623 — decisión

| Aspecto | Conclusión |
|---------|------------|
| ¿Bug de código? | **No** — validación DGII opera correctamente |
| Bloqueo | Partner sin RNC; datos de prueba inconsistentes |
| Acción código | **Ninguna** (restricción Fase 21) |
| Acción operativa | Completar RNC partner canónico; transacción gobierno 5% limpia |

---

## Próximos pasos (operación)

1. Fusionar partners duplicados PROD (ids 21, 23 → 22) con autorización.
2. Crear transacción 623 válida: partner con RNC, `RET-GOB-5`, referencia pago.
3. Certificar descarga Excel 607/623 con rol supervisor fiscal.
4. Completar matriz contable: filtros + export real + auxiliar proveedores.
5. Ejecutar regresión pagos/retenciones tras estabilizar datos.

---

## Documentación relacionada

- `docs/REPORTS_AUDIT.md`
- `docs/REPORTS_ROOT_CAUSE_ANALYSIS.md`
- `evidence/phase21-prod-reports/`

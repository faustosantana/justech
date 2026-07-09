# PR: Fase A fiscal → development

**Título:** Fase A fiscal: FDP, clasificador DGII y 606/202606 sin errores

**Base:** `development`  
**Head:** `feature/fiscal-integration-phase-a`

**Crear PR:** https://github.com/faustosantana/justech/compare/development...feature/fiscal-integration-phase-a?expand=1

---

## Summary

Integración fiscal Fase A validada en `erp.justech.do` / `justech_dev` — **punto estable, sin cambios en Producción**.

- **Fiscal Data Provider** (`justech.do.fiscal.data.provider`): lectura unificada Adel/Justech/l10n_latam para NCF, tipos de ingreso/gasto, anulaciones y exclusiones. Elimina 90 errores «sin NCF» en 606/202606 (facturas Adel con NCF en `l10n_latam_document_number`).
- **Clasificador DGII parametrizable** (`justech_l10n_do_reports` 19.0.1.16.1): catálogo `justech.do.dgii.tax.classification` + servicio clasificador. Sin lógica por nombre de impuesto. ITBIS→N, ISC→W, CDT→X. Persistencia automática en upgrade.
- **606/202606 corregido**: 95 errores → **0 errores**, **90/90 facturas válidas** (período 202606, JUSTECH S.R.L.).
- **Evidencias**: `evidence/fiscal-integration/` (FDP-deploy, CLASSIFIER-closure-final, informes técnicos).
- **Roadmap y gate NCF**: `docs/ERP_ROADMAP.md`, `docs/FISCAL_INTEGRATION_PHASE_A.md`, `NCF_MOTOR_GATE_CHECKLIST.md`.

## Estado operativo (explícito)

| Aspecto | Estado |
|---------|--------|
| **Adel** (`l10n_do_accounting`) | ✅ **Sigue activo** — motor del histórico |
| **Motor NCF Justech** | ⛔ **Sigue desactivado** — `justech_do_fiscal_enabled=0` en todas las empresas |
| **Histórico financiero** | ✅ **Intacto** — 2.255 posted, 947 reconciles, 677 pagos, 1.504 NCF Adel |
| **606/202606** | ✅ **0 errores**, 90 válidos |
| **Producción** (`justgroup.app`) | ⛔ **Sin cambios** — despliegue solo en `erp.justech.do` dev |

## Commits incluidos (vs `development`)

- `253f522` — A-001 baseline Fase A
- `a665035` — DEV-1 install base+ncf
- `e8d31f0` — DEV-2 install reports
- `7c0672d` — stabilización backup/filestore
- `91b0123` — FDP + clasificador DGII parametrizable
- `4f5f4d1` — docs: resumen ejecutivo, roadmap, gate NCF

## Módulos afectados

- `justech_l10n_do_base` 19.0.1.7.0 — Fiscal Data Provider
- `justech_l10n_do_reports` 19.0.1.16.1 — Clasificador + exportadores 606–609/623
- `justech_l10n_do_ncf` — instalado, motor **OFF**

## Evidencia clave

- `evidence/fiscal-integration/CLASSIFIER-closure-final/CLOSURE_VALIDATE.json` — 28/28 PASS
- `evidence/fiscal-integration/PHASE_A_EXECUTIVE_SUMMARY.md`
- `evidence/fiscal-integration/NCF_MOTOR_GATE_CHECKLIST.md`
- `evidence/fiscal-integration/DGII_TAX_CLASSIFIER_TECHNICAL_REPORT.md`
- `evidence/fiscal-integration/FISCAL_DATA_PROVIDER_REPORT.md`

## Test plan

- [x] Healthcheck pre/post: 18/18 PASS
- [x] Histórico: posted/reconciles/pagos/NCF Adel sin cambio
- [x] 606/202606: 0 errores, columnas N/W/X correctas (5 facturas CDT)
- [x] 607: 74 válidos, 0 errores
- [x] 608/609/623: ejecutan sin excepción
- [x] Catálogo 154 clasificaciones persistido post-upgrade sin sync manual
- [ ] Revisión humana antes de merge
- [ ] **No activar motor NCF** hasta completar gate checklist

## Restricciones de este PR

- **No merge automático** — requiere aprobación explícita.
- **No activa** motor NCF Justech.
- **No despliega** a `justgroup.app`.
- **No toca** `main`.

## Próximo paso post-merge

Piloto NCF en lab aislado (`justech_ncf_lab`) según `NCF_MOTOR_GATE_CHECKLIST.md` — no activar `justech_do_fiscal_enabled` en dev operativo hasta gate P0 completo.

# Análisis de Brechas — Localización República Dominicana (NCF Tradicional)

**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente:** `hellenia_dev` — Odoo 19 Enterprise On-Premise (`19.0-20260619`)  
**Alcance:** Etapa 1 — NCF tradicional (`l10n_do` + `l10n_do_reports`)  
**Fecha:** 2026-06-30  
**Versión:** 3.0 — **Post Fase 5 DAFC**  
**Certificación:** [PHASE5_EXECUTIVE_SUMMARY.md](PHASE5_EXECUTIVE_SUMMARY.md)

---

## Resumen ejecutivo (con evidencia Fase 5)

| Categoría | Confirmado PASS | Confirmado FAIL | POR VALIDAR |
|-----------|----------------:|----------------:|------------:|
| Contabilidad RD (plan, diarios, flujo) | 5 | 0 | 0 |
| Impuestos ITBIS/retenciones | 4 | 0 | 0 |
| Documentos fiscales NCF | 0 | 4 | 0 |
| Reportes DGII 606/607/608 | 0 | 3 | 0 |
| eNCF / Infile | — | N/A (excluido) | — |

**Certificación:** `PHASE5_DAFC ok: true` — `scripts/certify-phase5-dafc.py`  
**Backup Fase 5:** `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0502`

---

## Metodología

| Fase | Actividad | Estado |
|------|-----------|--------|
| 1 | Revisión documentación oficial Odoo | ✅ |
| 2 | Revisión manifest/código `l10n_do` en imagen | ✅ |
| 3 | **Fase 5 DAFC — pruebas funcionales laboratorio** | ✅ **2026-06-30** |
| 4 | Actualización brechas con evidencia | ✅ |
| 5 | Decisión custom vs. estándar | ⏸️ Solo si go-live fiscal bloqueado |

---

## Clasificación de brechas (P0–P3)

### P0 — Bloqueante go-live fiscal DGII

| ID | Brecha | Evidencia Fase 5 | Acción |
|----|--------|------------------|--------|
| **G-02** | Framework `l10n_latam.document.type` ausente | `"l10n_latam_document_framework": false` — modelo no en registry | Evaluar upgrade plataforma o custom post-4 comprobaciones |
| **G-04** | Libros DGII 606/607/608 ausentes | XML IDs `l10n_do_reports.account_report_606/607/608` = MISSING | `hellenia_reports` o extensión solo si confirmado post-UAT |

### P1 — Importante (workaround temporal o desarrollo planificado)

| ID | Brecha | Evidencia Fase 5 | Acción |
|----|--------|------------------|--------|
| **G-01** | Secuencias NCF no operativas | `ncf_sequences_count: 0`, `l10n_do_sequence_codes: 0` | Ligado a G-02; manifest advierte desarrollo adicional |
| **G-05** | PDF factura layout DGII | No probado — sin NCF generado | Validar tras resolver G-01/G-02 |
| **G-07** | Identificación LATAM partners | `l10n_latam` ausente | Validar RNC en facturas B2B post-framework |

### P2 — Deseable

| ID | Brecha | Evidencia | Acción |
|----|--------|-----------|--------|
| **G-06** | Selección automática B01 vs B02 | No verificable sin tipos documento | Post G-02 |
| **G-08** | Propina 10% | Impuesto existe; no usado en lab | Validar si aplica rubro Hellenia |

### P3 — Cerrado / no bloqueante

| ID | Brecha | Evidencia | Estado |
|----|--------|-----------|--------|
| **G-09** | BD sin `account` | Resuelto Fase 3 | ✅ CLOSED |
| **G-00** | Backup SSH | Resuelto — backups automatizados | ✅ CLOSED |
| **E-flow** | Flujo contable E2E | PHASE5 lab: pagos/cobros OK | ✅ PASS |

---

## 1. Lo que Odoo cubre — CONFIRMADO (Fase 5)

| # | Capacidad | Módulo | Evidencia | Estado |
|---|-----------|--------|-----------|--------|
| O-02 | Plan contable RD | `l10n_do` | 289 cuentas, tipos NIIF | ✅ CONFIRMED |
| O-03 | ITBIS 18% ventas | `l10n_do` | `18% ITBIS` sale + default company | ✅ CONFIRMED |
| O-04 | ITBIS compras 16/9/8/18/exento | `l10n_do` | 37 impuestos | ✅ CONFIRMED |
| O-05 | Retenciones ISR/ITBIS | `l10n_do` | 12 retenciones negativas | ✅ CONFIRMED |
| O-06 | Posiciones fiscales | `l10n_do` | 11 posiciones | ✅ CONFIRMED |
| O-14 | Tax report ITBIS | `l10n_do` | `l10n_do.tax_report` | ✅ CONFIRMED |
| O-16 | Balance/P&G formato RD | `l10n_do_reports` | `l10n_do_bs`, `l10n_do_pl` | ✅ CONFIRMED |
| O-19 | Flujo compra-venta-contabilidad | `purchase`+`sale`+`account` | FACTU/0003 + INV/00003 balanceados | ✅ CONFIRMED |

---

## 2. Lo que Odoo NO cubre — CONFIRMADO FAIL (Fase 5)

| # | Capacidad | Evidencia | Estado |
|---|-----------|-----------|--------|
| O-07 | Secuencias NCF B01–B04 | 0 secuencias NCF | ❌ FAIL |
| O-08 | Asignación NCF al facturar | Sin campos fiscales en `account.move` | ❌ FAIL |
| O-09 | Tipo documento B01 | Sin `l10n_latam.document.type` | ❌ FAIL |
| O-10 | Tipo documento B02 | Idem | ❌ FAIL |
| O-16b | Libro compras 606 | XML ID missing | ❌ FAIL |
| O-16c | Libro ventas 607 | XML ID missing | ❌ FAIL |
| O-16d | Anulaciones 608 | XML ID missing | ❌ FAIL |

---

## 3. Fuera de alcance (confirmado documental — sin prueba)

| # | Capacidad | Motivo |
|---|-----------|--------|
| N-01 | eNCF / ECF | `l10n_do_edi` ausente en tarball |
| N-02 | Infile | Requiere eNCF |
| N-03 | XML DGII | eNCF |
| N-04 | Firma digital | eNCF |
| N-05 | E31–E34 | eNCF |
| N-06 | POS fiscal E2E | POS no instalado (por diseño) |

---

## 4. Matriz decisión custom vs. estándar

| Escenario | Decisión Fase 5 |
|-----------|-----------------|
| Contabilidad operativa DEV | ✅ Continuar sin custom |
| Go-live fiscal DGII | ❌ Bloqueado hasta G-02 + G-04 |
| Custom `hellenia_account` | ⏸️ Solo tras 4 comprobaciones + brecha demostrada |
| Upgrade plataforma / saas-19.3 | Evaluar si trae `l10n_latam_invoice_document` |

---

## 5. Veredicto vinculado

**CONTINUAR_CON_RESERVA_FISCAL** — Ver [PHASE5_EXECUTIVE_SUMMARY.md](PHASE5_EXECUTIVE_SUMMARY.md)

La implementación **puede continuar** en DEV para fases operativas.  
La implementación **debe detenerse** para **go-live fiscal PROD** hasta cerrar P0.

---

## 6. Referencias

| Documento | Relación |
|-----------|----------|
| [DGII_FISCAL_ARCHITECTURE.md](DGII_FISCAL_ARCHITECTURE.md) | **Arquitectura fiscal integral DGII** — diseño multi-fase (sin MVP) |
| [DOMINICAN_ACCOUNTING_CERTIFICATION.md](DOMINICAN_ACCOUNTING_CERTIFICATION.md) | Bloques contables A,C,D,E,F |
| [DOMINICAN_FISCAL_CERTIFICATION.md](DOMINICAN_FISCAL_CERTIFICATION.md) | Bloques fiscales B,G,H |
| [ODOO19_OFFICIAL_MODULE_INVENTORY.md](ODOO19_OFFICIAL_MODULE_INVENTORY.md) | Inventario completo módulos oficiales |
| [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) | Diseño NCF tradicional |
| [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md) | Plan TC histórico — superseded por DAFC Fase 5 |

---

**Versión:** 3.0  
**Mantenido por:** Justech — Consultoría Odoo Enterprise  
**Próximo paso:** Aprobación explícita para fase siguiente (POS u otra); no go-live fiscal sin cerrar P0

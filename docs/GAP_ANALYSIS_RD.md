# Análisis de Brechas — Localización República Dominicana (NCF Tradicional)

**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente:** `hellenia_dev` — Odoo `19.0+e-20260619`  
**Alcance:** Etapa 1 — NCF tradicional (`l10n_do` + `l10n_do_reports`)  
**Fecha:** 2026-06-30  
**Versión:** 1.0  
**Estado:** **Hipótesis pre-validación — nada confirmado hasta ejecutar pruebas**

---

## Propósito

Este documento consolida **hipótesis de brechas** entre lo que Odoo oficial declara cubrir, lo que Hellenia requiere, y lo que probablemente necesite desarrollo custom. Todas las filas marcadas **POR VALIDAR** deben confirmarse o refutarse mediante el [Plan de Pruebas L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md).

> **Regla:** Ninguna capacidad se considera disponible hasta que el caso de prueba vinculado concluya en `PASS`.

---

## Metodología

| Fase | Actividad | Estado |
|------|-----------|--------|
| 1 | Revisión documentación oficial Odoo (19.0, saas-19.3) | ✅ Documental |
| 2 | Revisión manifest/código `l10n_do` en imagen DEV | ✅ Documental |
| 3 | Ejecución plan de pruebas TC-000–TC-030 | ⏸️ **Pendiente** |
| 4 | Actualización brechas con evidencia | ⏸️ **Pendiente** |
| 5 | Decisión custom vs. estándar | ⏸️ **Pendiente** |

**Plan de pruebas vinculado:** [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md)

---

## Resumen ejecutivo (hipótesis)

| Categoría | Ítems identificados | Confirmados | Brechas probables |
|-----------|--------------------:|------------:|------------------:|
| Cobertura oficial Odoo | 18 | 0 | — |
| Fuera de alcance Odoo (Etapa 1) | 6 | — | N/A |
| Desarrollo custom potencial | 8 | 0 | 8 POR VALIDAR |

**Riesgo principal (hipótesis):** El manifest `l10n_do` 19.0 incluye advertencia legacy indicando que las secuencias NCF pueden requerir terceros o desarrollo adicional. **TC-020** es la prueba crítica de desempate.

---

## 1. Lo que Odoo oficialmente cubre (POR VALIDAR)

> Fuente: [Documentación Odoo RD saas-19.3](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html), manifest `l10n_do` 19.0, [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md).  
> **Ningún ítem confirmado funcionalmente en build Hellenia hasta completar pruebas.**

| # | Capacidad oficial | Módulo | TC vinculado | Estado |
|---|-------------------|--------|--------------|--------|
| O-01 | Paquete fiscal mínimo DGII | `l10n_do` | TC-001, TC-009 | POR VALIDAR |
| O-02 | Plan contable RD (DGII/NIIF) | `l10n_do` | TC-007, TC-008 | POR VALIDAR |
| O-03 | Impuestos ITBIS venta 18%, 16%, 0%, exento | `l10n_do` | TC-010 | POR VALIDAR |
| O-04 | Impuestos ITBIS compra / crédito fiscal | `l10n_do` | TC-011 | POR VALIDAR |
| O-05 | Retenciones ITBIS e ISR | `l10n_do` | TC-012 | POR VALIDAR |
| O-06 | Posiciones fiscales (exenciones, retenciones) | `l10n_do` | TC-013 | POR VALIDAR |
| O-07 | Secuencias NCF precargadas (B01–B04, B11, B13, etc.) | `l10n_do` | TC-017 | POR VALIDAR |
| O-08 | Asignación NCF al confirmar factura | `l10n_do` | TC-020 | POR VALIDAR ⚠️ |
| O-09 | Tipos documento B01 Crédito Fiscal | `l10n_do` | TC-023 | POR VALIDAR |
| O-10 | Tipos documento B02 Consumo Final | `l10n_do` | TC-024 | POR VALIDAR |
| O-11 | Notas crédito B04 / débito B03 | `l10n_do` | TC-025, TC-026 | POR VALIDAR |
| O-12 | Comprobante proveedores informales B11 | `l10n_do` | TC-029 | POR VALIDAR |
| O-13 | Gastos menores B13 | `l10n_do` | TC-029 (parcial) | POR VALIDAR |
| O-14 | Tax report ITBIS (estructura declaración) | `l10n_do` | TC-002, TC-030 | POR VALIDAR |
| O-15 | Diarios con documentos fiscales (Use Documents) | `l10n_do` | TC-014, TC-015 | POR VALIDAR |
| O-16 | Reportes fiscales RD (606, 607, 608, IT-1) | `l10n_do_reports` | TC-003, TC-031 | POR VALIDAR |
| O-17 | Factura PDF con datos fiscales | `l10n_do` / `account` | TC-030 | POR VALIDAR |
| O-18 | Registro NCF proveedor en compras | `l10n_do` | TC-027 | POR VALIDAR |

---

## 2. Lo que Odoo NO cubre (Etapa 1 — confirmado documentalmente)

Estos ítems están **fuera del stack** `l10n_do` + `l10n_do_reports` por diseño de Odoo o decisión de proyecto. No requieren prueba funcional para confirmar exclusión.

| # | Capacidad | Motivo | Alternativa / Fase |
|---|-----------|--------|-------------------|
| N-01 | eNCF / ECF electrónico | Módulo separado `l10n_do_edi` | Fase futura eNCF |
| N-02 | Integración Infile (PSE) | Requiere `l10n_do_edi` + contrato Infile | [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) |
| N-03 | Transmisión XML a DGII | Solo vía eNCF | Fase futura |
| N-04 | Firma digital ECF | Solo `l10n_do_edi` | Fase futura |
| N-05 | Tipos E31–E34 electrónicos | Exclusivos eNCF | Fase futura |
| N-06 | POS con NCF integrado end-to-end | Requiere Fase 7 POS + validación B02 | Plan POS separado |

---

## 3. Brechas probables — desarrollo custom potencial Evidencia preliminar | TC | Prioridad | Impacto | Esfuerzo est. | Módulo custom |
|----|-------------------|---------------------|-----|-----------|---------|---------------|---------------|
| G-01 | **Secuencias NCF no operativas sin terceros** | Advertencia manifest `l10n_do` 19.0 | TC-020 | 🔴 P0 | Bloqueante go-live | 5–15 días | `hellenia_account` |
| G-02 | Framework documentos LATAM ausente/incompleto en 19.0 | `l10n_do` 19.0 sin dependencia `l10n_latam_invoice_document` (presente en saas-19.3) | TC-014, TC-017 | 🔴 P0 | Alto — UI documentos diferente | 3–10 días | `hellenia_account` |
| G-03 | Tipos NCF B14, B15, B16 no precargados | No declarados explícitamente en manifest 19.0 | TC-017 | 🟠 P1 | Medio — depende operación Hellenia | 2–5 días | `hellenia_account` |
| G-04 | Reportes 606/607/608/IT-1 incompletos o ausentes | Doc Odoo no lista explícitamente; foro sin confirmación | TC-031 | 🔴 P0 | Bloqueante declaraciones DGII | 5–20 días | `hellenia_reports` |
| G-05 | Formato PDF factura no cumple requisitos DGII impresos | Estándar Odoo puede diferir de layout RD exigido | TC-030 | 🟠 P1 | Medio — riesgo auditoría | 3–8 días | `hellenia_reports` |
| G-06 | Selección automática B01 vs B02 por R. RNC cliente | Comportamiento no documentado para 19.0 on-premise | TC-024 | 🟡 P2 | Bajo — workaround manual | 1–3 días | `hellenia_account` |
| G-07 | Campo RNC / tipo identificación LATAM incompleto en 19.0 | `l10n_latam_identification_type` evolución saas-19.3 | TC-006, TC-023 | 🟠 P1 | Medio — validación B2B | 2–5 días | `hellenia_account` |
| G-08 | Propina 10% (hospitalidad) — si aplica Hellenia | Declarado en manifest; uso real POR VALIDAR | TC-010 | 🟡 P2 | Bajo — rubro específico | 1–2 días | `hellenia_account` |

### Leyenda prioridad

| Nivel | Significado |
|-------|-------------|
| 🔴 P0 | Bloqueante — impide operación fiscal legal |
| 🟠 P1 | Importante — workaround manual posible temporalmente |
| 🟡 P2 | Deseable — mejora operativa o cumplimiento secundario |

### Leyenda esfuerzo estimado

Estimaciones orientativas para desarrollo custom con `_inherit` (sin modificar `enterprise/`). Se refinan post-UAT.

| Rango | Interpretación |
|-------|----------------|
| 1–3 días | Extensión menor — campo, constraint, reporte simple |
| 3–10 días | Extensión media — flujo documentos, lógica NCF |
| 10–20 días | Extensión mayor — reportes fiscales completos, integración |

---

## 4. Matriz de decisión custom vs. estándar

| Escenario post-pruebas | Decisión |
|------------------------|----------|
| TC-020 PASS — NCF asigna sin terceros | G-01 **cerrada** — usar estándar |
| TC-020 FAIL — NCF no asigna | G-01 **confirmada** — evaluar custom `hellenia_account` |
| TC-030 PASS — reportes 606/607/608/IT-1 completos | Usar estándar; G-04 **cerrada** |
| TC-031 FAIL — reportes ausentes/incompletos | G-04 **confirmada** — `hellenia_reports` |
| TC-014 FAIL — Use Documents no disponible | G-02 **confirmada** — investigar upgrade 19.3 o custom |
| Todos TC PASS | Etapa 1 sin custom fiscal — solo módulos Hellenia operativos |

**Regla de proyecto:** Custom solo tras brecha **demostrada** con evidencia TC. Ver [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) — *Estándar antes que custom*.

---

## 5. Brechas por área funcional

### 5.1 Instalación y módulos

| Aspecto | Odoo oficial (hipótesis) | Brecha | TC |
|---------|-------------------------|--------|-----|
| `l10n_do` auto_install con `account` | Sí — manifest | POR VALIDAR | TC-001 |
| `l10n_do_reports` requiere Enterprise | Sí — depende `account_reports` | POR VALIDAR | TC-003 |
| `l10n_do_edi` ausente en tarball 19.0 | Confirmado documental — no aplica Etapa 1 | N/A | TC-004 |

### 5.2 Empresa y plan contable

| Aspecto | Odoo oficial (hipótesis) | Brecha | TC |
|---------|-------------------------|--------|-----|
| País DO dispara localización | Sí — doc oficial | POR VALIDAR | TC-005 |
| RNC en empresa | Sí — doc saas-19.3 | POR VALIDAR en 19.0 | TC-006 |
| Plan contable template `do` | Sí — `l10n_do` | POR VALIDAR | TC-007 |

### 5.3 Impuestos

| Aspecto | Odoo oficial (hipótesis) | Brecha | TC |
|---------|-------------------------|--------|-----|
| ITBIS 18/16/0/exento ventas | Precargado — manifest | POR VALIDAR | TC-010 |
| ITBIS compra crédito fiscal | Precargado — manifest | POR VALIDAR | TC-011 |
| Retenciones ISR/ITBIS | Precargado — manifest | POR VALIDAR | TC-012 |
| Tax report ITBIS casillas DGII | `account_tax_report_data.xml` | POR VALIDAR | TC-031 |

### 5.4 NCF y documentos fiscales

| Aspecto | Odoo oficial (hipótesis) | Brecha potencial | TC |
|---------|-------------------------|------------------|-----|
| Secuencias B01, B02, B03, B04 | Declaradas manifest | POR VALIDAR operativas | TC-017, TC-020 |
| Rangos con vencimiento DGII | Doc saas-19.3 | POR VALIDAR en 19.0 | TC-018, TC-021 |
| NC referencia NCF origen | Doc saas-19.3 | POR VALIDAR | TC-025 |
| Advertencia manifest terceros | Texto en manifest 19.0 | **G-01** — riesgo alto | TC-020 |

### 5.5 Facturación y compras

| Aspecto | Odoo oficial (hipótesis) | Brecha potencial | TC |
|---------|-------------------------|------------------|-----|
| Factura B01 B2B | Doc oficial | POR VALIDAR | TC-023 |
| Factura B02 B2C | Doc oficial | POR VALIDAR | TC-024 |
| Factura proveedor + NCF entrada | Doc saas-19.3 | POR VALIDAR | TC-027 |
| Proveedor informal B11 | Manifest | POR VALIDAR | TC-029 |

### 5.6 Impresión y reportes

| Aspecto | Odoo oficial (hipótesis) | Brecha potencial | TC |
|---------|-------------------------|------------------|-----|
| PDF con NCF/RNC/ITBIS | Estándar localización | POR VALIDAR layout DGII — **G-05** | TC-030 |
| Libro ventas 607 | `l10n_do_reports` | POR VALIDAR — **G-04** | TC-031 |
| Libro compras 606 | `l10n_do_reports` | POR VALIDAR — **G-04** | TC-031 |
| Anulaciones 608 | `l10n_do_reports` | POR VALIDAR — **G-04** | TC-031 |
| Declaración IT-1 | Tax report + reports | POR VALIDAR — **G-04** | TC-031 |

---

## 6. Riesgos regulatorios (contexto, no brecha Odoo)

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Ley 32-23 migración obligatoria e-CF | Futuro — NCF papel con plazo DGII | Plan Fase eNCF independiente |
| Rangos NCF tradicionales DGII | Externo — trámite Hellenia | Configurar en Odoo post-autorización |
| Licencia Enterprise sin registrar en DEV | Trial expiration | Monitorear; registrar en go-live PROD |

---

## 7. Módulos custom Hellenia — rol previsto

| Módulo | Rol si brecha confirmada | Regla |
|--------|-------------------------|-------|
| `hellenia_account` | Extensiones NCF, documentos, impuestos, partners RD | Solo `_inherit` — nunca parchear `l10n_do*` |
| `hellenia_reports` | Reportes fiscales complementarios 606/607/608/IT-1 | Complementar, no duplicar `l10n_do_reports` |
| `justech_core` | Utilidades transversales | Sin lógica fiscal directa |

**Estado actual módulos custom:** Scaffolding sin lógica fiscal RD — ver `custom/hellenia_account/`, `custom/hellenia_reports/`.

---

## 8. Plan de actualización post-pruebas

Tras ejecutar [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md):

1. **Actualizar §1** — Cambiar filas POR VALIDAR → CONFIRMADO (PASS) o NO DISPONIBLE (FAIL).
2. **Confirmar/cerrar §3** — Brechas G-01 a G-08 con evidencia TC.
3. **Priorizar backlog custom** — Solo ítems G-xx confirmados.
4. **Emitir acta Fase 2** — Vincular a [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md).
5. **Decisión go/no-go** Etapa 1 NCF tradicional.

---

## 9. Referencias

| Documento | Relación |
|-----------|----------|
| [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md) | Plan de pruebas — fuente de verdad funcional |
| [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) | Diseño técnico NCF tradicional |
| [L10N-RD-READINESS.md](L10N-RD-READINESS.md) | Preparación pre-instalación |
| [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) | eNCF — fuera de alcance Etapa 1 |
| [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) | Fases implementación |

| Fuente externa | URL |
|----------------|-----|
| Odoo RD saas-19.3 | https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html |
| Manifest `l10n_do` 19.0 | https://github.com/odoo/odoo/blob/19.0/addons/l10n_do/__manifest__.py |

---

**Versión:** 1.0  
**Mantenido por:** Consultoría implementación Justech  
**Próximo paso:** Ejecutar TC-000 tras aprobación — actualizar este documento con resultados reales

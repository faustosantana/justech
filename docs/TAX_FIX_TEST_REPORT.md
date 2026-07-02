# Fase 13.2 — Reporte de corrección fiscal en TEST

**Fecha:** 2026-06-30 (UTC)  
**Entorno:** `hellenia_test` — https://test.hellenia.cloud  
**Rama:** `cursor/fiscal-fix-phase13-2-dd85`  
**Evidencia:** `evidence/phase13-2-diagnose-test.json`, `evidence/phase13-2-validate-test.json`

---

## Resumen ejecutivo

| Ítem | Resultado |
|------|-----------|
| Diagnóstico impuesto 15% en TEST | **PASS** — no detectado |
| Plan contable RD (`do`) | **PASS** — 289 cuentas |
| ITBIS 18% venta | **PASS** |
| Cotización nueva sin 15% | **PASS** — `[18.0]` |
| Facturas B01/B02 | **PASS** |
| Nota crédito B04 | **PASS** |
| Compras B11/B13 | **PASS** |
| Reportes 606/607/608 | **PASS** |
| PDF factura | **PASS** |
| Menús DGII en español | **PASS** |
| **Certificación TEST** | **PASS** |

---

## 1. Causa raíz del impuesto 15% (contexto producción)

En **PRODUCCIÓN** (`hellenia_prod`) se identificó la causa raíz antes de la corrección:

| Hallazgo | Valor inicial PROD |
|----------|-------------------|
| Plan contable | `generic_coa` (51 cuentas) |
| Impuestos activos | Solo 4 plantillas genéricas Odoo |
| Impuesto incorrecto venta | `account.1_sale_tax_template` — **15%** |
| Impuesto incorrecto compra | `account.1_purchase_tax_template` — **15%** |
| Producto afectado | "Prueba" con impuesto 15% |
| Impuesto por defecto compañía | `account_sale_tax_id` = 15% |

**Causa raíz:** La base de datos de producción se creó sin cargar el plan contable dominicano (`l10n_do` / chart `do`). Quedó el plan genérico de Odoo con impuestos plantilla del 15%, no el ITBIS RD del 18%.

**TEST no presentaba el problema** porque el plan `do` ya estaba cargado (38 impuestos, ITBIS 18% operativo).

---

## 2. Corrección aplicada en código (upgrade-safe)

### Scripts nuevos

| Script | Función |
|--------|---------|
| `scripts/diagnose-fiscal-taxes.py` | Diagnóstico formal: impuestos, plan, productos, causa raíz |
| `scripts/fix-fiscal-rd-configuration.py` | Carga plan `do`, desactiva 15%, remapea productos |
| `scripts/phase13-2-validate-fiscal.py` | Suite funcional 18 escenarios |
| `scripts/run-phase13-2-fiscal-fix.sh` | Orquestador TEST/PROD |

### Módulos Justech 19.0.1.2.0

- Reportes DGII en español con totales, trazabilidad (`generated_at`, `generated_by_id`)
- Detección ITBIS mejorada (nombre + tasa 8/9/16/18%)
- Menús y exportaciones CSV/Excel en español
- PDF: "Tipo de documento" en lugar de "Document Type"

---

## 3. Pruebas ejecutadas en TEST

Evidencia: `evidence/phase13-2-validate-test.json`

| # | Escenario | Estado | Detalle |
|---|-----------|--------|---------|
| 1 | Configuración impuestos | PASS | `active_15=0`, ITBIS 18% |
| 2 | Cotización nueva | PASS | Línea con `[18.0]`, sin 15% |
| 3 | Factura B01 | PASS | NCF `B0100020001`, ITBIS 18% |
| 4 | Factura B02 | PASS | NCF `B0200020113`, ITBIS 18% |
| 5 | Nota crédito B04 | PASS | NCF `B0400020018` |
| 6 | Compra B11 | PASS | `FACTU/2026/06/0105` |
| 7 | Gasto B13 | PASS | `FACTU/2026/06/0106` |
| 8 | Anulación + 608 | PASS | 2 líneas anuladas |
| 9 | Reporte 606 | PASS | 106 líneas |
| 10 | Reporte 607 | PASS | 156 líneas, total 452,037.56 |
| 11 | Reporte 608 | PASS | 2 líneas |
| 12 | PDF factura | PASS | 30,211 bytes |
| 13 | Español menú DGII | PASS | "Reportes DGII" |

---

## 4. Antes / después (TEST)

| Métrica | TEST antes | TEST después |
|---------|------------|--------------|
| Impuesto 15% activo | 0 | 0 |
| ITBIS 18% venta | Sí | Sí |
| Módulos Justech | 1.1.0 | 1.2.0 |
| Reportes con totales/trazabilidad | No | Sí |
| Menús DGII en español | Parcial | Sí |

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Secuencias PostgreSQL desincronizadas en TEST | Script `fix_seq.sql` aplicado antes de upgrade |
| Rangos NCF faltantes (B04) | Validación crea rango de prueba si no existe |
| Textos core Odoo en inglés | Documentado en `SPANISH_UX_VALIDATION.md`; menús Justech en ES |

---

## 6. Conclusión

**TEST: PASS** — La localización Justech, impuestos RD y reportes DGII funcionan correctamente. Se autoriza promoción a producción con el mismo procedimiento (`fix-fiscal-rd-configuration.py` + upgrade módulos 1.2.0).

**Pendiente producción:** Aplicar corrección fiscal (causa raíz 15% solo existía en `hellenia_prod`).

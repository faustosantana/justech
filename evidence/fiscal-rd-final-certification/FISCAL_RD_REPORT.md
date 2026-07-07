# FISCAL-RD-FINAL — Certificación definitiva módulo fiscal dominicano

**Fecha:** 2026-07-07  
**Entorno:** `hellenia_test` (PROD no tocado)  
**Módulos:** `justech_l10n_do_base` 19.0.1.5.0 · `justech_l10n_do_ncf` 19.0.1.6.0 · `justech_l10n_do_reports` 19.0.1.13.0

---

## Veredicto

| Área | TEST |
|------|------|
| 11 tipos NCF serie B | **PASS** |
| DGII 606/607/608/609/623 | **PASS** |
| Smoke integral | **PASS** |
| Impuestos huérfanos | **0** |

**Certificación TEST: PASS completo** para comprobantes tradicionales serie B y exportadores DGII core.

---

## Respuestas a las 6 preguntas

### 1. ¿El módulo fiscal RD quedó completamente terminado?

**Casi — sí para NCF serie B y DGII operativos.** En esta fase se implementaron los 5 tipos faltantes (B12, B14, B15, B16, B17), se cerró el campo `justech_do_income_type_607`, y se certificaron los 11 comprobantes + 5 formatos DGII en TEST.

**Queda fuera de alcance (no es deuda “Fase 2” del módulo base, sino producto separado):**
- **eNCF serie E** (E31–E47): comprobantes electrónicos con firma digital / EDI
- Formularios DGII adicionales: IT-1, IR-17, IR-2, IR-3, 624
- Columnas 606 opcionales avanzadas (proporcionalidad ITBIS, ISC detallado, propina legal automática)

### 2. ¿Qué comprobantes soporta?

| Prefijo | Nombre | Movimiento | Smoke TEST |
|---------|--------|------------|------------|
| B01 | Factura Crédito Fiscal | Venta | ✅ |
| B02 | Factura Consumo | Venta | ✅ |
| B03 | Nota de Débito | Venta | ✅ |
| B04 | Nota de Crédito | Venta NC | ✅ |
| B11 | Comprobante Compras | Compra | ✅ |
| B12 | Registro Único Ingresos | Venta | ✅ |
| B13 | Gastos Menores | Compra | ✅ |
| B14 | Regímenes Especiales | Venta | ✅ |
| B15 | Gubernamental | Venta | ✅ |
| B16 | Exportaciones | Venta | ✅ |
| B17 | Pagos al Exterior | Compra | ✅ |

Por comprobante: secuencia, rango, asignación automática, validación, expiración, PDF, reversión (B04), integración contable.

### 3. ¿Qué exportaciones DGII soporta?

| Formato | Función | TEST |
|---------|---------|------|
| **606** | Compras | ✅ Excel 11 líneas |
| **607** | Ventas | ✅ Excel 33 líneas |
| **608** | NCF anulados | ✅ (vacío si no hay anulaciones) |
| **609** | Pagos exterior | ✅ (vacío si no hay B17/extranjeros) |
| **623** | Retenciones 5% Estado | ✅ (vacío si no hay retenciones gov) |

Retenciones ITBIS/ISR: mapeadas vía `hellenia_account` + repartición impuestos Justech.

### 4. ¿Existe alguna funcionalidad pendiente?

**Sí, explícita y acotada:**

| Item | Tipo | Impacto |
|------|------|---------|
| eNCF E31–E47 | Producto futuro (`justech_l10n_do_edi`) | Clientes obligados a facturación electrónica |
| Campos 606 avanzados | Mejora exportador | Empresas con proporcionalidad ITBIS compleja |
| IT-1 / IR-17 / IR-2 / IR-3 | Formularios adicionales | Declaraciones fuera de 606–609 |
| Tests unitarios 609/623 | Cobertura | Playwright/regresión existe; unit tests Odoo pendientes |

**Eliminado en esta fase:** “Fase 2” para B12–B17, B14 NOT_IMPLEMENTED, income_type_607 pendiente.

### 5. ¿Puede instalarse en cualquier cliente dominicano?

**Sí**, siempre que:
- País compañía = DO
- `justech_do_fiscal_enabled = True`
- Catálogo de cuentas configurado (Justech COA o compatible)
- Rangos NCF activos por tipo usado
- Impuestos ITBIS/retenciones mapeados a cuentas

No depende de Hellenia: módulos en `custom/justech_l10n_do_*` son genéricos. `hellenia_account` aporta catálogo retenciones pero no bloquea instalación base.

### 6. ¿Lo certificarías como producto Justech listo para producción?

**Sí — para operación con NCF serie B + DGII 606/607/608/609/623.**

**Condición:** clientes que requieran **eNCF obligatorio** necesitan el módulo EDI (aún no desarrollado).

**No promover PROD Hellenia** hasta validar COA Justech en ese entorno (COA-3/COA-PROD separado).

---

## Cambios implementados

- `fiscal_document_type_data.xml`: B12, B14, B15, B16, B17
- `fiscal_document_type.py`: constantes SALE/PURCHASE/CONSUMER prefixes
- `account_move.py` (ncf): auto-NCF genérico compra/venta + in_refund
- `account_move.py` (reports): `justech_do_income_type_607`
- `dgii_607_exporter.py`: usa campo income type
- Tests extendidos + `scripts/fiscal-rd-final-certify-test.py`

## Evidencia

- `evidence/fiscal-rd-final-certification/ncf_all_types.json`
- `evidence/fiscal-rd-final-certification/dgii_all_formats.json`
- `evidence/fiscal-rd-final-certification/summary.json`

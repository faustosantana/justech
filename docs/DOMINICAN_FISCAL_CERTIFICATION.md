# Certificación Fiscal — República Dominicana (DAFC Bloques B, G, H)

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` — Odoo `19.0-20260619` Enterprise On-Premise  
**Fecha certificación:** 2026-06-30T05:04:50Z  
**Alcance:** `l10n_do` + `l10n_do_reports` — **sin** `l10n_do_edi`  
**Restricción:** Sin instalar módulos, sin modificar configuración.

---

## Resumen

| Bloque | Área | Estado |
|--------|------|--------|
| B | Impuestos y posiciones fiscales | **PASS** |
| G | Localización RD (`l10n_do`) | **PASS CON OBSERVACIONES** |
| H | Cumplimiento DGII | **PASS CON OBSERVACIONES** |

---

## Bloque B — Impuestos

**Total impuestos configurados:** 37  
**Impuesto venta por defecto:** 18% ITBIS  
**Impuesto compra por defecto:** 18% ITBIS

### ITBIS por tasa

| Tasa | Ventas | Compras |
|------|--------|---------|
| 18% | ✅ 18% ITBIS | ✅ 18% ITBIS (+ variantes serv/import) |
| 16% | — | ✅ 16% ITBIS |
| 9% | — | ✅ 9% ITBIS |
| 8% | — | ✅ 8% ITBIS |
| 0% / Exento | ✅ ITBIS Exempt | ✅ ITBIS Exempt |

### Retenciones (muestra verificada — 12 en total)

| Impuesto | Tasa | Uso |
|----------|------|-----|
| -100% ITBIS (N07-09) | -18% | purchase |
| -10% ISR Fee | -10% | purchase |
| -100% ITBIS (N01-11) | -18% | purchase |
| -27% ISR (L253-12) | -27% | purchase |
| -10% ISR Rent. | -10% | purchase |
| -5% ISR Gov. | -5% | sale |
| -2% ISR (N07-07) | -2% | purchase |
| -2% ISR Mat. | -2% | purchase |
| … | … | … |

### Posiciones fiscales (11)

1. DO Domestic  
2. P. Physical Services  
3. P. Legal Services  
4. P. Legal Surveillance  
5. Informal Supplier of Goods  
6. Outside Services  
7. Governmental  
8. Non-Profit Services  
9. Special Regimes  
10. Restaurants  
11. To Take Away  

**Conclusión B:** Maestro fiscal RD completo para ITBIS, exenciones y retenciones ISR/ITBIS. Sin modificación.

---

## Bloque G — Localización RD

### Módulos

| Módulo | Estado | Notas |
|--------|--------|-------|
| `l10n_do` | ✅ installed | Plan, impuestos, tax report |
| `l10n_do_reports` | ✅ installed | Balance y P&G formato RD |
| `l10n_do_check_printing` | ✅ installed | Cheques (no probado) |
| `l10n_do_edi` | ❌ absent | eNCF — fuera de alcance |

### Framework documentos fiscales

| Elemento | Evidencia | Estado |
|----------|-----------|--------|
| Modelo `l10n_latam.document.type` | No existe en BD/registry | ❌ **FAIL** |
| Secuencias NCF (`ir.sequence`) | 0 secuencias con nombre NCF | ❌ **FAIL** |
| Códigos secuencia `l10n_do` | 0 | ❌ **FAIL** |
| Campo NCF en `account.move` | Solo `ref` — sin `l10n_do_ncf` | ❌ **FAIL** |
| Tax Report ITBIS | `l10n_do.tax_report` → "Tax Report" | ✅ PASS |
| Balance RD | `l10n_do_reports.l10n_do_bs` | ✅ PASS |
| P&G RD | `l10n_do_reports.l10n_do_pl` | ✅ PASS |
| Libro compras 606 | XML ID ausente | ❌ **FAIL** |
| Libro ventas 607 | XML ID ausente | ❌ **FAIL** |
| Anulaciones 608 | XML ID ausente | ❌ **FAIL** |

### Advertencia manifest `l10n_do` 19.0

> *"Esta localización, aunque posee las secuencias para NCF, las mismas no pueden ser utilizadas sin la instalación de módulos de terceros o desarrollo adicional."*

**Evidencia Fase 5:** La advertencia se confirma operativamente — no hay secuencias NCF ni framework LATAM de documentos en el build on-premise `19.0-20260619`.

---

## Bloque H — DGII (evidencia, no hipótesis)

### ¿Qué cumple hoy?

| # | Capacidad | Evidencia |
|---|-----------|-----------|
| 1 | Plan contable RD DGII/NIIF | 289 cuentas cargadas |
| 2 | ITBIS 18/16/9/8/exento | 37 impuestos verificados |
| 3 | Retenciones ISR/ITBIS | 12 retenciones negativas en maestro |
| 4 | Posiciones fiscales sectoriales | 11 posiciones |
| 5 | Diarios fiscales/contables | INV, FACTU, CSH1, BNK1, STJ, CAMBI, TAX |
| 6 | Flujo compra-venta con ITBIS en facturas | FACTU/0003 + INV/00003 con 3 líneas balanceadas |
| 7 | Tax Report estructura ITBIS | `l10n_do.tax_report` presente |
| 8 | Estados financieros formato RD | `l10n_do_bs`, `l10n_do_pl` |
| 9 | RNC empresa | 133621282 |

### ¿Qué no cumple?

| # | Brecha | Evidencia Fase 5 |
|---|--------|------------------|
| 1 | Secuencias NCF operativas | `ncf_sequences_count: 0` |
| 2 | Tipos documento B01/B02/B03/B04 | Modelo `l10n_latam.document.type` ausente |
| 3 | Asignación NCF al publicar factura | No verificable — sin framework |
| 4 | Libros DGII 606/607/608 | XML IDs no existen en `l10n_do_reports` |
| 5 | PDF factura con NCF impreso | No probado — sin número NCF generado |

### ¿Qué requiere desarrollo?

| Ítem | Prioridad | Notas |
|------|-----------|-------|
| Framework tipos documento + secuencias NCF | P0 | Custom `hellenia_account` solo tras 4 comprobaciones |
| Libros fiscales 606/607/608 | P0 | Complementar o extender `l10n_do_reports` |
| Layout PDF fiscal DGII | P1 | Si estándar no cumple post-NCF |

### ¿Qué requiere futura implementación?

- `l10n_do_edi` + Infile (eNCF)
- Transmisión XML DGII
- Tipos E31–E34 electrónicos
- Migración Ley 32-23 e-CF

### ¿Qué no aplica?

- POS fiscal integrado (Fase futura, no instalado)
- eNCF en Etapa 1 NCF tradicional
- Catálogo / usuarios operativos

---

## Matriz fiscal (Bloque J parcial)

| Área | Estado | Notas |
|------|--------|-------|
| ITBIS y retenciones | PASS | Maestro completo |
| Posiciones fiscales | PASS | 11 configuradas |
| `l10n_do` / `l10n_do_reports` | PASS | Instalados y operativos |
| NCF / documentos fiscales | **FAIL** | Sin framework en 19.0 on-premise |
| Libros DGII 606/607/608 | **FAIL** | No disponibles |
| Tax Report ITBIS | PASS | Estructura presente |
| eNCF / Infile | NO APLICA | Etapa futura |

---

## Brechas confirmadas (referencia GAP)

| ID | Prioridad | Estado | Evidencia |
|----|-----------|--------|-----------|
| G-02 | **P0** | CONFIRMED | `l10n_latam.document.type` ausente |
| G-04 | **P0** | CONFIRMED | Reportes 606/607/608 ausentes |
| G-01 | **P1** | CONFIRMED | 0 secuencias NCF |
| G-05 | P1 | POR VALIDAR | PDF layout — requiere prueba con NCF |
| G-07 | P1 | POR VALIDAR | Identificación LATAM partners |

---

**Contabilidad operativa:** [DOMINICAN_ACCOUNTING_CERTIFICATION.md](DOMINICAN_ACCOUNTING_CERTIFICATION.md)  
**Resumen ejecutivo y veredicto:** [PHASE5_EXECUTIVE_SUMMARY.md](PHASE5_EXECUTIVE_SUMMARY.md)

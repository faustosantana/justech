# Análisis y mapeo de formatos DGII — Fase 17.5

**Proyecto:** Justech Localization RD / Hellenia  
**Fecha análisis:** 2026-06-30  
**Alcance:** Solo repositorio — sin cambios en DEV, TEST, PROD ni módulos Odoo

---

## Objetivo

Analizar las 33 plantillas oficiales DGII en `data/localizations/do/templates/` y producir mapeos técnicos JSON en `data/localizations/do/mappings/` para que futuros exportadores Justech generen archivos conformes sin usar las macros Excel oficiales.

---

## Metodología

1. **Descompresión** de los 33 ZIP en entorno de análisis (`/tmp/dgii-analysis/`).
2. **Lectura estructural** con `xlrd` (`.xls`) y `openpyxl` (`.xlsx`/`.xlsm`).
3. **Detección automática** de fila de encabezado, columnas, hojas y presencia de macros — script `scripts/analyze_dgii_templates.py`.
4. **Validación manual** de formatos prioritarios 606, 607, 608, 609, 623, ITBIS y Norma 2-05 (catálogos, columnas reservadas, totales).
5. **Generación de mapeos** — script `scripts/generate_dgii_mappings.py`.
6. **Mapeo Odoo:** solo campos estándar verificables (`account.move`, `res.partner`) y referencias documentadas de Hellenia Fase 18 (`hellenia.withholding.catalog`). **No se inventaron campos**; los no disponibles se documentan como faltantes.

---

## Formatos analizados (33 ZIP)

| # | Código | Archivo ZIP | Hoja principal | Col. datos | Macros |
|---|--------|-------------|----------------|------------|--------|
| 1 | 606 (pre-2018) | `Formato606.zip` | Herramienta Formato 606 | 16 | No |
| 2 | 606-GOB | `Formato606Gubernamental.zip` | Herramienta Formato 606 | 16 | No |
| 3 | 607 (pre-2018) | `Formato607.zip` | Herramienta Formato 607 | 9 | No |
| 4 | 608 (pre-2018) | `Formato608.zip` | Formato 608 | 5 | No |
| 5 | 609 NG | `Formato609-NG-7-18.zip` | Formato 609 | 15 | **Sí** |
| 6 | 609 (pre-2018) | `PagosalExterior609.zip` | Herramienta envio Formato 609 | — | No |
| 7 | 612 | `ComprasDivisas(Formato612).zip` | Formato 612 | 10 | No |
| 8 | 613 | `VentasDivisas613.zip` | Formato 613 | 10 | No |
| 9 | 615 | `ReembolsosPagosReclamaciones615.zip` | Formato 615 | 11 | No |
| 10 | 616 | `Formato616.zip` | Formato 616 | 11 | No |
| 11 | 623 | `FormatoenvioRetencionesEstado623.zip` | Formato 623 | 9 | No |
| 12 | 629 | `EnvioReporteSiniestrosVehiculos(629).zip` | Formato 629 | 5 | No |
| 13 | 629 instructivo | `InstructivoEnvioSiniestrosVehiculos(629).zip` | — | PDF/DOC | — |
| 14 | 632 DIOR | `DIOR_Instalacion.zip` | Operaciones | 41 | **Sí** (.xlsm) |
| 15 | 641 | `Formato641.zip` | Herramienta Formato 641 | 7 | No |
| 16 | 642 | `Formato642.zip` | Herramienta Formato 642 | 10 | No |
| 17 | 643 | `HerramientaDeEnvioFormato643.zip` | Herramienta Formato 643 | 13 | **Sí** |
| 18 | 644 | `Formato-De-Compra-De-Combustible-644.zip` | Herramienta Formato 644 | 15 | No |
| 19 | 645 | `Formato-De-Venta-De-Combustible-645.zip` | Herramienta Formato 645 | 15 | No |
| 20 | 647 | `Formato-De-Envio-647.zip` | Herramienta Formato | 26 | No |
| 21 | 648 | `Herramienta-Envio-Formato-648.zip` | REPORTE DE VENTAS CIGARRILLOS | 3 | No |
| 22 | 649 | `Herramienta-Envio-Formato-649.zip` | Herramienta Formato 649 | 21 | No |
| 23 | 650 | `Formato-650.zip` | Formato de Envío FALCONDO | 13 | No |
| 24 | 651 | `Formato-651.zip` | Formato de Envío FALCONDO | 16 | No |
| 25 | **606 NG** | `Formato-de-Envio-606-(NG-07-2018-y-05-2019).zip` | Herramienta Formato 606 | **25** | No |
| 26 | **607 NG** | `Formato-de-Envio-607-(NG-07-2018-y-05-2019).zip` | Herramienta Formato 607 | **25** | No |
| 27 | **608 NG** | `Formato-de-Envio-608-(NG-07-2018-y-05-2019).zip` | Formato 608 | **5** | No |
| 28 | IC1 | `Formato-IC1.zip` | Formato de Envío FALCONDO | 13–16 | No |
| 29 | **ITBIS** | `FormatoExcelEnvioDatosITBIS.zip` | LOCAL + IMPORTACION | 7 + 8 | No |
| 30 | ITBIS instructivo | `InstructivoFormatoExcelEnvioDatosITBIS.zip` | — | — | — |
| 31 | ITBIS manual | `ManualenviodatosITBIS.zip` | — | — | — |
| 32 | **Norma 2-05** | `FormatoExcelNORMA2-05RetencionesTerceros.zip` | Norma 2-05 | 8 | No |
| 33 | Validador N13 | `Instalacion_ValidadorEntidadadFinanciera.zip` | Instalador Windows | — | — |

**Versión vigente para exportadores:** archivos marcados **NG** (períodos desde mayo 2018).

Resumen machine-readable: `/tmp/dgii-analysis/all_templates_summary.json` (regenerable con `analyze_dgii_templates.py`).

---

## Mapeos JSON creados

| Archivo | Formato | Columnas mapeadas |
|---------|---------|-------------------|
| `data/localizations/do/mappings/dgii_606.json` | 606 Compras NG | 25 (A–AA) |
| `data/localizations/do/mappings/dgii_607.json` | 607 Ventas NG | 25 (A–Y) |
| `data/localizations/do/mappings/dgii_608.json` | 608 NCF anulados NG | 5 |
| `data/localizations/do/mappings/dgii_609.json` | 609 Pagos exterior NG | 15 |
| `data/localizations/do/mappings/dgii_623.json` | 623 Retenciones Estado | 8 |
| `data/localizations/do/mappings/dgii_itbis.json` | ITBIS adelantos | 7 LOCAL + 8 IMPORTACION |
| `data/localizations/do/mappings/dgii_norma_2_05.json` | Norma 2-05 retenciones | 8 |

Cada JSON incluye: código, nombre oficial, archivo fuente, SHA256, hoja, columnas (tipo, longitud, obligatorio, formato), catálogos, validaciones, campos Odoo sugeridos, campos faltantes, reglas de negocio y notas DGII.

---

## Hallazgos técnicos por formato prioritario

### 606 — Compras

- **Encabezado:** RNC declarante (A4), Período YYYYMM (A5), Cantidad Registros (C6).
- **Columna H:** reservada/vacía; numeración salta de G (6) a I (7).
- **Catálogos embebidos** en columnas auxiliares AD–AF (no exportar): tipos bienes/servicios, retención ISR, forma de pago.
- **Hoja auxiliar:** `UtilitarioP` (lista de períodos).
- **Versión plantilla:** 2025.
- **Sin macros** en `.xls`; validación interna DGII vía contadores (Lineas de Error K6).

### 607 — Ventas

- **25 columnas** incluyendo desglose de formas de venta (R–X).
- **Tipo de ingreso** (F): catálogo 01–06 en columna auxiliar.
- **Versión plantilla:** 2023.1.1.
- La suma de formas de pago debe cuadrar con monto facturado + ITBIS según normativa.

### 608 — NCF anulados

- Solo 5 columnas de datos; **columna C reservada**.
- **Tipo de anulación:** códigos 01–10 documentados en catálogo.
- Independiente del 607.

### 609 — Pagos al exterior

- Archivo **`.xlsm` con macros VBA**.
- Hoja **`Listas`:** países (códigos numéricos DGII) y tipos de servicio.
- Columna C reservada en numeración.

### 623 — Retenciones del Estado

- Fila encabezado en **12** (no 11).
- Totales: Monto Total en Retenciones, Total Errores.
- Distinto de Norma 2-05.

### ITBIS — Adelantos

- Dos hojas: **LOCAL** (compras) e **IMPORTACION** (aduanas/DGA).
- Fechas en formato `aaaammdd`.
- IMPORTACION requiere datos aduaneros no presentes en Odoo estándar.

### Norma 2-05 — Retenciones a terceros

- Reporta ITBIS retenido a proveedores.
- Campo **Identificacion Retención** debe mapearse al catálogo `hellenia.withholding.catalog` (Fase 18 TEST).

---

## Convenciones de formato DGII

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Fecha | `YYYYMMDD` | `20250615` |
| Período | `YYYYMM` | `202506` |
| RNC | 9 dígitos | `131793916` |
| Cédula | 11 dígitos | `00112345678` |
| NCF | Alfanumérico 11–13 | `B0100000001` |
| Montos | Decimal 2 decimales, sin separadores de miles | `15000.00` |
| Códigos catálogo | Numéricos con zero-padding | `01`, `02` |

---

## Limitaciones del análisis

- Validaciones condicionales Excel (Data Validation) en `.xlsm` no se extrajeron completamente (`openpyxl` las omite).
- Catálogos de 609 (países/servicios) y 623 (tipo referencia) requieren extracción completa de hoja `Listas`/instructivo en fase posterior.
- Los módulos `justech_l10n_do_*` **no están en este repositorio**; campos fiscales se documentan como faltantes.
- Libro de Ventas **987** no disponible en la página DGII al momento de la descarga.

---

## Scripts de reproducción

```bash
pip install openpyxl xlrd
python3 scripts/analyze_dgii_templates.py   # → /tmp/dgii-analysis/all_templates_summary.json
python3 scripts/generate_dgii_mappings.py   # → data/localizations/do/mappings/dgii_*.json
```

---

## Referencias

- Plantillas: `data/localizations/do/templates/`
- Inventario: `data/localizations/do/templates/templates.json`
- Guía plantillas: `docs/DGII_TEMPLATES.md`
- Matriz de soporte: `docs/DGII_SUPPORTED_FORMATS_MATRIX.md`
- Backlog campos: `docs/DGII_MISSING_FIELDS_BACKLOG.md`

# Fase 23.3I — Rediseño visual premium cotización

**Fecha:** 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_reports` 19.0.1.4.4

## Objetivo

Mantener la distribución exacta del wireframe (header, banda, fechas, bloques cliente/vendedor, tabla, totales, condiciones, firmas, footer) pero cambiar el lenguaje visual a un documento corporativo premium (SAP / Oracle NetSuite / Dynamics / Odoo Enterprise).

## Cambios visuales (solo CSS/QWeb cotización)

| Antes (Excel-like) | Después (premium) |
|--------------------|-------------------|
| Cajas con borde en cliente/vendedor | Bloques abiertos, títulos con subrayado verde |
| Borde vertical logo/empresa | Separador hairline sutil |
| Caja blanca en número de cotización | Texto blanco directo en banda |
| Bordes en cada celda de totales | Solo línea superior en total |
| Marco en condiciones | Tipografía + línea sutil |
| Footer con borde verde grueso | Hairline gris claro |
| Filas tabla con rejilla | Solo líneas horizontales + zebra sutil |

## Sin cambios

- Estructura HTML y orden de secciones
- Paperformat cotización (23.3H)
- Logo, spacers, paginación
- Facturas, pedidos confirmados, contabilidad, DGII

## Evidencia

`evidence/phase23-3i-premium-quote-visual/`

**No promovido a PROD.**

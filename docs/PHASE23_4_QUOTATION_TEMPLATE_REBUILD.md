# Fase 23.4 — Reconstrucción template cotización premium

**Fecha:** 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_reports` 19.0.1.5.0

## Objetivo

Reconstrucción completa del QWeb de cotización siguiendo la imagen de referencia: documento corporativo premium, sin apariencia Excel.

## Cambios (solo template cotización)

- Header limpio: logo grande izquierda, empresa derecha, sin cajas ni líneas verticales
- Banda verde `#3E4827` con número en caja oscura
- Cliente: solo Cliente, RNC, Teléfono, Correo
- Vendedor: solo Vendedor + Términos de pago (sin email/tel interno)
- Tabla SAP-style: encabezado verde, filas con aire, líneas suaves
- Totales premium alineados derecha, TOTAL destacado en verde
- Condiciones ancladas al fondo vía espaciador dinámico (lógica existente)
- Firmas con iconos SVG inline
- Footer minimalista + paginación

## Sin cambios

- Modelos, paperformat, DGII, contabilidad, otros reportes

## Evidencia

`evidence/phase23-4-quote-template-rebuild/`

**No promovido a PROD.**

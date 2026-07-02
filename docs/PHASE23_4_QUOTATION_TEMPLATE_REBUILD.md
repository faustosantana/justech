# Fase 23.4 — Reconstrucción template cotización premium

**Fecha:** 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_reports` 19.0.1.5.1

## Objetivo

Reconstrucción completa del QWeb de cotización siguiendo la imagen de referencia: documento corporativo premium, sin apariencia Excel.

## Cambios (solo template cotización)

- Header limpio: logo grande izquierda, empresa derecha, sin cajas ni líneas verticales
- Banda verde `#3E4827` con separador vertical blanco y número a la derecha
- Campos cliente/vendedor en filas label | valor (sin cajas grises)
- Términos de pago: "Contado" o "Crédito a XX días"
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

| Archivo | Descripción |
|---------|-------------|
| `screenshot_before_rebuild.png` | Antes (23.3I) |
| `screenshot_after_rebuild.png` | Después (23.4) |
| PDFs 1/5/25 productos | `hellenia_test` |
| `validation.json` | PASS |

## Resultado TEST (PASS)

| Caso | Páginas |
|------|---------|
| 1 producto (S00134) | 1 |
| 5 productos (S00135) | 1 |
| 25 productos (S00138) | 2 |

**No promovido a PROD.**

# Hellenia — Validación Visual Cotización Premium

**Última actualización:** Fase 23.3F — 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_reports` **19.0.1.4.2**  
**Resultado:** **TEST PASS**

---

## Resumen ejecutivo

| Criterio | Estado |
|----------|--------|
| Encabezado al inicio del área imprimible (sin layout Odoo duplicado) | PASS |
| Sin estilo Excel — bloques corporativos sin cajas | PASS |
| Tabla productos elegante (#3E4827, líneas finas) | PASS |
| Totales refinados, total destacado #3E4827 | PASS |
| Espaciador dinámico (min-height solo ≤8 productos) | PASS |
| Condiciones / firmas / footer anclados abajo (pocos ítems) | PASS |
| 1 producto = **1 sola página** | PASS |
| 5 / 15 / 25 productos sin romper diseño | PASS |
| Sin mojibake / sin inglés | PASS |
| Portal PDF HTTP 200 | PASS |
| Backend PDF OK | PASS |
| Listo para PROD | **No** — pendiente aprobación explícita |

---

## Fases

| Fase | Resultado |
|------|-----------|
| 23.3C | PASS — UTF-8 + layout tablas |
| 23.3D | PASS — compactación + firmas iniciales |
| 23.3E | PASS — ajustes finos visuales |
| **23.3F** | **PASS** — pulido premium corporativo (solo QWeb/CSS) |

---

## Cambios Fase 23.3F

1. **Ocultar header/footer Odoo duplicados** — CSS en plantilla cotización
2. **Encabezado ~15 mm más arriba** — `margin-top: -15mm` en shell A4
3. **Bloques cliente/vendedor** — títulos grises, valores negros, sin bordes
4. **Tabla productos** — cabecera Hellenia, filas con línea inferior `#ededed`
5. **Totales** — menos líneas, total con borde superior `#3E4827` y fondo `#f4f6f1`
6. **Shell A4 condicional** — `min-height: 210mm` solo si ≤8 productos; evita media página vacía con 15+
7. **Firmas corporativas** — ENTREGADO POR / RECIBIDO POR / FECHA con líneas alineadas
8. **Footer minimal** — Tel \| Correo \| Web, gris, pegado al borde inferior

**Restricción respetada:** sin cambios en Python, modelos, lógica, pagos ni retenciones.

---

## PDFs generados

| Archivo | Productos | Páginas | Tamaño |
|---------|-----------|---------|--------|
| `quotation_1_product.pdf` | 1 | 1 | ~69 KB |
| `quotation_5_products.pdf` | 5 | 1 | ~72 KB |
| `quotation_15_products.pdf` | 15 | 2 | ~80 KB |
| `quotation_25_products.pdf` | 25 | 2 | ~89 KB |
| `portal_order_135.pdf` | 1 | 1 | ~69 KB |

Evidencia: `evidence/phase23-3f-quotation-premium-polish/`

---

## Screenshots

- `screenshot_quote_1_page1.png`
- `screenshot_quote_5_page1.png`
- `screenshot_quote_15_page1.png` / `screenshot_quote_15_page2.png`
- `screenshot_quote_25_page1.png` / `screenshot_quote_25_page2.png`
- `screenshot_portal_page1.png`

---

## Diferencias visuales vs 23.3E

| Aspecto | 23.3E | 23.3F |
|---------|-------|-------|
| Header Odoo externo | Visible (doble encabezado) | Oculto — solo branding Hellenia |
| Margen superior | Franja blanca amplia | ~15 mm más arriba |
| Cajas cliente/vendedor | Algo de estructura tabular | Bloques abiertos, sin celdas |
| Espaciador inferior | Python + px fijos grandes | QWeb shell A4 condicional |
| 15 productos pág. 1 | Media página vacía bajo totales | Totales al pie de tabla, sin hueco |
| Footer | Línea verde gruesa | Separador fino gris, más discreto |

---

## Decisión

**TEST PASS** — Cotización con apariencia corporativa premium en TEST.  
Pendiente **aprobación visual humana** antes de PROD.

# Fase 25A — Revisión visual factura Justech

**Estado:** `PENDING_USER_VISUAL_APPROVAL`  
**Base de datos:** `hellenia_test` únicamente  
**Módulo:** `justech_report_design` v19.0.3.0.0  
**Reporte:** `Justech PDF — Factura` (paralelo, no oficial)

> Esta fase **no implementa correcciones**. Solo documenta hallazgos para tu revisión explícita.

---

## Artefactos generados

| Escenario | PDF | PNG pág. 1 |
|-----------|-----|------------|
| 1 línea | `01_invoice_1_line.pdf` | `01_invoice_1_line.png` |
| 5 líneas | `02_invoice_5_lines.pdf` | `02_invoice_5_lines.png` |
| 22 líneas (2 págs.) | `03_invoice_22_lines.pdf` | `03_invoice_22_lines.png` (+ `03_invoice_22_lines_p2.png`) |
| Con descuento | `04_invoice_with_discount.pdf` | `04_invoice_with_discount.png` |
| Sin descuento | `05_invoice_no_discount.pdf` | `05_invoice_no_discount.png` |
| Fiscal B01 | `06_invoice_fiscal_b01.pdf` | `06_invoice_fiscal_b01.png` |
| Consumo B02 | `07_invoice_consumo_b02.pdf` | `07_invoice_consumo_b02.png` |
| Gubernamental | `08_invoice_government.pdf` | `08_invoice_government.png` |
| Nota de crédito B04 | `09_credit_note_b04.pdf` | `09_credit_note_b04.png` |

**Referencia de comparación:** imagen aprobada Fase 25 (factura fiscal Hellenia con NCF B01000001234, retención ISR, observaciones a–f).

**Muestra principal para comparar:** `06_invoice_fiscal_b01.png`

---

## Matriz de revisión (vs. diseño aprobado)

Evaluación basada en inspección de PNG/PDF generados en TEST el 2026-07-02.  
No se asume PASS por defecto.

| # | Elemento | Resultado | Notas |
|---|----------|-----------|-------|
| 1 | Logo | **PASS** | Logo Hellenia grande a la izquierda, proporción correcta. |
| 2 | Header empresa | **PASS** | Datos empresa arriba derecha (nombre, dirección, RNC, tel, correo, web). Sin bloque duplicado de empresa debajo. |
| 3 | Banda verde | **PASS** | Barra `#3E4827` con texto blanco. |
| 4 | Texto «FACTURA» en banda | **FAIL** | wkhtmltopdf renderiza letras separadas («F A C T U R A») por `letter-spacing: 2.5px` en `.jt-hq-band-title`. |
| 5 | No. factura en banda | **FAIL** | En borradores el número aparece vacío (`invoice_name: false`). En publicadas sí aparece (ej. INV/2026/00215). |
| 6 | NCF en banda | **PASS** | Visible en facturas publicadas con NCF asignado (ej. B0100020036). Vacío en borrador — esperado. |
| 7 | Tipo de comprobante | **PASS** | Muestra valor real del catálogo (`Factura de Crédito Fiscal`, `Factura de Consumo`, `Nota de Crédito`). Texto difiere del mockup de referencia («Factura con Valor Fiscal») pero es el dato fiscal real. |
| 8 | Información del cliente | **PASS** | Nombre, RNC, teléfono, correo en columna 1. |
| 9 | Condiciones de pago | **PASS** | «Crédito a 30 días» / «Contado» según término real. |
| 10 | Vendedor | **PASS** | `invoice_user_id` visible (OdooBot en TEST). |
| 11 | Fecha de emisión | **PASS** | Formato `dd/mm/yyyy`. |
| 12 | Fecha de vencimiento | **PASS** | Formato `dd/mm/yyyy`. |
| 13 | Iconos en columnas meta | **FAIL** | La imagen aprobada muestra iconos verdes en encabezados de columnas; el PDF no los incluye. |
| 14 | Fondo gris encabezados meta | **FAIL** | Referencia: bloques con fondo gris claro en títulos de columna; implementación actual solo texto sin fondo. |
| 15 | Tabla — encabezado verde | **PASS** | thead verde con texto blanco. |
| 16 | Tabla — columnas | **PASS** | #, Descripción, Cant., P. Unit., ITBIS, Subtotal (+ Descuento si aplica). |
| 17 | Tabla — zebra | **PASS** | Filas alternas gris claro (`#f8f9f6`) en PDF multi-línea. |
| 18 | Descuento columna | **PASS** | Visible en `04_invoice_with_discount` cuando `discount > 0`. |
| 19 | Descuento totales | **PASS** | Subtotal bruto, Descuento, Subtotal en bloque derecho. |
| 20 | ITBIS línea | **PASS** | Monto por línea coincide con cálculo Odoo. |
| 21 | ITBIS total | **PASS** | Coincide con totales Odoo (ej. RD$ 180.00 sobre RD$ 1,000.00). |
| 22 | Retenciones | **FAIL** | No aparecen en `08_invoice_government` pese a toggle gobierno; referencia muestra «RETENCIONES (ISR 1%)». |
| 23 | Observaciones / términos | **FAIL** | Bloque izquierdo ausente en muestras sin `narration` / términos empresa. Referencia siempre muestra texto a–f. |
| 24 | Totales — bloque derecho | **PASS** | Subtotal, ITBIS, TOTAL alineados a la derecha. |
| 25 | Totales — caja borde gris | **FAIL** | Referencia: recuadro gris alrededor de totales; implementación sin borde visible. |
| 26 | TOTAL tipografía | **PASS** | TOTAL grande en verde `#3E4827`. |
| 27 | Firmas | **PASS** | ENTREGADO POR / RECIBIDO POR + líneas + Fecha. |
| 28 | Footer verde | **PASS** | Barra verde con teléfono \| correo \| web \| página X de Y. |
| 29 | Paginación multi-página | **PASS** | `03_invoice_22_lines`: «Página 1 de 2» y «Página 2 de 2». |
| 30 | Márgenes | **PASS** | Carta, márgenes compactos coherentes con cotización. |
| 31 | Espaciado firmas pág. 2 | **FAIL** | En pág. 2 de 22 líneas, firmas quedan a media página con mucho espacio vacío superior. |
| 32 | Tipografía general | **PASS** | DejaVu Sans / sans-serif legible. |
| 33 | Colores marca | **PASS** | Verde `#3E4827` consistente con cotización. |
| 34 | Bordes tabla | **PASS** | Sin bordes gruesos no deseados (wkhtmltopdf). |
| 35 | Alineación numérica | **PASS** | Cant., P. Unit., ITBIS, Subtotal alineados a la derecha. |
| 36 | Nota de crédito — título banda | **FAIL** | `09_credit_note_b04` muestra «FACTURA» en banda; debería ser «NOTA DE CRÉDITO» según diseño fiscal. |
| 37 | Nota de crédito — datos | **PASS** | NCF B04, tipo «Nota de Crédito», totales correctos. |
| 38 | Consumo B02 | **PASS** | NCF B02, cliente sin RNC, tipo «Factura de Consumo». |
| 39 | Moneda DOP | **PASS** | Prefijo RD$ en todos los escenarios DOP. |
| 40 | Correo cliente sin etiqueta | **NO APLICA** | Email se muestra sin prefijo «Correo:» — aceptable si coincide con referencia. |

---

## Resumen

| Resultado | Cantidad |
|-----------|----------|
| PASS | 30 |
| FAIL | 9 |
| NO APLICA | 1 |

**Conclusión de esta fase:** el paquete está listo para tu revisión visual. **No se declara aprobación final** hasta tu confirmación explícita.

---

## Restricciones verificadas (sin cambios)

- PROD: no tocado
- Factura estándar Odoo: intacta
- DGII / contabilidad / cotización / compras / inventario: sin modificaciones

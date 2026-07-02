# Fase 25A — Auditoría visual (diferencias vs. imagen aprobada)

**Fecha:** 2026-07-02  
**Comparación:** PDFs generados en `hellenia_test` vs. imagen de referencia Fase 25  
**Acción:** solo documentación — **sin correcciones aplicadas**

---

## 1. Diferencia: espaciado de letras en «FACTURA»

| Campo | Detalle |
|-------|---------|
| **Observado** | En PDF, el texto de la banda se extrae como `F A C T U R A` (letras separadas). |
| **Referencia** | «FACTURA» continuo, sin espacios entre letras. |
| **Causa** | CSS `.jt-hq-band-title { letter-spacing: 2.5px; }` en `hellenia_quotation.scss`, heredado por la banda de factura. wkhtmltopdf amplifica el espaciado. |
| **Corrección propuesta** | En factura, usar clase `.jt-inv-band-title` con `letter-spacing: 0.5px` o `0`, o regla específica `.jt-inv-band .jt-hq-band-title { letter-spacing: 0; }`. |

---

## 2. Diferencia: número de factura vacío en borrador

| Campo | Detalle |
|-------|---------|
| **Observado** | `01_invoice_1_line.pdf`: banda muestra «No. FACTURA:» sin valor (`doc.name` es `false` en borrador). |
| **Referencia** | Siempre muestra número (ej. FAC-0000123 / INV/…). |
| **Causa** | Campo `account.move.name` no se asigna hasta publicar o confirmar secuencia. |
| **Corrección propuesta** | En QWeb, fallback: `doc.name or doc.id` con etiqueta «Borrador», o mostrar `doc.payment_reference` / secuencia provisional; definir regla de negocio con usuario. |

---

## 3. Diferencia: iconos en encabezados de columnas meta

| Campo | Detalle |
|-------|---------|
| **Observado** | Columnas cliente / pago / vendedor / fechas sin iconos. |
| **Referencia** | Iconos verdes pequeños sobre cada título de columna (persona, documento, calendario). |
| **Causa** | Template `justech_invoice_template.xml` no incluye elementos `<img>` o iconos SVG/font en `.jt-hq-card-title`. |
| **Corrección propuesta** | Añadir iconos inline (PNG/SVG embebidos en módulo) junto a cada título, con tamaño ~10px y color `#3E4827`. |

---

## 4. Diferencia: fondo gris en bloque de 5 columnas

| Campo | Detalle |
|-------|---------|
| **Observado** | Títulos de columna en texto verde sobre fondo blanco. |
| **Referencia** | Encabezados de columna con fondo gris claro continuo. |
| **Causa** | SCSS `.jt-inv-meta-cols` sin `background-color` en celdas de título. |
| **Corrección propuesta** | Añadir `background-color: #f5f5f5` en fila de títulos o padding con fondo en cada `.jt-inv-meta-col` para la fila de labels. |

---

## 5. Diferencia: bloque observaciones / términos ausente

| Campo | Detalle |
|-------|---------|
| **Observado** | En muestras sin `narration`, no aparece bloque «OBSERVACIONES / TÉRMINOS Y CONDICIONES». |
| **Referencia** | Texto largo (a)–(f) a la izquierda de totales. |
| **Causa** | `jt_show_invoice_observations()` retorna `False` si `narration` vacío y `hellenia_terms_conditions` vacío; bloque condicionado con `t-if`. |
| **Corrección propuesta** | Precargar términos empresa en facturas (similar a cotización `note`) o mostrar `hellenia_terms_conditions` por defecto; validar con negocio si debe ser siempre visible. |

---

## 6. Diferencia: recuadro de totales sin borde

| Campo | Detalle |
|-------|---------|
| **Observado** | Totales flotantes a la derecha sin marco visible. |
| **Referencia** | Caja compacta con borde gris claro alrededor de subtotal / ITBIS / total. |
| **Causa** | `.jt-hq-totals` tiene `border: none !important` heredado de cotización. |
| **Corrección propuesta** | Clase `.jt-inv-totals` con `border: 1px solid #e0e0e0` solo en factura, sin afectar cotización. |

---

## 7. Diferencia: retenciones no visibles en factura gubernamental

| Campo | Detalle |
|-------|---------|
| **Observado** | `08_invoice_government.pdf`: total RD$ 11,800 sin fila de retenciones; `retentions: []` en manifest. |
| **Referencia** | «RETENCIONES (ISR 1%): RD$ 35.00» u otra retención aplicada. |
| **Causa** | Toggle `hellenia_ret_isr_gov` en `create()` no dispara `_onchange` de impuestos; impuesto negativo no se aplica antes de `action_post()`. Helper `get_jt_invoice_retention_lines()` lee líneas de impuesto publicadas. |
| **Corrección propuesta** | En datos de prueba: llamar `inv._onchange_hellenia_ret_isr_gov()` o aplicar impuesto manualmente antes de publicar; en template verificar que fila retenciones se renderiza cuando `get_jt_invoice_show_retentions()` es True. |

---

## 8. Diferencia: nota de crédito muestra «FACTURA» en banda

| Campo | Detalle |
|-------|---------|
| **Observado** | `09_credit_note_b04.pdf`: banda izquierda dice «FACTURA». |
| **Referencia** | Título dinámico «NOTA DE CRÉDITO» para `out_refund`. |
| **Causa** | Template hardcodea `FACTURA` en `jt-inv-band-left`; no usa `move_type` ni helper fiscal. |
| **Corrección propuesta** | Sustituir texto por helper (ej. `get_jt_document_band_title()` → NOTA DE CRÉDITO / FACTURA / NOTA DE DÉBITO según `move_type` y `justech_do_document_type_id`). Reutilizar lógica de `hellenia_fiscal_document_title()` sin copiar DGII. |

---

## 9. Diferencia: texto tipo comprobante vs. mockup

| Campo | Detalle |
|-------|---------|
| **Observado** | «Factura de Crédito Fiscal» (catálogo B01). |
| **Referencia** | «Factura con Valor Fiscal» en imagen mockup. |
| **Causa** | Campo real `justech.do.fiscal.document.type.name` difiere del texto artístico del mockup. |
| **Corrección propuesta** | **No cambiar dato fiscal.** Si se desea texto comercial distinto, añadir campo de etiqueta PDF separado del nombre DGII — requiere decisión de negocio. Marcar como aceptable si prima exactitud fiscal. |

---

## 10. Diferencia: firmas en página 2 con espacio vacío excesivo

| Campo | Detalle |
|-------|---------|
| **Observado** | `03_invoice_22_lines_p2.png`: firmas a mitad de página, ~40% espacio blanco arriba. |
| **Referencia** | Firmas ancladas cerca del pie, encima del footer verde. |
| **Causa** | `.jt-hq-sig-grow { height: 320px; }` fijo empuja firmas; en multi-página el spacer se repite o no colapsa. |
| **Corrección propuesta** | Reducir `jt-hq-sig-grow` en factura, usar `min-height` condicional, o mover firmas solo a última página con CSS `page-break-inside: avoid` y spacer dinámico. |

---

## 11. Observación: PNG no generados en contenedor Odoo

| Campo | Detalle |
|-------|---------|
| **Observado** | `manifest.json` registra `"png": null` desde shell Odoo. |
| **Causa** | `pdftoppm` no disponible dentro del contenedor `hellenia-test-odoo-1`. |
| **Corrección propuesta** | Generar PNG en host VPS post-`docker cp` (como en `run-phase25a-visual-review.sh` actualizado) o instalar `poppler-utils` en imagen Odoo. |

---

## Archivos fuente revisados

| Archivo | Rol |
|---------|-----|
| `custom/justech_report_design/report/invoice/justech_invoice_template.xml` | Estructura QWeb |
| `custom/justech_report_design/static/src/scss/hellenia_invoice.scss` | Estilos factura |
| `custom/justech_report_design/static/src/scss/hellenia_quotation.scss` | Estilos compartidos banda/totales |
| `custom/justech_report_design/models/account_move.py` | Helpers ITBIS, retenciones, observaciones |

---

## Próximo paso (fuera de 25A)

Tras tu revisión visual y aprobación explícita, abrir **Fase 25B** para aplicar solo las correcciones que autorices — una por una, con nueva evidencia.

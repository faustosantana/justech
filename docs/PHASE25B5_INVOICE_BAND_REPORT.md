# Fase 25B.5 — Informe ajuste header fiscal

**Estado:** `PENDING_USER_VISUAL_APPROVAL`  
**Módulo:** `justech_report_design` v`19.0.3.6.0`  
**Entorno:** `hellenia_test` únicamente  
**Rama:** `cursor/phase25b5-invoice-band-dd85`

---

## Diferencias identificadas (25B.4 → referencia)

| Aspecto | Antes (25B.4) | Objetivo |
|---------|---------------|----------|
| Recuadro interno | Borde vertical entre columnas + borde izquierdo del bloque | Sin caja visible; texto integrado en banda |
| Distribución | 2 columnas con divs apilados | 2 columnas 3+3 con pares etiqueta/valor |
| Posición | Bloque centrado en mitad derecha | Bloque alineado al extremo derecho |
| Separación columnas | ~10–28 px | 36 px entre grupos |
| Etiquetas/valores | Inline sin columna fija | Tabla invisible: etiquetas 138px, valores alineados |
| NCF | Mismo peso que resto | Valor en negrita solo si NCF real existe |

---

## Archivos modificados (solo encabezado fiscal)

1. `custom/justech_report_design/report/invoice/justech_invoice_template.xml`  
   - Reestructuración del bloque fiscal en tablas sin borde (`jt-inv-band-meta-pairs`)  
   - Dos grupos 3+3 con espaciador central  
   - Clase condicional `jt-inv-ncf-strong` cuando `get_jt_ncf_display() != '—'`

2. `custom/justech_report_design/static/src/scss/hellenia_invoice.scss`  
   - Eliminación de bordes/outline/box-shadow en tablas internas de banda  
   - Alineación derecha del bloque (`align="right"`, `text-align: right`)  
   - Ancho fijo etiquetas, valores en negrita, etiquetas peso normal  
   - Separador único FACTURA|meta (igual cotización `jt-hq-band-num`)

3. `custom/justech_report_design/__manifest__.py` → v`19.0.3.6.0`

**No se modificó:** `account_move.py`, tabla, totales, footer, firmas, meta cliente, cotización.

---

## Confirmación sin regresiones

| Área | ¿Modificada? |
|------|----------------|
| Logo / header superior | No |
| Información empresa | No |
| Cliente / pago / vendedor | No |
| Tabla productos | No |
| Totales / descuentos / ITBIS / retenciones | No |
| Observaciones | No |
| Firmas / footer / paginación | No |
| Lógica fiscal / DGII / cálculos | No |

---

## Evidencia

```
evidence/phase25b5-invoice-band/
├── 01_invoice_1_line.pdf / .png
├── 02_invoice_5_lines.pdf / .png
├── 03_invoice_with_discount.pdf / .png
└── validation.json
```

ZIP: `packages/phase25b5-invoice-band/phase25b5-invoice-band.zip`

Regenerar: `bash scripts/run-phase25b5-invoice-band-test.sh`

---

## Auditoría visual (agente)

- Recuadro interno entre columnas: eliminado  
- Bloque desplazado a la derecha: sí (`align="right"`)  
- Columnas 3+3 balanceadas: sí  
- Etiquetas alineadas por ancho fijo: sí (138px)  
- Valores en columna común por grupo: sí  
- NCF borrador (`—`): sin resalte extra; publicada usará negrita en valor  

**Pendiente:** aprobación visual del usuario.

# FASE 24.1H — Diagnóstico flujo vertical CONDICIONES / FIRMAS

**Fecha:** 2026-07-02  
**Módulo:** `justech_report_design` v`19.0.1.1.5`  
**Entorno:** TEST (`hellenia_test`)  
**PROD:** no tocado

---

## Síntoma reportado

| Escenario | Comportamiento observado |
|-----------|-------------------------|
| Cotización **1 producto** | CONDICIONES casi desaparecen o quedan desplazadas |
| Cotización **5 productos** | CONDICIONES se ven correctamente |
| Expectativa | La posición de CONDICIONES **no debe depender** de la cantidad de líneas |

---

## Causa raíz (ANTES)

### 1. Contenedor acoplado `jt-hq-lower`

CONDICIONES y FIRMAS vivían dentro del **mismo wrapper**:

```xml
<div class="jt-hq-lower">
    <div class="jt-hq-cond-wrap">CONDICIONES</div>
    <div class="jt-hq-sig-push" style="height: {{ signature_push_px }}px;"/>
    <div class="jt-hq-sigs-wrap">FIRMAS</div>
</div>
```

Eso trataba condiciones y firmas como **un solo bloque inferior**, no como secciones independientes.

### 2. Spacer dinámico calculado por cantidad de líneas

En `models/sale_order.py`, `get_jt_quotation_signature_push_px()` calculaba la altura del spacer con fórmulas que dependían de `count` (líneas del detalle):

```python
content_above_lower = 412 + count * 34 + totals_h   # si count <= 22
max_push = page_usable - content_above_lower - cond_h - sig_h - footer_gap
cap = 340 if count <= 5 else 310
return max(64, min(int(max_push) + boost, cap))
```

| Líneas | `content_above_lower` aprox. | `signature_push_px` típico |
|--------|------------------------------|------------------------------|
| 1 | ~504 px | **340 px** (tope) |
| 5 | ~640 px | **~300 px** |
| 20 | ~1140 px | multipágina, push reducido |

Con **menos líneas**, el algoritmo insertaba **más espacio** entre CONDICIONES y FIRMAS porque intentaba empujar las firmas al pie de página **desde dentro del mismo contenedor** que las condiciones.

### 3. Flag `anchor_signatures` también dependía de líneas

`get_jt_quotation_anchor_signatures()` devolvía `True` cuando `count <= 22`, activando el spacer grande en cotizaciones cortas (1–5 productos) — precisamente donde el usuario veía el problema.

### 4. Efecto visual en PDF (wkhtmltopdf)

Flujo real **antes**:

```
TABLA PRODUCTOS
↓
TOTALES (float right)
↓
┌─ jt-hq-lower ─────────────────────┐
│ CONDICIONES                        │
│ [spacer 340px si 1 línea]          │  ← empuja todo el bloque inferior
│ FIRMAS                             │
└────────────────────────────────────┘
```

Con 1 producto, el spacer enorme **separaba** condiciones de firmas pero el bloque completo competía con el área flotada de totales y el espacio útil de página, haciendo que CONDICIONES parecieran desplazadas o “perdidas” respecto a la referencia de 5 productos.

**Conclusión:** no era un bug de CSS aislado; era un **error de arquitectura QWeb** — condiciones y firmas compartían contenedor y lógica de posicionamiento acoplada al número de líneas.

---

## Corrección estructural (DESPUÉS)

### Principio

Separar flujo en bloques **hermanos** en orden fijo de documento:

```
TABLA PRODUCTOS
↓
TOTALES
↓
CLEARFIX
↓
CONDICIONES          ← flujo estático, siempre aquí
↓
ZONA FIRMAS          ← solo aquí el espacio flexible
  ├─ fila grow (altura 100%)
  └─ firmas (valign bottom)
↓
FOOTER
```

### Template (v19.0.1.1.5)

```xml
<div class="jt-hq-totals-wrap">...</div>
<div class="jt-hq-clear"/>

<div class="jt-hq-cond">
    <div class="jt-hq-cond-title">CONDICIONES</div>
    <div class="jt-hq-cond-body" t-out="terms_text"/>
</div>

<table class="jt-hq-sigs-zone" frame="void" rules="none">
    <tr class="jt-hq-sig-grow"><td>&#160;</td></tr>
    <tr><td class="jt-hq-sigs-cell">...firmas...</td></tr>
</table>
```

### Cambios clave

| Elemento | Antes | Después |
|----------|-------|---------|
| Wrapper `jt-hq-lower` | Agrupa cond + sigs | **Eliminado** |
| `signature_push_px` en QWeb | Inline style por líneas | **Eliminado** |
| Helpers Python de push/anchor | 5 métodos con `count * 34` | **Eliminados** |
| Posición CONDICIONES | Después de totales pero dentro de lower + spacer | **Hermana directa** después de totales + clearfix |
| Posición FIRMAS | Mismo contenedor que condiciones | **Zona independiente** `jt-hq-sigs-zone` |
| Espacio flexible | Entre cond y sigs, calculado por líneas | **Solo en fila grow** de sigs-zone; altura fija CSS (380px), **sin depender de líneas** |

### SCSS

- `.jt-hq-sigs-zone { height: 380px; }` — constante de zona de anclaje de firmas
- `.jt-hq-sig-grow td { height: 100%; }` — absorbe espacio flexible **solo** para firmas
- `.jt-hq-sigs-cell { vertical-align: bottom; }` — firmas al fondo de la zona
- `.jt-hq-cond { clear: both; }` + `.jt-hq-clear` tras totales — evita interferencia del float de totales

---

## Validación esperada

| Check | 1 producto | 5 productos | 25 productos |
|-------|------------|-------------|--------------|
| CONDICIONES tras TOTALES | ✅ mismo orden HTML | ✅ | ✅ |
| Sin `jt-hq-lower` | ✅ | ✅ | ✅ |
| Sin `signature_push_px` | ✅ | ✅ | ✅ |
| FIRMAS en zona propia | ✅ | ✅ | ✅ |
| Descuentos / note / footer | sin cambio | sin cambio | sin cambio |

---

## Archivos modificados

- `report/quotation/hellenia_quotation_template.xml`
- `static/src/scss/hellenia_quotation.scss`
- `models/sale_order.py` (eliminados helpers de push/anchor)
- `scripts/phase24-1-report-design-test.py` (checks de flujo vertical)
- `scripts/phase24-1g-quotation-audit.py` (checks vis/flow)

---

## Rollback

```bash
git checkout cursor/phase24-1g-vis001-fix-dd85 -- custom/justech_report_design/
# En TEST:
docker compose ... run odoo -d hellenia_test -u justech_report_design --stop-after-init
```

---

*Diagnóstico generado tras corrección estructural 24.1H — sin promoción PROD.*

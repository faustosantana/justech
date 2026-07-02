# Fase 23.3B — Fix error 500 impresión cotización (TEST)

**Fecha:** 2026-07-01  
**Entorno:** `hellenia_test` — `test.hellenia.cloud`  
**Módulo:** `hellenia_reports` **19.0.1.2.1**  
**Resultado:** **TEST PASS**

---

## Síntoma reportado

Al imprimir cotización desde portal:

```
GET /es/my/orders/135?access_token=...&report_type=pdf
→ 500 Internal Server Error
```

Cotizaciones afectadas: S00134 (id 135), S00135, S00136.

---

## Causa exacta

**`AttributeError: 'res.company' object has no attribute 'get_hellenia_quotation_terms_display'`**

| Aspecto | Detalle |
|---------|---------|
| Archivo | `custom/hellenia_reports/report/report_sale_quotation.xml` |
| Línea | ~219 (bloque CONDICIONES) |
| Elemento | `<div t-out="company.get_hellenia_quotation_terms_display()"/>` |

El template QWeb invocaba un método Python en `res.company`. Ese método existía en disco pero:

1. El worker HTTP del contenedor `hellenia-test-odoo-1` no había recargado el registry tras el upgrade (solo se ejecutó en contenedor one-off).
2. Las llamadas a métodos personalizados desde QWeb son frágiles en contexto portal/PDF.

El script de Fase 23.3 pasaba porque `odoo shell` carga el módulo en su propio proceso; la UI real usa el worker persistente.

---

## Corrección aplicada

### 1. Template QWeb (fix principal)

Reemplazar llamada Python por acceso directo al campo + default inline:

```xml
<t t-set="hellenia_default_quotation_terms">(a) Las piezas ofrecidas...</t>
...
<div t-out="company.hellenia_quotation_terms or hellenia_default_quotation_terms"/>
```

### 2. Numeración de líneas

Reemplazar `product_lines.index(line)` por contador `product_line_num` en el loop QWeb.

### 3. Despliegue TEST

- Upgrade `hellenia_reports` + **`docker compose up -d --force-recreate odoo`** para recargar Python en worker HTTP.

---

## Validación UI real

| Prueba | Resultado |
|--------|-----------|
| Portal PDF orden 135 + access_token | **HTTP 200** — PDF válido (`%PDF`) |
| Backend `_render_qweb_pdf` orden 135 | **PASS** — 69 800 bytes |
| PDF 1 producto (S00134) | **PASS** |
| PDF 5 productos (S00135) | **PASS** |
| PDF 15 productos (S00136) | **PASS** |

Script: `./scripts/run-phase23-3b-test.sh`

---

## Evidencia

`evidence/phase23-3b-quotation-500-fix/`

| Archivo | Contenido |
|---------|-----------|
| `traceback_before_fix.log` | Stack trace del 500 original |
| `validation.json` | Resultados HTTP + PDFs |
| `quotation_1_product.pdf` | Post-fix |
| `quotation_5_products.pdf` | Post-fix |
| `quotation_15_products.pdf` | Post-fix |

---

## Archivos modificados

- `custom/hellenia_reports/report/report_sale_quotation.xml`
- `custom/hellenia_reports/__manifest__.py` → `19.0.1.2.1`
- `scripts/run-phase23-3-test.sh` — force-recreate odoo
- `scripts/phase23-3b-quotation-500-fix-test.py` — **nuevo**
- `scripts/run-phase23-3b-test.sh` — **nuevo**

---

## Promoción PROD

**No** — pendiente aprobación explícita.

Rama: `cursor/phase23-3b-quotation-500-fix-dd85`

# Hellenia — Template Oficial de Cotización (Fase 23.3)

**Módulo:** `hellenia_reports` **19.0.1.2.0**  
**Alcance:** Solo cotizaciones PDF (`sale.order` en estado `draft` / `sent`)  
**Color corporativo:** `#3E4827` (Pantone 5743 C)

---

## Objetivo

Reemplazar la presentación estándar de cotización por un documento corporativo premium, limpio y en español, sin afectar facturas, pagos, DGII ni otros reportes.

---

## Archivos modificados / creados

| Archivo | Acción |
|---------|--------|
| `custom/hellenia_reports/report/report_sale_quotation.xml` | **Nuevo** — template `hellenia_quotation_document` + herencia `sale.report_saleorder_raw` |
| `custom/hellenia_reports/report/report_sale_order.xml` | Eliminado bloque comercial duplicado (solo aplica a pedidos confirmados) |
| `custom/hellenia_reports/models/res_company.py` | Campo `hellenia_quotation_terms` + método `get_hellenia_quotation_terms_display()` |
| `custom/hellenia_reports/data/quotation_terms_default.xml` | **Nuevo** — valor por defecto en empresa principal |
| `custom/hellenia_reports/views/res_company_views.xml` | Campo editable en Ajustes → Empresa → Documentos Hellenia |
| `custom/hellenia_reports/static/src/scss/hellenia_reports.scss` | Clases `.hellenia-quote-*`, `.hellenia-card`, etc. |
| `custom/hellenia_reports/__manifest__.py` | Versión `19.0.1.2.0`, nuevos data/report |
| `scripts/phase23-3-quotation-template-test.py` | Validación automatizada TEST |
| `scripts/run-phase23-3-test.sh` | Despliegue + upgrade + validación TEST |

---

## Campo editable

**Modelo:** `res.company`  
**Campo:** `hellenia_quotation_terms` (`fields.Text`)

**Ubicación UI:** Configuración → Empresas → [Empresa] → pestaña **Documentos Hellenia** → Condiciones de cotización

**Lógica de renderizado:**

1. Si `sale.order.note` tiene contenido → mostrar `order.note`
2. Si no → `company.hellenia_quotation_terms`
3. Si está vacío → texto por defecto corporativo (6 puntos a–f)

---

## Estrategia QWeb

- **No se modifica core Odoo.**
- Se hereda `sale.report_saleorder_raw` y se enruta condicionalmente:
  - `draft` / `sent` → `hellenia_reports.hellenia_quotation_document`
  - `sale` / `done` → `sale.report_saleorder_document` (con herencia Hellenia existente)
- El template premium es autónomo (sin `web.external_layout`) para control total del diseño.

---

## Estructura visual

1. Encabezado — logo grande izquierda, datos empresa derecha  
2. Banda verde `#3E4827` — COTIZACIÓN + número en caja blanca  
3. Fechas — cotización y validez (`dd/mm/yyyy`)  
4. Tarjetas — cliente (izq) y vendedor + términos de pago (der)  
5. Tabla — #, DESCRIPCIÓN, CANTIDAD, PRECIO UNITARIO, SUBTOTAL  
6. Totales — Subtotal, ITBIS, Total (caja destacada)  
7. Condiciones — bloque redondeado editable  
8. Pie — línea verde + teléfono | web | correo | Santo Domingo, RD  

**Excluido:** QR, NCF, textos en inglés, azul/dorado fuera de marca.

---

## Validación TEST

```bash
./scripts/run-phase23-3-test.sh
```

Evidencia: `evidence/phase23-3-quotation-template/`

---

## Promoción PROD

**No promover sin aprobación explícita.**  
Cuando se apruebe: upgrade `hellenia_reports` en `hellenia_prod` siguiendo el procedimiento de Fase 23.2.

# Hellenia — Validación Visual Cotización Premium (Fase 23.3)

**Fecha:** 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_reports` **19.0.1.2.0**  
**Resultado:** **TEST PASS**

---

## Resumen ejecutivo

| Criterio | Estado |
|----------|--------|
| Template premium activo en cotizaciones | PASS |
| Campo `hellenia_quotation_terms` creado | Sí |
| Condiciones editables (nota / empresa) | PASS |
| PDF 1 producto | PASS |
| PDF 5 productos | PASS |
| PDF 15 productos (salto de página) | PASS |
| Español completo | PASS |
| Sin QR / NCF | PASS |
| Sin inglés prohibido | PASS |
| Color corporativo #3E4827 | PASS (banda título + SCSS) |
| Listo para PROD | **No** — pendiente aprobación explícita |

---

## PDFs generados

| Archivo | Líneas | Tamaño | Cotización |
|---------|--------|--------|------------|
| `quotation_1_product.pdf` | 1 | 69 800 bytes | S00134 |
| `quotation_5_products.pdf` | 5 | 72 620 bytes | S00135 |
| `quotation_15_products.pdf` | 15 | 79 453 bytes | S00136 |

Ruta evidencia: `evidence/phase23-3-quotation-template/`

---

## Checks automatizados

Script: `scripts/phase23-3-quotation-template-test.py`  
Resultado: `validation.json` — **0 checks fallidos**

### Contenido validado en HTML

- Textos: COTIZACIÓN, INFORMACIÓN DEL CLIENTE, INFORMACIÓN DEL VENDEDOR, TÉRMINOS DE PAGO, DESCRIPCIÓN, CANTIDAD, PRECIO UNITARIO, SUBTOTAL, ITBIS, CONDICIONES, Santo Domingo, República Dominicana  
- Clases CSS: `hellenia-quote-page`, `hellenia-quote-header`, `hellenia-quote-title-band`, `hellenia-card`, `hellenia-items-table`, `hellenia-totals`, `hellenia-conditions`, `hellenia-footer-contact`  
- Ausencia: Quotation, Customer, Salesperson, Payment Terms, Expiration, Untaxed Amount, QR, NCF  
- Ausencia colores legacy: `#1a365d`, `#c9a227`

### Condiciones editables

| Prueba | Resultado |
|--------|-----------|
| Prioridad `order.note` | PASS |
| Respaldo `company.hellenia_quotation_terms` | PASS |
| Edición desde empresa | PASS |

---

## Errores visuales encontrados

Ninguno bloqueante en TEST.

**Observación menor:** el nombre del término de pago puede mostrar el texto maestro de Odoo (ej. "Manual Payment") si no está traducido en datos — no es un defecto del template.

---

## Screenshots

Capturas generadas desde PDF en `evidence/phase23-3-quotation-template/screenshots/` (si disponibles en el entorno de ejecución).

---

## Decisión

**TEST PASS** — Template listo para revisión humana y aprobación de promoción a PROD.

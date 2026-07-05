# Fase 28B — Corrección UX Factura Cliente (TEST)

**Fecha:** 2026-07-03  
**Entorno:** `hellenia_test` / https://test.hellenia.cloud  
**Resultado:** **PASS**

## Problemas corregidos

| Problema Fase 28 | Corrección 28B |
|------------------|----------------|
| Pestaña activa = Información Fiscal | **Líneas de factura** vuelve a ser la primera pestaña |
| Retenciones / Gobierno 5% en header | Movidas a pestaña **Retenciones** |
| Espacio vacío en encabezado | SCSS más compacto |
| Orden de pestañas incorrecto | Fiscal y Retenciones al final del notebook |

## Orden de pestañas (factura cliente)

1. Líneas de factura (`invoice_tab`)
2. Otra información (`other_info`)
3. Información Fiscal (`hellenia_fiscal_info_tab`)
4. Retenciones (`hellenia_withholding_tab`)

> Apuntes contables (`aml_tab`) permanece en posición estándar Odoo cuando el usuario tiene permisos contables.

## Archivos modificados

- `custom/hellenia_ux/views/account_move_invoice_form_phase28_views.xml`
- `custom/hellenia_ux/views/account_move_withholding_views.xml` (desactiva vista legacy del header)
- `custom/hellenia_ux/static/src/scss/hellenia_ux.scss`
- `custom/hellenia_ux/__manifest__.py` → **19.0.1.2.0**
- `scripts/phase28b-invoice-form-ux-fix-validation.py` (nuevo)

## Validación TEST — PASS

- Pestaña por defecto = Líneas de factura ✓
- Retenciones fuera del header ✓
- Información Fiscal al final ✓
- Crear factura sin/con cliente ✓
- Agregar línea y confirmar ✓
- `justech_report_design` / NCF sin cambios ✓

## PROD

**No desplegado.** Esperando aprobación.

## Revisión visual

Abrir nueva factura cliente en TEST y confirmar que:
- La tabla de productos aparece de inmediato
- No hay bloque “Retenciones” arriba del notebook
- Pestaña activa = Líneas de factura

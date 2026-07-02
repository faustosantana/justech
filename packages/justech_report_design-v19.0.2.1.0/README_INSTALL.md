# Instalación — Justech Report Design v19.0.2.1.0

## Contenido del paquete

| Elemento | Descripción |
|----------|-------------|
| `justech_report_design/` | Módulo Odoo listo para copiar a `addons` |
| `design_reference/` | PDFs de referencia (Hellenia) |
| `MANIFEST.txt` | Checksum y lista de archivos |

## Requisitos

- Odoo 19 Community o Enterprise
- Módulo `sale` instalado
- wkhtmltopdf (reportes PDF estándar de Odoo)

## Instalación rápida

```bash
# 1. Copiar módulo
cp -r justech_report_design /ruta/a/odoo/addons/

# 2. Reiniciar Odoo y actualizar lista de apps
# 3. Instalar "Justech Report Design" desde Apps
```

O por línea de comandos:

```bash
odoo-bin -d MI_BASE -i justech_report_design --stop-after-init
```

## Post-instalación

1. **Ajustes → Empresas → [Tu empresa] → Términos y Condiciones (Cotización)**
   - Editar el texto que aparece al pie del PDF.

2. **Ventas → Configuración → Cotizaciones y pedidos**
   - Términos y condiciones por defecto en nuevas cotizaciones.

3. **Ventas → Cotización → Imprimir → Cotización / Pedido**
   - Debe usar el diseño Justech automáticamente.

## Compatibilidad Hellenia

Si ya existe `hellenia_reports` con campo `hellenia_quotation_terms`, el módulo lo reutiliza sin migración.

## Rollback

Desde **Ajustes → Técnico → Informes → Informes**
- Restaurar acción `sale.action_report_saleorder` → `sale.action_report_saleorder_backup`

## Soporte

Justech — https://www.justech.io

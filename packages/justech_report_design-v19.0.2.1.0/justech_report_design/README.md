# Justech Report Design — Cotización Hellenia

Módulo Odoo 19 con el diseño PDF de cotización aprobado (Fase 24.2B).

## Características

- Reporte principal: **Cotización en PDF** (`sale.action_report_saleorder`)
- Respaldo: **Cotización en PDF (Respaldo)** → reporte estándar Odoo
- Condiciones por empresa → precargadas en `sale.order.note`
- PDF imprime exactamente `doc.note` (editable por cotización)
- Estilos SCSS en `web.report_assets_common` (wkhtmltopdf)

## Requisitos

| Requisito | Versión |
|-----------|---------|
| Odoo | 19.0 |
| Módulo `sale` | instalado |
| wkhtmltopdf | en el contenedor/servidor Odoo |

Opcional: si también tienes `hellenia_reports`, se usan sus `hellenia_quotation_terms` en lugar de `jt_quotation_terms`.

## Instalación rápida

```bash
# 1. Copiar módulo al addons path
cp -r justech_report_design /ruta/addons/

# 2. Reiniciar Odoo y actualizar lista de apps

# 3. Instalar
odoo -d TU_BASE -i justech_report_design --stop-after-init
```

O desde la UI: **Aplicaciones** → actualizar lista → buscar **Justech Report Design** → Instalar.

## Configuración

1. **Ajustes → Empresas → [tu empresa] → Cotizaciones PDF**  
   Editar condiciones por defecto.

2. Al crear una cotización, el campo **Términos y Condiciones** se precarga automáticamente.

3. **Imprimir → Cotización en PDF** genera el diseño Justech.

## Desinstalación / rollback

```python
# Shell Odoo — volver al reporte estándar
action = env.ref('sale.action_report_saleorder')
action.write({
    'report_name': 'sale.report_saleorder',
    'report_file': 'sale.report_saleorder',
})
env.cr.commit()
```

Luego desinstalar el módulo desde Aplicaciones si se desea.

## Versión

Ver `__manifest__.py` — distribución **19.0.2.1.0** (portable).

## Licencia

LGPL-3.0

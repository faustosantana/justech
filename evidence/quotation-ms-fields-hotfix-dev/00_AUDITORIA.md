# Hotfix P0 — Quitar SA/Levantamiento del formulario de Cotizaciones

## Auditoría

| Ítem | Valor |
|---|---|
| Módulo | `justech_managed_services` |
| Archivo | `custom/justech_managed_services/views/sale_order_views.xml` |
| XML ID | `justech_managed_services.view_sale_order_form_justech_ms` |
| Vista heredada | `sale.view_order_form` |
| XPath responsable (eliminado) | `//field[@name='partner_id']` position=`after` |
| Campos insertados (ya no) | `justech_managed_service_id` (Servicio Administrado), `justech_assessment_id` (Levantamiento) |
| ¿Estándar Odoo? | No — herencia custom del módulo MS |

## Corrección

- Eliminada la inserción XML de ambos campos.
- Conservado el smart button «Servicio Adm.» (solo si hay vínculo).
- Modelo / columnas BD: sin cambios.
- Formularios de Levantamiento / Servicio Administrado: intactos (validado en DEV).

## Validación DEV

- `VISIBLE_FORM_FIELDS_REMOVED = True` (hermanos de `partner_id` ya no incluyen los 2 campos).
- Assessment form sigue con `managed_service_id`.
- Versión módulo: `19.0.2.1.3`

## Producción

No desplegado. Esperando aprobación.

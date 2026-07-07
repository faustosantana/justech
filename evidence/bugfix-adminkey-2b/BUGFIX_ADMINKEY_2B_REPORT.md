# BUGFIX-ADMINKEY-2B — OwlError `prompt_message` undefined

## Causa raíz exacta

La vista `justech_modules.view_justech_admin_key_wizard_form` referencia el campo `prompt_message`, pero en el despliegue de BUGFIX-ADMINKEY-2 la vista se cargó **antes** de que el registro del modelo quedara consistente en todos los workers (upgrade parcial / workers sin reiniciar). El cliente Owl recibía la vista con `<field name="prompt_message"/>` mientras el registro en memoria aún no exponía ese campo → **OwlError: field is undefined**.

**Nota de rutas:** el wizard **no** vive en `custom/justech_admin/wizards/` (esa ruta no existe). El modelo y la vista están en **`justech_modules`**:

| Componente | Ruta real |
|---|---|
| Modelo | `custom/justech_modules/models/justech_admin_key_wizard.py` |
| Vista | `custom/justech_modules/views/justech_admin_access_views.xml` |
| Import | `custom/justech_modules/models/__init__.py` (línea 17) |
| Manifest | `custom/justech_modules/__manifest__.py` |

## Archivos corregidos

1. `custom/justech_modules/models/justech_admin_key_wizard.py` — `prompt_message` definido como `fields.Text(readonly=True)`
2. `custom/justech_modules/__manifest__.py` — versión `19.0.1.8.7` (fuerza upgrade)

## Acciones en PROD

- `rsync` de `justech_modules`
- `-u justech_modules --stop-after-init`
- `docker compose restart odoo`
- Validación shell + healthcheck

## Validación PROD (`hellenia_prod`)

| Pregunta | Resultado |
|---|---|
| ¿Wizard abre sin OwlError? | **Sí** — `get_views` incluye `prompt_message` (tipo `text`, readonly) |
| ¿Seguridad Justech abre? | **Sí** — `justech.control.security` tras autenticación |
| ¿Auditoría Justech abre? | **Sí** — `justech.control.audit` tras autenticación |
| ¿Healthcheck PASS? | **Sí** — `RESULTADO: PASS` |

Checks: 14/14 PASS — ver `validation-prod.json`.

## Diagnóstico post-fix

- `justech_modules` versión: **19.0.1.8.7**
- `ir.model.fields` id **13642** — `prompt_message`, ttype **text**
- Vista id **1812** — arch contiene `prompt_message`

## No tocado

NCF, DGII, COA, contabilidad, licencias, lógica de auditoría/seguridad fuera del wizard.

## Sin commit / push / merge

Cambios locales + evidencia únicamente.

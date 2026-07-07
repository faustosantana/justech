# fix-admin-panel-functions — TEST

**Fecha:** 2026-07-07  
**Módulos:** justech_modules 19.0.1.8.1, justech_admin 19.0.2.12.0

## Resultado

| Check | Estado |
|-------|--------|
| Tests | **67/67 PASS** |
| Validación | **PASS** |
| Healthcheck | **PASS** |

## Cambio UX

- **Administrar** abre `justech.client.module.admin.panel` (panel comercial)
- Funciones con switches **ON/OFF** (`boolean_toggle`)
- **Guardar cambios** y acciones críticas piden Clave Administrativa Justech
- Flags comerciales en `justech.client.module.feature.flag` (control comercial, sin enforcement fiscal)
- Formulario técnico de línea redirigido vía `get_formview_action()`

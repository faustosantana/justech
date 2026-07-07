# BUGFIX-ADMINKEY-2 — Seguridad Justech no abre

## Causa raíz
Seguridad/Auditoría invocaban require_session() directamente, mostrando AccessError en inglés sin abrir el wizard de clave.

Además, la sesión `SCOPE_ADMIN` no se reutilizaba desde Configuración porque `action_open_control_security()` y `action_open_control_audit()` no usaban `open_protected()` como el Centro de Control.

## Archivo principal
`custom/justech_modules/models/justech_admin_access_service.py`

## Corrección
- Seguridad/Auditoría usan `open_protected(..., target_method=...)` → wizard en español.
- Mensaje de sesión expirada en español (`_session_reauth_message`).
- Wizard admite `target_method` para evitar ACL de server actions.
- Launchers `_launch_control_security` / `_launch_control_audit`.

## Validación
- TEST: **PASS**
- PROD: **PASS**
- Healthcheck PROD: **PASS**

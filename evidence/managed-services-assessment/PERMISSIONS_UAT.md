# PERMISOS UAT — Servicios Administrados

Usuarios DEV (solo `justech_dev`; password no se publica):

- `uat_ms_manager` → `group_ms_manager`
- `uat_ms_user` → `group_ms_user` (consultor de LEV-2026-0006)
- `uat_ms_bare` → solo `base.group_user`

| Capacidad | Manager | User | Bare |
|---|---|---|---|
| Menú Servicios Administrados | Sí | Sí | No (filtrado) |
| Leer modelo | Sí | Sí (reglas) | AccessError |
| Leer no asignado | Sí | AccessError | AccessError |
| Unlink completado | Sí | AccessError | AccessError |
| Reabrir / marcar revisado | Sí | No (groups en botón) | No |
| Generar PDF / oportunidad | Sí | Sí (asignado) | No |

**Confirmación:** no se modificaron grupos generales de Contabilidad/Ventas/CRM para resolver el ACL fiscal al abrir Contactos con usuario solo-MS.

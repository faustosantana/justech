# Security Contract — justech_managed_services

## Módulo

`justech_managed_services` v19.0.1.0.0

## Categoría de grupos

**Justech Servicios Administrados** (`module_category_justech_managed_services`)

## Grupos

| XML ID | Nombre | Hereda |
|--------|--------|--------|
| `group_ms_user` | Usuario de Servicios Administrados | `base.group_user` |
| `group_ms_manager` | Administrador de Servicios Administrados | `group_ms_user` |

Administrador incluye por defecto a `base.user_root` y `base.user_admin` (solo en instalación del módulo).

## ACL — `justech.managed.service.assessment`

| Grupo | R | W | C | U |
|-------|---|---|---|---|
| `group_ms_user` | ✓ | ✓ | ✓ | ✗ |
| `group_ms_manager` | ✓ | ✓ | ✓ | ✓ |

## Record rules

| XML ID | Grupo | Dominio |
|--------|-------|---------|
| `rule_ms_assessment_user` | `group_ms_user` | `consultant_id = user` OR `create_uid = user` |
| `rule_ms_assessment_manager` | `group_ms_manager` | `[(1,'=',1)]` |

## Restricciones Python

- `unlink()`: estados `done`, `reviewed`, `proposal_ready` bloqueados para usuarios sin `group_ms_manager`.
- `action_reopen_public()`: solo `group_ms_manager`.

## Superficie pública

- Rutas `auth="public"` con validación por `access_token`.
- Escritura vía `sudo()` limitada a métodos `public_save_partial` / `public_submit` tras validación de token, vencimiento y estado.
- No expone IDs internos en URL.

## Modelos extendidos (solo lectura de contadores)

- `res.partner` — compute `justech_ms_assessment_count` respeta ACL del modelo assessment.
- `crm.lead` — idem.

## Sin modificación de

- Grupos estándar de Odoo (excepto asignación explícita en instalación a admin/root del grupo manager).
- ACL / rules de otros módulos.
- Vistas core reemplazadas (solo xpath heredado).

## Rollback de permisos

Desinstalar el módulo elimina grupos, ACL y rules propias. Usuarios perderán acceso al menú *Servicios Administrados*.

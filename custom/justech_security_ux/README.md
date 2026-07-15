# Justech Security UX — Permisos Enterprise

Capa de experiencia para administrar usuarios **sin conocer `res.groups`**.

## Principios

1. `res.groups` es la única fuente de verdad.
2. No se crean ACL, Record Rules ni permisos paralelos.
3. La UI sincroniza roles y acciones hacia grupos existentes.
4. Los grupos técnicos viven en **Permisos Avanzados** (solo Administrador del Sistema).
5. Un usuario puede pertenecer a **varias áreas a la vez**; cada área es independiente.

## Uso

1. En el formulario de usuario → pestaña **Permisos Justech**.
2. Marcar una o más áreas (Comercial, Compras, Inventario, …).
3. En cada bloque: elegir Rol y permisos específicos.
4. Revisar el **Resumen general** al final.

## Documentación de auditoría

- `docs/GROUP_MATRIX.md`
- `docs/GROUP_IMPLICATIONS.md`
- `docs/ROLE_MAPPING.md`

## Rollback

Restaurar módulo desde backup DEV y/o dump PostgreSQL:

`/root/backups/justech_dev/p1-multiarea-*`

# PERMISSIONS-UX-1 — Antes / Después

## Antes

- Pestaña **Access Rights** con widget estándar `res_user_group_ids`.
- Privilegios Odoo listados sin categorías de negocio.
- Sin tooltips en español por permiso.
- **Justech Admin** y **Justech Platform** activables directamente desde la lista técnica de grupos.
- Sin indicador visual de permisos exclusivos Justech.

## Después

- Pestaña renombrada a **Centro de Permisos**.
- Widget estándar oculto para administradores (visible solo en modo técnico `group_no_one`).
- Permisos organizados:

| Categoría | Permisos |
|-----------|----------|
| FINANZAS | Contabilidad, Banco, Multimoneda |
| OPERACIONES | Compras, Inventario |
| CONSULTA | Tablero, Auditoría |
| ADMINISTRACIÓN DEL ERP | Hellenia Governance |
| USO INTERNO JUSTECH | Justech Admin, Justech Platform |

- Cada permiso normal incluye tooltip al pasar el cursor (icono ? nativo Odoo).
- Permisos internos con fondo diferenciado, badges **🔒 Exclusivo Justech** / **Solo soporte autorizado**.
- Activación interna → wizard de Clave Administrativa; sesión válida reutilizada; sesión expirada vuelve a pedir clave.
- Escritura directa de grupos internos bloqueada en `res.users.write()`.

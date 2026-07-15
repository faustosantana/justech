# Changelog — justech_security_ux

## [19.0.2.0.0] — 2026-07-14 — P1 UX Permisos Enterprise

### Added
- Navegación por responsabilidades (Comercial, Compras, Inventario, Finanzas, Contabilidad, Fiscal, e-CF, Garantías, RRHH, CRM, Administración Justech).
- Tarjetas de rol con capacidades por área.
- Acciones operativas en lenguaje de negocio + tooltips.
- Documentación de auditoría: `docs/GROUP_MATRIX.md`, `GROUP_IMPLICATIONS.md`, `ROLE_MAPPING.md`.

### Changed
- «Permisos Avanzados» (grupos técnicos Odoo) visible solo para Administrador del Sistema.
- UI principal renombrada a «Permisos Justech».

### Unchanged
- Sin ACL nuevas, sin Record Rules nuevas, sin grupos nuevos.
- Sin migración automática de usuarios.
- Producción no tocada.

## [19.0.1.0.0] — 2026-07-14 — RC-SECURITY-UX-V1

### Added
- Primera capa de permisos operativos sobre `res.groups`.

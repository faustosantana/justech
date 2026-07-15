# Changelog — justech_security_ux

## [19.0.3.0.0] — 2026-07-14 — RC Permisos Justech definitivos

### Changed
- Rediseño completo: una sola pestaña «Permisos Justech» por módulos (multiárea).
- Niveles estándar reales de Odoo (Ventas/Compras/Inventario/Contabilidad/…).
- Capacidades Justech solo si existe grupo o control real.
- Sync quirúrgico: modificar un módulo no hace wipe de otros `group_ids`.
- Resumen general efectivo + advertencias de implicaciones.
- «Permisos Avanzados» preservado con aviso técnico.

### Removed (solo UX)
- Radio de una sola «Área de responsabilidad».
- Roles/áreas artificiales que ocultaban módulos.

### Unchanged
- ACL / Record Rules / `res.groups` / `implied_ids`: 0 cambios estructurales.
- Sin segunda capa de seguridad.
- Sin dependencias hellenia_*.
- Producción no tocada.

## [19.0.2.1.0] — 2026-07-14 — P1 Multiárea (iteración previa)

### Changed
- Selección múltiple de áreas (reemplazada por diseño modular 19.0.3.0.0).

## [19.0.2.0.0] — 2026-07-14 — P1 UX Permisos Enterprise

### Added
- Primera UX enterprise por responsabilidades.

## [19.0.1.0.0] — 2026-07-14 — RC-SECURITY-UX-V1

### Added
- Primera capa de permisos operativos sobre `res.groups`.

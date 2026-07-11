# ARQUITECTURA v2 — Consola Enterprise Administración Justech

**Fecha:** 2026-07-11  
**Backup:** `/opt/odoo-dev/backups/jac-enterprise-pre-20260711_213310` (PREFLIGHT_PASS)  
**Base:** justech_dev · **Rama:** feature/fiscal-standard-consolidation

## Decisiones

1. **Evolucionar** `justech_admin_center` (no segunda app).
2. **Productos → submódulos** vía `justech.admin.product` + `product_id` en catálogo.
3. **Estado funcional por empresa** vía `justech.admin.module.company` (instalación técnica sigue siendo global).
4. **Reauth:** reutilizar `justech.admin.access.service` + `justech.admin.session` (scope `admin_center`); **además** verificar `JUSTECH_ADMIN_CENTER_PASSWORD_HASH` (PBKDF2) si está definido en el entorno. Nunca guardar plaintext ni commitear secretos.
5. **Motores fiscales por empresa:** campo `fiscal_engine` = `traditional_ncf` | `electronic` | `none` en la fila empresa×módulo fiscal.
6. **UI:** dashboard HTML + grid de productos (sin kanban horizontal); español; tokens `#1B3A5C` / `#0D9488`; dark mode scoped.
7. **Dependencia:** `justech_modules` (sesión/clave existente).

## Contratos de manifiesto

```python
"justech_admin_center": {
    "product_code": "fiscal",  # core|fiscal|finance|warranty|integrations|audit
    "functional_name": "...",
    "short_description": "...",
    "long_description": "...",  # qué es, procesos, criticidad, activar/desactivar
    "is_critical": True,
    "activation_scope": "company",  # company|global
    "fiscal_engine_capable": True,
    ...
}
```

## Flujo seguro

Usuario autorizado → wizard clave → sesión 15 min → operaciones con preview → auditoría (sin secretos).

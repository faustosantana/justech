# LICENSE-4 — Catálogo real de licencias Justech

**Fecha:** 2026-07-07  
**Entorno:** PROD (`hellenia_prod`)

## Cambio

- `get_license_wizard_catalog()` usa whitelist estricta `LICENSE_WIZARD_CUSTOMIZATION_CODES` + `REAL_JUSTECH_CUSTOMIZATIONS`
- Ya no consulta `is_justech_licensable` ni el catálogo comercial completo
- Wizard simplificado: lista con toggles, `product_name` auto-poblado
- Productos comerciales para `multicurrency_commercial` y `global_audit`

## Validación PROD

- Catálogo: 5 módulos (cliente)
- Healthcheck: PASS
- Sin módulos inventados

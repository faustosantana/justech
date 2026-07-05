# F31.1.1 — Recomendaciones (sin implementar)

## Bloqueadores para LICENSING ENGINE READY

| # | Issue | Acción | Sprint |
|---|-------|--------|--------|
| 1 | LIFE-01 | Revalidar `expires_at`/`state` en `is_active()` | F31.2 |
| 2 | CONC-01 | Verificar UNIQUE `license.company` en BD; corregir si ausente | F31.2 |
| 3 | SQL-01 | Migrar `_sql_constraints` → `models.Constraint` (Odoo 19) | F31.2 |
| 4 | PERF-01 | `ormcache` + invalidación | F31.2 |
| 5 | SEC-01 | Hash `license_key` | F31.2 |
| 6 | COMP-02 | Enforce `max_users` | F31.2 |

## Performance

- Target post-cache: `is_active()` < 100 µs p99
- Target post-cache: `get_feature()` < 50 µs p99
- Añadir índice compuesto `justech_license_company(company_id, license_id)`
- Considerar materialized view o cache Redis para SaaS (F36)

## Seguridad

- Ocultar `license_key` en vistas para `license_user`
- Auditar intentos fallidos de `validate_license`
- Rotación de claves + `justech.activation.key` integrado

## Concurrencia

- `SELECT FOR UPDATE` en `action_activate()` para activación concurrente
- Test de carga con 2 workers Odoo (futuro)

## Governance gate

**No iniciar `hellenia_governance` hasta F31.2 P1 completado y re-certificación ≥ 80.**

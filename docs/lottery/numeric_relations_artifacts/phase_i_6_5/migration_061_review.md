# Migración 061 — Revisión previa a aplicar en DEV

**Fecha:** 2026-07-24  
**Ambiente:** DEV únicamente (`jaios-lottery-pg-dev` / DB `jaios_lottery_dev` @ `127.0.0.1:5433`)  
**Producción:** NO tocada  

## Identificación

| Campo | Valor |
|-------|--------|
| Revision | `061_lottery_ia_control_center` |
| Revises | `060_lottery_ai_alerting_closeout` |
| Schema | `jaios` |

## Contenido (upgrade)

1. **CREATE TABLE** `lottery_prediction_motors` (+ índices + unique `(key, tenant_id)`)
2. **CREATE TABLE** `lottery_prediction_motor_runs` (+ FK CASCADE + índice)
3. **ADD COLUMN** (nullable, condicional si no existe) en `lottery_ai_prompt_versions`:
   - `display_name`, `change_reason`, `notes`
   - `analysis_steps`, `tool_bindings`, `motor_bindings`
   - `benchmark_summary`, `gates_snapshot`
   - `archived_at`, `parent_draft_of`

## Operaciones destructivas

**Ninguna** en `upgrade()`: no DROP TABLE, no DELETE, no TRUNCATE, no ALTER destructivo.

`downgrade()` sí elimina tablas/columnas — **no se ejecutará** en esta fase.

## Dependencias

`061` asume existencia de `lottery_ai_prompt_versions` creada por **059**.  
`060` es el `down_revision` inmediato.

## Estado DEV antes

| Ítem | Valor |
|------|--------|
| `alembic_version` registrado | `032_lottery_scheduler_operations` (desalineado) |
| Esquema lottery real | ~3.0 (columnas `country_code`, `sync_priority`, etc.) |
| Tablas AI Admin 059/060 | **ausentes** (salvo `lottery_ai_usage` ad-hoc) |
| Draws | 91927 (histórico intacto; solo lectura en app) |

## Plan de aplicación seguro

1. Backup `pg_dump -Fc` (hecho).
2. **Stamp** a `058_lottery_3_0_platform` (alineación con esquema lottery real; **no** correr 033→057).
3. `alembic upgrade 061_lottery_ia_control_center` → aplica **059 + 060 + 061** (cadena mínima requerida por 061).
4. Validar objetos creados.
5. Confirmar draws count invariante.
6. No aplicar en Producción.

## Idempotencia

- Alembic no re-aplica 061 si `alembic_version` = 061.
- ADD COLUMN en 061 ya es condicional (`if name not in cols`).
- CREATE TABLE no es IF NOT EXISTS — segunda aplicación vía alembic está bloqueada por version table.

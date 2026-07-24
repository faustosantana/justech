# LOCAL DEV BOOTSTRAP — NO COMMITTED

Documenta fills locales necesarios para arrancar el API Control Center sobre un árbol `backend/` incompleto respecto a `app.main`. **No forman parte del feature I-1…I-6 ni del PR.**

## Por qué existió

El working tree local no contenía todos los módulos que importa `app.main` (DGCP, M365, Hermes, commercial search, etc.). Para levantar `jaios-cc-dev-api` contra `jaios_lottery_dev` se rellenaron archivos desde imagen/contenedor existentes (**solo local**).

## Qué se excluye del PR

- `backend/app/api/v1/*` untracked ajenos a lottery (ai, hermes, whatsapp, …)
- `backend/app/core/permissions.py`, `module_access.py`, `api_errors.py`, …
- `backend/app/models/*` / `schemas/*` / `services/*` fills (DGCP, documents, commercial, …)
- `backend/app/services/credential_vault.py` (requerido por resolvers de integraciones al boot)
- Parches temporales en `deps.py` / `search.py` (**restaurados a HEAD** antes del cierre)

## Cómo reproducir DEV sin esos fills

1. Usar imagen backend completa alineada al commit de la rama, **o**
2. Montar el árbol completo de producción/staging compatible, **o**
3. Arrancar solo el entrypoint lottery con el mismo set de módulos que CI.

## Secretos

Este documento **no** contiene passwords, tokens ni connection strings. Credenciales de usuarios de prueba DEV viven solo en el entorno local y no se versionan.

## Dump de backup

`backups/jaios_lottery_dev_pre_061_*.dump` permanece **local** (gitignore). En el repo solo: `.sha256` + `pre_backup_meta.txt`.

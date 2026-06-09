# Database

Esquema PostgreSQL para JAIOS Fase 1.

## Estructura

- `init/` — Scripts ejecutados al primer arranque de PostgreSQL (Docker)
- `migrations/` — Migraciones Alembic (fuente de verdad para evolución del esquema)

## Esquema `jaios`

| Tabla | Propósito |
|-------|-----------|
| `tenants` | Empresas / organizaciones |
| `users` | Usuarios globales |
| `tenant_memberships` | Relación usuario ↔ tenant con rol |
| `api_keys` | Claves API por tenant |
| `refresh_tokens` | Tokens de refresco JWT |
| `llm_provider_configs` | Configuración LLM por tenant |
| `integration_connections` | Conexiones Odoo, n8n, DGCP |
| `audit_logs` | Auditoría transversal |

## Migraciones

```bash
# Desde el contenedor backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

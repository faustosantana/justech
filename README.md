# JAIOS — Justech AI Operating System

**JAIOS Intelligence Platform** — Core Platform entregado; Fase 3 activa (Odoo Intelligence Center).

Ver [`docs/roadmap.md`](docs/roadmap.md) para el roadmap oficial completo.

## Stack

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 15, React, TypeScript, Tailwind, Shadcn |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Alembic |
| Base de datos | PostgreSQL 16 |
| Vector DB | Qdrant |
| Automatización | n8n |
| IA | Hermes Local, DeepSeek Huawei, OpenAI, Claude |

## Estructura del repositorio

```
jaios/
├── frontend/       # Next.js 15 — UI shell y cliente API
├── backend/        # FastAPI — auth, multi-tenant, gateway, LLM router
├── agents/         # Framework de agentes IA (sin lógica de negocio)
├── integrations/   # Conectores: Odoo, n8n, DGCP
├── database/       # Esquema SQL, migraciones Alembic
├── docker/         # Configuraciones por servicio
└── docs/           # Arquitectura y guías
```

## Inicio rápido

```bash
cp .env.example .env
make build
make up
make migrate
make seed
```

**Credenciales demo:** `admin@justech.do` / `JaiosAdmin2026!` — tenant `justech`

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/docs |
| n8n | http://localhost:5678 |
| Qdrant | http://localhost:6333/dashboard |

## Componentes core

- **Autenticación** — JWT access + refresh tokens, RBAC por tenant
- **Multiempresa** — Aislamiento por `tenant_id` en todas las capas
- **API Gateway** — Nginx + middleware FastAPI (rate limit, tenant context)
- **LLM Router** — Enrutamiento unificado a 4 proveedores con fallback
- **Integraciones** — Stubs profesionales para Odoo, n8n y DGCP

## Roadmap (resumen)

| Fase | Módulo | Estado |
|------|--------|--------|
| 1 | Core Platform | Entregado |
| 2 | DGCP Intelligence Center | Entregado |
| 3 | Odoo Intelligence Center | Activo |
| 4 | Microsoft 365 Intelligence Center | Planificado |
| 5 | Tasks / Work Hub / Notificaciones | Planificado |
| 6+ | Search, Documents, Supplier/Price Intelligence | Futuro |
| 7 | Hermes Memory, Multi-Agent Operations | Futuro |

## Documentación

- [`docs/architecture.md`](docs/architecture.md) — Diseño y dependencias
- [`docs/roadmap.md`](docs/roadmap.md) — Roadmap oficial y reglas de fase

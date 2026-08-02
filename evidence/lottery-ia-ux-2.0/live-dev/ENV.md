# Lottery IA UX 2.0 — Live DEV environment

- Backend container: `jaios-workspace-dev-api` (image `jaios-app-backend:lottery-ai-openai-creds`)
- Backend URL: `http://127.0.0.1:8022/api/v1`
- Backend health: `GET /api/v1/health` → 200 `{"status":"ok","service":"jaios-api","version":"0.1.0"}`
- Frontend RC container: `jaios-lottery-web-rc` → `http://127.0.0.1:3001` (200; API proxy points to :8001 — not used for this validation)
- Frontend live UX (this branch): `http://127.0.0.1:3010` with `INTERNAL_API_URL=http://127.0.0.1:8022`
- Frontend proxy health: `GET http://127.0.0.1:3010/api/v1/health` → 200
- Postgres DEV: `jaios-lottery-pg-dev` `:5433`
- Chat session: `7f0c8cfc-2d16-4da8-9f40-b095a180776e` (UX20 live case)
- Frontend commit (pre-fix): `f9c83e9`

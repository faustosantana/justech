# Production Image Build — Lottery Official

## Goal

Bake Lottery into Docker images so production does **not** depend on `docker cp` / hot-patch.

## Backend bake method

Production layout does not rebuild the full Python dependency tree for every release overlay.
Official Lottery bake uses:

- Base image: `jaios-app-backend:pre-lottery-official-20260722` (snapshot of previous `latest`)
- Dockerfile: `backend/Dockerfile.lottery-official` (also on host `/opt/jaios-app/backend/Dockerfile.lottery-official`)
- Build context: `/opt/jaios-app/backend`

```bash
cd /opt/jaios-app
docker build \
  -f backend/Dockerfile.lottery-official \
  --build-arg BASE_IMAGE=jaios-app-backend:pre-lottery-official-20260722 \
  -t jaios-app-backend:lottery-official-20260722 \
  -t jaios-app-backend:latest \
  backend/
```

The Dockerfile COPY overlays lottery packages, wiring (`router`, `main`, `config`, permissions, assistant), and Alembic `050`–`056`, then runs an import sanity check.

## Frontend build

```bash
cd /opt/jaios-app
docker compose build frontend
docker tag jaios-app-frontend:latest jaios-app-frontend:lottery-official-20260722
```

Context: `./frontend` / `frontend/Dockerfile` target `production`.

## Evidence

- `/var/jaios/lottery-bake/20260722/logs/backend_build.log`
- `/var/jaios/lottery-bake/20260722/logs/frontend_build.log`
- `/var/jaios/lottery-bake/20260722/build/Dockerfile.lottery-official`

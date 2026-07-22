# Desarrollo local en laptop

JAIOS en producción vive en el VPS (`https://jaios.justech.do`).  
En tu Mac desarrollas con **puertos alternos** para no chocar con otros proyectos (p. ej. JustColmado en `:3000`).

## Setup inicial (una vez)

```bash
cd ~/Projects/jaios

cp .env.example .env
cp docker-compose.override.example.yml docker-compose.override.yml

# Generar secretos locales (opcional pero recomendado)
# openssl rand -hex 32  → APP_SECRET_KEY y JWT_SECRET_KEY en .env
```

## Puertos locales

| Servicio   | URL / host local              | Contenedor |
|------------|-------------------------------|------------|
| Frontend   | http://localhost:3001         | :3000      |
| Gateway    | http://localhost:8001         | :80        |
| API health | http://localhost:8001/api/v1/health | —    |
| PostgreSQL | localhost:5433                | :5432      |
| Redis      | localhost:6380                | :6379      |
| n8n        | http://localhost:5679         | :5678      |
| Qdrant     | http://localhost:6334         | :6333      |

## Iniciar desarrollo

```bash
cd ~/Projects/jaios
docker compose up -d --build
docker compose exec -T backend python -m app.scripts.bootstrap_migrations
docker compose exec -T backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

Abrir: **http://localhost:3001/login**

Credenciales demo: `admin@justech.do` / `JaiosAdmin2026!` — tenant `justech`

## Detener desarrollo

```bash
cd ~/Projects/jaios
docker compose down
```

## Error en /login (webpack / Cannot read properties of undefined)

Suele ser caché `.next` corrupta o un **service worker** de JustColmado en `:3000`.

```bash
cd ~/Projects/jaios
chmod +x scripts/dev-frontend-reset.sh
./scripts/dev-frontend-reset.sh
```

Luego abre **http://localhost:3001/login** (no :3000).  
En Chrome: DevTools → Application → Service Workers → Unregister, o borrar datos del sitio para `localhost:3000`.

## Reglas

- `docker-compose.override.yml` está en `.gitignore` — **no afecta producción**.
- Producción usa solo `docker-compose.yml` + `.env` del VPS.
- **No** commitear `.env` ni apuntar a `jaios.justech.do` en desarrollo local.

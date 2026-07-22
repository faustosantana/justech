#!/usr/bin/env bash
# Reinicia el frontend local limpiando caché (.next) — corrige errores webpack en /login.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "→ Deteniendo frontend…"
docker compose stop frontend 2>/dev/null || true

echo "→ Limpiando .next y caché…"
rm -rf frontend/.next frontend/node_modules/.cache

if [[ ! -f docker-compose.override.yml ]]; then
  echo "→ Creando docker-compose.override.yml (puertos locales 3001/8001)…"
  cp docker-compose.override.example.yml docker-compose.override.yml
fi

echo "→ Levantando frontend…"
docker compose up -d --build frontend

echo ""
echo "Listo. Abre:"
echo "  http://localhost:3001/login   (recomendado — sin conflicto JustColmado)"
echo "  http://localhost:8001/api/v1/health"
echo ""
echo "Si usaste :3000 antes, borra datos del sitio en Chrome:"
echo "  DevTools → Application → Storage → Clear site data"

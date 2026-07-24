#!/usr/bin/env bash
# Publish platform numeric-relations branch as official DEV RC on :3001/:8001.
# Does NOT touch Production. Does NOT enable sync writes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

API_PORT="${RC_API_PORT:-8001}"
WEB_PORT="${RC_WEB_PORT:-3001}"
DB_URL="${DATABASE_URL:-postgresql+asyncpg://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev}"

echo "== Phase G RC publish =="
echo "root=$ROOT"
echo "HEAD=$(git rev-parse --short HEAD)"
git merge-base --is-ancestor 459a799 HEAD
git merge-base --is-ancestor 3f4d134 HEAD
git merge-base --is-ancestor cf4a732 HEAD
git merge-base --is-ancestor 255cf9c HEAD
git merge-base --is-ancestor 4c8e748 HEAD

# Stop previous NR UAT FE if present
docker rm -f jaios-nr-uat-fe 2>/dev/null || true
docker rm -f jaios-lottery-web-rc 2>/dev/null || true

# Free API port if host uvicorn is old lottery (not this RC)
if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Stopping listener on :$API_PORT for RC API swap (local only)"
  lsof -tiTCP:"$API_PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
  sleep 1
fi
pkill -f 'uat_nr_dev_server|rc_nr_dev_server' 2>/dev/null || true
sleep 1

# shellcheck disable=SC1091
set -a; [[ -f .env ]] && source .env; set +a
# Re-assert RC ports/DB after .env (do not let .env steal API_PORT)
API_PORT="${RC_API_PORT:-8001}"
WEB_PORT="${RC_WEB_PORT:-3001}"
DB_URL="postgresql+asyncpg://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
export PYTHONPATH="$ROOT/backend:$ROOT"
export DATABASE_URL="$DB_URL"
export LOTTERY_MODULE_ENABLED=true
export LOTTERY_SYNC_ENABLED=false
export LOTTERY_SYNC_WRITE_ENABLED=false

echo "API_PORT=$API_PORT WEB_PORT=$WEB_PORT"

nohup backend/.venv312/bin/uvicorn scripts.rc_nr_dev_server:app \
  --host 127.0.0.1 --port "$API_PORT" --log-level warning \
  > /tmp/jaios-nr-rc-api.log 2>&1 &
echo "API_PID=$!"

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$API_PORT/api/v1/health" | grep -q 'jaios-nr-rc-dev'; then
    echo "RC API healthy on :$API_PORT"
    break
  fi
  sleep 1
done
curl -sf "http://127.0.0.1:$API_PORT/api/v1/health" || { echo "API failed"; tail -40 /tmp/jaios-nr-rc-api.log; exit 1; }

# Build production frontend from THIS platform tree (validated branch)
docker build \
  -f frontend/Dockerfile \
  --target production \
  --build-arg INTERNAL_API_URL=http://host.docker.internal:"$API_PORT" \
  --build-arg NEXT_PUBLIC_API_URL= \
  --build-arg NEXT_PUBLIC_APP_NAME="JAIOS Lottery NR RC" \
  -t jaios-lottery-rc-frontend:latest \
  frontend

docker run -d --name jaios-lottery-web-rc \
  --add-host=host.docker.internal:host-gateway \
  -p "${WEB_PORT}:3001" \
  -e NODE_ENV=production \
  -e APP_ENV=staging \
  -e PORT=3001 \
  -e HOSTNAME=0.0.0.0 \
  --restart unless-stopped \
  jaios-lottery-rc-frontend:latest

echo "waiting for RC frontend..."
for _ in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:$WEB_PORT/login" >/dev/null 2>&1 \
    && curl -sf "http://127.0.0.1:$WEB_PORT/lottery/admin/numeric-relations" >/dev/null 2>&1; then
    echo "RC ready: http://127.0.0.1:$WEB_PORT (API :$API_PORT → DEV DB)"
    exit 0
  fi
  sleep 3
done
echo "RC frontend not ready" >&2
docker logs jaios-lottery-web-rc 2>&1 | tail -50 >&2 || true
exit 1

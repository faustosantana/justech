#!/usr/bin/env bash
# QA E2E Playwright — seed, pruebas funcionales y evidencia en .qa/e2e/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

E2E_DIR="$ROOT/.qa/e2e"
mkdir -p "$E2E_DIR"

echo "=== JAIOS QA E2E Playwright ==="

echo "→ Verificando servicios Docker…"
docker compose ps --status running | grep -E 'backend|frontend' >/dev/null || {
  echo "ERROR: backend/frontend no están en ejecución. Ejecute: make up"
  exit 1
}

echo "→ Seed fixtures E2E…"
docker compose exec backend python -m app.scripts.e2e_seed_fixtures /tmp/e2e-fixtures.json
docker compose cp backend:/tmp/e2e-fixtures.json "$E2E_DIR/fixtures.json"

echo "→ Ejecutando Playwright (Chrome del sistema en host)…"
set +e
(
  cd "$ROOT/e2e"
  npm install --no-audit --no-fund 2>/dev/null || true
  PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://localhost:3000}" \
  PLAYWRIGHT_API_URL="${PLAYWRIGHT_API_URL:-http://localhost:8000/api/v1}" \
  E2E_DIR="$E2E_DIR" \
  npm test
)
E2E_EXIT=$?
set -e

echo "→ Generando resumen…"
python3 "$ROOT/scripts/generate_e2e_summary.py"

if [[ "$E2E_EXIT" -eq 0 ]]; then
  echo "✅ QA E2E completo — ver $E2E_DIR/e2e-summary.md"
else
  echo "❌ QA E2E falló (exit $E2E_EXIT) — ver $E2E_DIR/e2e-summary.md y $E2E_DIR/html-report/"
  exit "$E2E_EXIT"
fi

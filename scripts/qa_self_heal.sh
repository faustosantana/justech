#!/usr/bin/env bash
# JAIOS Self-Healing QA Loop
# Detección separada frontend/backend; healers precisos y rápidos.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPORT_DIR="$ROOT/.qa"
REPORT_FILE="$REPORT_DIR/self-heal-report.md"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
API_PREFIX="${GATEWAY_URL}/api/v1"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# --- Colecciones ---
declare -a ERRORS_FOUND=()
declare -a FRONTEND_ERRORS=()
declare -a BACKEND_ERRORS=()
declare -a ACTIONS_APPLIED=()
declare -a ROUTES_OK=()
declare -a ROUTES_FAIL=()
declare -a APIS_OK=()
declare -a APIS_FAIL=()
declare -a ROOT_CAUSES=()

FRONTEND_NEEDS_HEAL=0
BACKEND_NEEDS_HEAL=0

# Patrones en líneas de error frontend (no logs INFO normales)
FRONTEND_LOG_PATTERNS=(
  "ENOENT"
  ".next/server/middleware.js"
  "Fast Refresh"
  "runtime error"
  "Hydration failed"
  "Module not found"
  "routes-manifest.json"
  "PageNotFoundError"
  "next/dist"
)

# Patrones en líneas de error backend (no sqlalchemy.engine.Engine INFO)
BACKEND_LOG_PATTERNS=(
  "Traceback"
  "500 Internal Server Error"
  "MissingGreenlet"
  "ValidationError"
  "sqlalchemy.exc"
  "pydantic_core"
  "IntegrityError"
  "OperationalError"
  "ProgrammingError"
)

FRONTEND_ROUTES=(
  "/login"
  "/dashboard"
  "/search"
  "/documents"
  "/prices"
  "/prices/drafts"
  "/dgcp"
  "/odoo"
  "/m365"
  "/m365/cuentas"
  "/work"
  "/tasks"
  "/notifications"
  "/oportunidades"
  "/empresas"
  "/configuracion"
  "/admin"
  "/admin/usuarios"
  "/admin/modulos"
  "/admin/reglas"
)

API_ENDPOINTS=(
  "/health"
  "/odoo/health"
  "/dgcp/dashboard"
  "/m365/health"
  "/tasks"
  "/work"
  "/notifications"
  "/search?q=Banco"
  "/search?q=Dell"
  "/search?q=MIREX"
  "/search/analytics?days=7"
  "/documents/health"
  "/companies"
  "/company-context"
  "/company-context/allowed"
  "/dashboard/executive"
  "/knowledge/health"
)

log_error() { ERRORS_FOUND+=("$1"); echo "❌ $1"; }
log_fe_error() { FRONTEND_ERRORS+=("$1"); ERRORS_FOUND+=("[frontend] $1"); echo "❌ [frontend] $1"; }
log_be_error() { BACKEND_ERRORS+=("$1"); ERRORS_FOUND+=("[backend] $1"); echo "❌ [backend] $1"; }
log_action() { ACTIONS_APPLIED+=("$1"); echo "🔧 $1"; }
log_ok() { echo "✅ $1"; }

mkdir -p "$REPORT_DIR"

# --- Utilidades HTTP ---
http_status() {
  local url="$1"
  python3 - <<PY 2>/dev/null || echo "000"
import urllib.request
try:
    r = urllib.request.urlopen("$url", timeout=90)
    print(r.status)
except Exception as e:
    if hasattr(e, 'code'):
        print(e.code)
    else:
        print("000")
PY
}

http_body_snippet() {
  local url="$1"
  python3 - <<PY 2>/dev/null || echo ""
import urllib.request
try:
    r = urllib.request.urlopen("$url", timeout=90)
    print(r.read(8000).decode("utf-8", errors="replace")[:4000])
except Exception:
    print("")
PY
}

route_has_real_content() {
  local body="$1"
  if [[ -z "$body" ]]; then return 1; fi
  if echo "$body" | grep -qiE "404|This page could not be found|Internal Server Error|ENOENT"; then
    return 1
  fi
  if echo "$body" | grep -qiE "JAIOS|Verificando sesión|Iniciar|Entrar|Dashboard|Odoo|Microsoft|Work Hub|Tasks|Notificaciones|DGCP"; then
    return 0
  fi
  if echo "$body" | grep -qi "<html"; then return 0; fi
  return 1
}

get_auth_token() {
  local token_file="$ROOT/backend/.qa/e2e-tokens.json"
  mkdir -p "$ROOT/backend/.qa"
  if docker compose exec -T backend python -m app.scripts.e2e_auth_token "/app/.qa/e2e-tokens.json" >/dev/null 2>&1; then
    if [[ -f "$token_file" ]]; then
      python3 - <<PY 2>/dev/null || echo ""
import json
from pathlib import Path
p = Path("${token_file}")
print(json.loads(p.read_text()).get("access_token", ""))
PY
      return
    fi
  fi
  docker compose exec -T backend python -m app.scripts.e2e_auth_token 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null \
    | tr -d '\r' || echo ""
}

api_status_authed() {
  local path="$1"
  local token="$2"
  API_PREFIX="$API_PREFIX" AUTH_TOKEN="$token" API_PATH="$path" python3 - <<'PY' 2>/dev/null || echo "000"
import os, urllib.request
base = os.environ.get("API_PREFIX", "")
path = os.environ.get("API_PATH", "")
token = os.environ.get("AUTH_TOKEN", "")
req = urllib.request.Request(
    f"{base}{path}",
    headers={"Authorization": f"Bearer {token}"},
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(r.status)
except Exception as e:
    print(getattr(e, 'code', '000'))
PY
}

# --- 1. Docker ps ---
check_docker() {
  echo "=== 1. Docker compose ps ==="
  if ! docker compose ps --format json >/dev/null 2>&1; then
    log_error "docker compose ps falló"
    return 1
  fi
  local running
  running=$(docker compose ps --services --filter status=running 2>/dev/null | tr '\n' ' ')
  log_action "Servicios en ejecución: ${running:-ninguno}"
  if ! echo "$running" | grep -q "frontend"; then
    log_fe_error "frontend no está running"
    FRONTEND_NEEDS_HEAL=1
  fi
  if ! echo "$running" | grep -q "backend"; then
    log_be_error "backend no está running"
    BACKEND_NEEDS_HEAL=1
  fi
  if ! echo "$running" | grep -q "gateway"; then
    log_error "gateway no está running"
  fi
}

# --- 2a. Escaneo logs frontend ---
filter_frontend_error_lines() {
  # Solo líneas con señales reales de fallo (evita falsos positivos de next dev normal)
  grep -iE "ERROR|⨯|ENOENT|Hydration failed|Module not found|Fast Refresh|PageNotFoundError|routes-manifest|runtime error|middleware\.js" || true
}

scan_frontend_logs() {
  echo "=== 2a. Escaneo logs frontend ==="
  local fe_logs fe_errors
  fe_logs="$(docker compose logs frontend --tail=200 2>/dev/null || true)"
  fe_errors="$(echo "$fe_logs" | filter_frontend_error_lines)"

  if [[ -z "$fe_errors" ]]; then
    log_ok "Sin errores frontend en logs recientes"
  fi

  for pat in "${FRONTEND_LOG_PATTERNS[@]}"; do
    if echo "$fe_errors" | grep -qi "$pat"; then
      log_fe_error "Patrón en logs frontend: $pat"
      FRONTEND_NEEDS_HEAL=1
    fi
  done

  for route in "${FRONTEND_ROUTES[@]}"; do
    if echo "$fe_logs" | grep -qE "GET ${route} 404"; then
      log_fe_error "Log frontend: GET ${route} 404"
      FRONTEND_NEEDS_HEAL=1
    fi
    if echo "$fe_logs" | grep -qE "GET ${route} 500"; then
      log_fe_error "Log frontend: GET ${route} 500"
      FRONTEND_NEEDS_HEAL=1
    fi
  done
}

# --- 2b. Escaneo logs backend ---
filter_backend_error_lines() {
  # Excluye INFO sqlalchemy.engine.Engine (ruido normal)
  grep -iE "ERROR|Traceback|Exception in ASGI|500 Internal Server Error|MissingGreenlet|ValidationError|sqlalchemy\.exc|pydantic_core|IntegrityError|OperationalError|ProgrammingError" \
    | grep -viE "sqlalchemy\.engine\.Engine" || true
}

scan_backend_logs() {
  echo "=== 2b. Escaneo logs backend ==="
  local be_logs be_errors
  be_logs="$(docker compose logs backend --tail=200 2>/dev/null || true)"
  be_errors="$(echo "$be_logs" | filter_backend_error_lines)"

  if [[ -z "$be_errors" ]]; then
    log_ok "Sin errores backend en logs recientes"
  fi

  for pat in "${BACKEND_LOG_PATTERNS[@]}"; do
    if echo "$be_errors" | grep -qi "$pat"; then
      log_be_error "Patrón en logs backend: $pat"
      BACKEND_NEEDS_HEAL=1
    fi
  done

  if [[ -n "$be_errors" ]]; then
    extract_backend_root_cause "$be_errors"
  fi
}

extract_backend_root_cause() {
  local be_logs="$1"
  local snippet
  snippet="$(echo "$be_logs" | grep -A8 -E "Traceback|MissingGreenlet|ValidationError|sqlalchemy\.exc|pydantic" | tail -12 | sed 's/^/  /')"
  if [[ -n "$snippet" ]]; then
    ROOT_CAUSES+=("$snippet")
  fi
}

# --- 3. Corrupción .next (solo frontend) ---
detect_next_corruption() {
  echo "=== 3. Detección corrupción .next ==="
  if docker compose ps --services --filter status=running 2>/dev/null | grep -q frontend; then
    if ! docker compose exec -T frontend sh -c "test -f .next/server/middleware.js" 2>/dev/null; then
      log_fe_error "ENOENT o ausente: .next/server/middleware.js"
      FRONTEND_NEEDS_HEAL=1
    else
      log_ok ".next/server/middleware.js presente"
    fi
  else
    log_fe_error "frontend no running — no se puede verificar middleware.js"
    FRONTEND_NEEDS_HEAL=1
  fi
}

heal_frontend() {
  echo "=== Reparación automática frontend ==="
  log_action "[frontend] docker compose stop frontend"
  docker compose stop frontend >/dev/null 2>&1 || true

  log_action "[frontend] Limpiar .next y node_modules/.cache"
  rm -rf "$ROOT/frontend/.next" "$ROOT/frontend/node_modules/.cache"

  log_action "[frontend] docker compose up -d frontend (next dev regenera .next)"
  docker compose up -d frontend

  log_action "[frontend] Esperar arranque next dev (15s)"
  sleep 15

  # Limpiar errores frontend previos y re-escanear solo frontend
  local kept=()
  for e in "${ERRORS_FOUND[@]}"; do
    if [[ "$e" != \[frontend\]* ]]; then
      kept+=("$e")
    fi
  done
  if ((${#kept[@]} > 0)); then
    ERRORS_FOUND=("${kept[@]}")
  else
    ERRORS_FOUND=()
  fi
  FRONTEND_ERRORS=()
  scan_frontend_logs
  detect_next_corruption
}

heal_backend() {
  echo "=== Reparación automática backend ==="
  local be_logs
  be_logs="$(docker compose logs backend --tail=200 2>/dev/null || true)"
  extract_backend_root_cause "$be_logs"

  log_action "[backend] pytest"
  if docker compose exec -T backend pytest -q 2>&1 | tail -5; then
    log_ok "pytest OK"
  else
    log_be_error "pytest falló"
    BACKEND_NEEDS_HEAL=1
  fi

  log_action "[backend] docker compose restart backend"
  docker compose restart backend >/dev/null 2>&1 || true
  sleep 8

  # Limpiar errores backend previos y re-escanear solo backend
  local kept=()
  for e in "${ERRORS_FOUND[@]}"; do
    if [[ "$e" != \[backend\]* ]]; then
      kept+=("$e")
    fi
  done
  if ((${#kept[@]} > 0)); then
    ERRORS_FOUND=("${kept[@]}")
  else
    ERRORS_FOUND=()
  fi
  BACKEND_ERRORS=()
  scan_backend_logs
}

# --- Validar rutas ---
validate_routes() {
  echo "=== 5. Validación rutas frontend ==="
  ROUTES_OK=()
  ROUTES_FAIL=()
  for route in "${FRONTEND_ROUTES[@]}"; do
    local url="${FRONTEND_URL}${route}"
    local status body
    status="$(http_status "$url")"
    body="$(http_body_snippet "$url")"
    if [[ "$status" == "200" ]] && route_has_real_content "$body"; then
      ROUTES_OK+=("$route → HTTP $status")
      log_ok "$route → HTTP $status"
    else
      ROUTES_FAIL+=("$route → HTTP $status (contenido inválido o vacío)")
      if [[ "$status" == "404" ]]; then
        log_fe_error "Ruta frontend 404: $route"
      elif [[ -z "$body" ]] || ! route_has_real_content "$body"; then
        log_fe_error "Pantalla blanca o contenido inválido: $route"
      else
        log_fe_error "$route → HTTP $status — contenido inválido"
      fi
      FRONTEND_NEEDS_HEAL=1
    fi
  done
}

# --- Validar APIs ---
validate_apis() {
  echo "=== 6. Validación APIs ==="
  APIS_OK=()
  APIS_FAIL=()
  local token
  token="$(get_auth_token)"
  if [[ -z "$token" ]]; then
    log_be_error "No se pudo obtener token de autenticación para APIs"
    BACKEND_NEEDS_HEAL=1
    for ep in "${API_ENDPOINTS[@]}"; do
      APIS_FAIL+=("$ep → sin token")
    done
    return
  fi
  for ep in "${API_ENDPOINTS[@]}"; do
    local st
    st="$(api_status_authed "$ep" "$token")"
    if [[ "$st" == "200" ]]; then
      APIS_OK+=("$ep → HTTP $st")
      log_ok "API $ep → HTTP $st"
    else
      APIS_FAIL+=("$ep → HTTP $st")
      log_be_error "API $ep → HTTP $st"
      BACKEND_NEEDS_HEAL=1
    fi
  done
}

apply_healers() {
  local reason="$1"
  if [[ "$FRONTEND_NEEDS_HEAL" -eq 1 && "$BACKEND_NEEDS_HEAL" -eq 1 ]]; then
    log_action "Heal mixto ($reason): backend + frontend"
    heal_backend
    heal_frontend
  elif [[ "$FRONTEND_NEEDS_HEAL" -eq 1 ]]; then
    log_action "Heal frontend ($reason)"
    heal_frontend
  elif [[ "$BACKEND_NEEDS_HEAL" -eq 1 ]]; then
    log_action "Heal backend ($reason) — sin rebuild frontend"
    heal_backend
  fi
}

# --- Reporte ---
write_report() {
  local final_status="$1"
  mkdir -p "$REPORT_DIR"
  {
    echo "# JAIOS Self-Heal QA Report"
    echo ""
    echo "- **Generado:** $TIMESTAMP"
    echo "- **Estado final:** $final_status"
    echo "- **Frontend:** $FRONTEND_URL"
    echo "- **Gateway API:** $GATEWAY_URL"
    echo ""
    echo "## Errores frontend"
    if [[ ${#FRONTEND_ERRORS[@]} -eq 0 ]]; then
      echo "- Ninguno"
    else
      for e in "${FRONTEND_ERRORS[@]}"; do echo "- $e"; done
    fi
    echo ""
    echo "## Errores backend"
    if [[ ${#BACKEND_ERRORS[@]} -eq 0 ]]; then
      echo "- Ninguno"
    else
      for e in "${BACKEND_ERRORS[@]}"; do echo "- $e"; done
    fi
    echo ""
    echo "## Causa raíz backend"
    if [[ ${#ROOT_CAUSES[@]} -eq 0 ]]; then
      echo "- No detectada"
    else
      for rc in "${ROOT_CAUSES[@]}"; do
        echo '```'
        echo "$rc"
        echo '```'
      done
    fi
    echo ""
    echo "## Acciones aplicadas"
    if [[ ${#ACTIONS_APPLIED[@]} -eq 0 ]]; then
      echo "- Ninguna"
    else
      for a in "${ACTIONS_APPLIED[@]}"; do echo "- $a"; done
    fi
    echo ""
    echo "## Rutas verificadas"
    if [[ ${#ROUTES_OK[@]} -gt 0 ]]; then
      for r in "${ROUTES_OK[@]}"; do echo "- ✅ $r"; done
    fi
    if [[ ${#ROUTES_FAIL[@]} -gt 0 ]]; then
      for r in "${ROUTES_FAIL[@]}"; do echo "- ❌ $r"; done
    fi
    if [[ ${#ROUTES_OK[@]} -eq 0 && ${#ROUTES_FAIL[@]} -eq 0 ]]; then
      echo "- (sin validar)"
    fi
    echo ""
    echo "## APIs verificadas"
    if [[ ${#APIS_OK[@]} -gt 0 ]]; then
      for a in "${APIS_OK[@]}"; do echo "- ✅ $a"; done
    fi
    if [[ ${#APIS_FAIL[@]} -gt 0 ]]; then
      for a in "${APIS_FAIL[@]}"; do echo "- ❌ $a"; done
    fi
    if [[ ${#APIS_OK[@]} -eq 0 && ${#APIS_FAIL[@]} -eq 0 ]]; then
      echo "- (sin validar)"
    fi
    echo ""
    echo "## Reglas heal"
    echo "- **Frontend:** stop → limpiar .next → up (sin rebuild si error es solo backend)"
    echo "- **Backend:** pytest → restart backend → revalidar APIs"
    echo "- **Mixto:** ambos healers solo si fallan frontend y backend"
    echo "- Nunca \`npm run build\` con \`next dev\` activo (usar \`make qa-frontend-build\`)"
    echo "- No cerrar fases si este reporte no es **PASS**."
    echo ""
    echo "## Estados de cierre permitidos"
    echo "- En desarrollo · Validación fallida · Corrección automática aplicada · Validación parcial · Validación completa"
    echo "- **Nunca** \"completado\" sin qa-self-heal OK."
  } > "$REPORT_FILE"
  echo ""
  echo "📄 Reporte: $REPORT_FILE"
}

# --- Main ---
main() {
  echo "╔══════════════════════════════════════════╗"
  echo "║   JAIOS Self-Healing QA Loop             ║"
  echo "╚══════════════════════════════════════════╝"
  echo ""

  if ! docker compose ps --services --filter status=running 2>/dev/null | grep -q frontend; then
    log_action "Levantando servicios (docker compose up -d)"
    docker compose up -d
    sleep 15
  fi

  check_docker
  scan_frontend_logs
  scan_backend_logs
  detect_next_corruption

  # Fast path: sin issues en logs/middleware → validar directo
  if [[ "$FRONTEND_NEEDS_HEAL" -eq 0 && "$BACKEND_NEEDS_HEAL" -eq 0 ]]; then
    log_ok "Sin señales de error en logs — validación directa"
    validate_routes
    validate_apis
  else
    apply_healers "detección inicial en logs"
    validate_routes
    validate_apis

    # Re-heal según fallos de validación (solo la capa afectada)
    FRONTEND_NEEDS_HEAL=0
    BACKEND_NEEDS_HEAL=0
    [[ ${#ROUTES_FAIL[@]} -gt 0 ]] && FRONTEND_NEEDS_HEAL=1
    [[ ${#APIS_FAIL[@]} -gt 0 ]] && BACKEND_NEEDS_HEAL=1

    if [[ "$FRONTEND_NEEDS_HEAL" -eq 1 || "$BACKEND_NEEDS_HEAL" -eq 1 ]]; then
      apply_healers "post-validación"
      validate_routes
      validate_apis
    fi
  fi

  local final="PASS"
  if [[ ${#ROUTES_FAIL[@]} -gt 0 ]] || [[ ${#APIS_FAIL[@]} -gt 0 ]]; then
    final="FAIL"
  fi

  write_report "$final"

  echo ""
  if [[ "$final" == "PASS" ]]; then
    echo "✅ qa-self-heal: PASS"
    exit 0
  else
    echo "❌ qa-self-heal: FAIL — ver $REPORT_FILE"
    exit 1
  fi
}

main "$@"

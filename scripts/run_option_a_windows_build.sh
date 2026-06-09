#!/usr/bin/env bash
# Opción A — totalmente automático (sin prompts)
# Requisito: GH_TOKEN en .env o entorno (permisos: repo, workflow)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPO="${JAIOS_GITHUB_REPO:-justech/jaios}"
WORKFLOW="desktop-windows-build.yml"

echo "=== JAIOS — Opción A automática (Windows CI) ==="

# Cargar GH_TOKEN desde .env si existe
if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi

if [[ -n "${GH_TOKEN:-}" ]]; then
  echo "→ Autenticando gh con GH_TOKEN…"
  echo "$GH_TOKEN" | gh auth login --with-token
elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  echo "→ Autenticando gh con GITHUB_TOKEN…"
  echo "$GITHUB_TOKEN" | gh auth login --with-token
fi

if ! gh auth status >/dev/null 2>&1; then
  echo ""
  echo "❌ Falta credencial GitHub (sin interacción posible desde el agente)."
  echo ""
  echo "Agrega UNA línea a ~/Projects/jaios/.env :"
  echo "  GH_TOKEN=ghp_xxxxxxxx"
  echo ""
  echo "Crear token: https://github.com/settings/tokens"
  echo "Permisos: repo, workflow (o classic: repo + workflow)"
  echo ""
  echo "Luego ejecuta de nuevo: ./scripts/run_option_a_windows_build.sh"
  exit 1
fi

echo "✓ GitHub: $(gh api user -q .login)"

if ! git rev-parse HEAD >/dev/null 2>&1; then
  echo "→ Commit inicial…"
  git add -A
  git commit -m "$(cat <<'EOF'
JAIOS platform + desktop client with Windows CI build.

Includes Tauri desktop app, GitHub Actions for Windows MSI/NSIS, and Mac installers workflow.
EOF
)"
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "→ Creando repo $REPO…"
  if gh repo view "$REPO" >/dev/null 2>&1; then
    git remote add origin "https://github.com/$REPO.git"
    git push -u origin HEAD
  else
    gh repo create "$REPO" --private --source=. --remote=origin --push
  fi
else
  echo "→ Push origin…"
  git push -u origin HEAD
fi

echo "→ Workflow $WORKFLOW…"
gh workflow run "$WORKFLOW"

sleep 5
RUN_ID="$(gh run list --workflow="$WORKFLOW" --limit=1 --json databaseId --jq '.[0].databaseId')"
echo "→ Run $RUN_ID (espera ~15-25 min)…"
gh run watch "$RUN_ID"

STATUS="$(gh run view "$RUN_ID" --json conclusion --jq .conclusion)"
if [[ "$STATUS" != "success" ]]; then
  echo "❌ Workflow falló: $STATUS"
  gh run view "$RUN_ID" --log-failed 2>&1 | tail -80
  exit 1
fi

echo "→ Descargando artifacts…"
chmod +x scripts/download_windows_desktop_artifacts.sh
./scripts/download_windows_desktop_artifacts.sh "$RUN_ID"

echo ""
echo "✅ Instaladores Windows:"
ls -lah .qa/desktop-installers/windows/

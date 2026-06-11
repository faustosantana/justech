#!/usr/bin/env bash
# Push del commit pendiente a GitHub.
# Uso: GH_TOKEN=ghp_xxx ./scripts/push_to_github.sh

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$TOKEN" ]]; then
  echo "Falta GH_TOKEN o GITHUB_TOKEN."
  echo ""
  echo "1. Crear token: https://github.com/settings/tokens (scope: repo)"
  echo "2. Ejecutar:"
  echo "   GH_TOKEN=ghp_xxxx ./scripts/push_to_github.sh"
  echo ""
  echo "O agregar a .env:"
  echo "   GH_TOKEN=ghp_xxxx"
  exit 1
fi

echo "$TOKEN" | gh auth login --with-token
git -c safe.directory="$(pwd)" fetch origin main
git -c safe.directory="$(pwd)" push origin main
echo "Push completado: $(git -c safe.directory="$(pwd)" log -1 --oneline)"

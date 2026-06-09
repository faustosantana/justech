#!/usr/bin/env bash
# Descarga artifacts Windows de GitHub Actions a .qa/desktop-installers/windows/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/.qa/desktop-installers/windows"
WORKFLOW="desktop-windows-build.yml"
VERSION="0.1.0"

mkdir -p "$OUT"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) no instalado."
  echo "  brew install gh && gh auth login"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh no autenticado. Ejecute: gh auth login"
  exit 1
fi

echo "=== Descargar instaladores Windows JAIOS ==="

RUN_ID="${1:-}"
if [[ -z "$RUN_ID" ]]; then
  echo "→ Buscando último run exitoso de $WORKFLOW…"
  RUN_ID="$(gh run list --workflow="$WORKFLOW" --status=success --limit=1 --json databaseId --jq '.[0].databaseId')"
  if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
    echo "No hay run exitoso. Disparando workflow…"
    gh workflow run "$WORKFLOW"
    echo "Esperando workflow (puede tardar ~20 min)…"
    gh run watch "$(gh run list --workflow=$WORKFLOW --limit=1 --json databaseId --jq '.[0].databaseId')"
    RUN_ID="$(gh run list --workflow="$WORKFLOW" --status=success --limit=1 --json databaseId --jq '.[0].databaseId')"
  fi
fi

echo "→ Descargando run $RUN_ID…"
TMP="$(mktemp -d)"
gh run download "$RUN_ID" -D "$TMP"

shopt -s nullglob
msi=( "$TMP"/**/JAIOS*.msi "$TMP"/**/*.msi )
exe=( "$TMP"/**/*setup*.exe "$TMP"/**/*.exe )
shopt -u nullglob

MSI_DEST="$OUT/JAIOS_${VERSION}_x64.msi"
EXE_DEST="$OUT/JAIOS_${VERSION}_x64-setup.exe"

found_msi=""
found_exe=""
for f in "${msi[@]:-}"; do
  [[ -f "$f" ]] && found_msi="$f" && break
done
for f in "${exe[@]:-}"; do
  [[ -f "$f" ]] && found_exe="$f" && break
done

if [[ -z "$found_msi" || -z "$found_exe" ]]; then
  echo "ERROR: artifacts incompletos en run $RUN_ID"
  find "$TMP" -type f
  exit 1
fi

cp "$found_msi" "$MSI_DEST"
cp "$found_exe" "$EXE_DEST"
rm -rf "$TMP"

echo ""
echo "✅ Instaladores Windows listos:"
echo "   $MSI_DEST"
echo "   $EXE_DEST"
ls -lah "$OUT"

python3 "$ROOT/scripts/generate_desktop_installer_report.py" 2>/dev/null || true

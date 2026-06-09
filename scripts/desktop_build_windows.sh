#!/usr/bin/env bash
# Build instaladores Windows JAIOS Desktop (.msi + NSIS setup.exe)
# Ejecutar en Windows (Git Bash / CI windows-latest) o: make desktop-build-windows
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/desktop"
QA="$ROOT/.qa"
WIN_OUT="$QA/desktop-installers/windows"
BUNDLE="$DESKTOP/src-tauri/target/release/bundle"

if [[ ! -f "$DESKTOP/package.json" ]]; then
  echo "ERROR: no se encuentra $DESKTOP/package.json"
  ls -la "$ROOT" || true
  ls -la "$DESKTOP" || true
  exit 1
fi

VERSION="$(cd "$DESKTOP" && node -p "require('./package.json').version")"

echo "=== JAIOS Desktop — build Windows v$VERSION ==="

mkdir -p "$WIN_OUT"

# shellcheck disable=SC1091
source "$HOME/.cargo/env" 2>/dev/null || true
export PATH="$HOME/.cargo/bin:$PATH"

if ! command -v node >/dev/null; then
  echo "ERROR: Node.js requerido"
  exit 1
fi
if ! command -v cargo >/dev/null; then
  echo "ERROR: Rust/cargo requerido"
  exit 1
fi

echo "→ npm install…"
if ! npm install --no-audit --no-fund; then
  npm config set strict-ssl false
  npm install --no-audit --no-fund
  npm config set strict-ssl true
fi

echo "→ Iconos (si faltan)…"
if [[ ! -f "$DESKTOP/src-tauri/icons/icon.ico" ]]; then
  python3 "$ROOT/scripts/generate_jaios_icons.py"
fi

cd "$DESKTOP"
export CARGO_TARGET_DIR="$DESKTOP/src-tauri/target"

echo "→ vite build…"
npm run build

echo "→ tauri build (msi + nsis)…"
npm run desktop:build

shopt -s nullglob
msi_files=( "$BUNDLE/msi/"*.msi )
exe_files=( "$BUNDLE/nsis/"*.exe )
shopt -u nullglob

if (( ${#msi_files[@]} == 0 )); then
  echo "ERROR: no se generó .msi en $BUNDLE/msi/"
  ls -la "$BUNDLE/msi/" 2>/dev/null || ls -la "$BUNDLE/" 2>/dev/null || true
  exit 1
fi
if (( ${#exe_files[@]} == 0 )); then
  echo "ERROR: no se generó setup .exe en $BUNDLE/nsis/"
  ls -la "$BUNDLE/nsis/" 2>/dev/null || true
  exit 1
fi

MSI_SRC="${msi_files[0]}"
EXE_SRC="${exe_files[0]}"
MSI_DEST="$WIN_OUT/JAIOS_${VERSION}_x64.msi"
EXE_DEST="$WIN_OUT/JAIOS_${VERSION}_x64-setup.exe"

cp "$MSI_SRC" "$MSI_DEST"
cp "$EXE_SRC" "$EXE_DEST"

echo ""
echo "✅ Instaladores Windows:"
echo "   MSI:  $MSI_DEST"
echo "   EXE:  $EXE_DEST"
ls -lah "$WIN_OUT"

python3 "$ROOT/scripts/generate_desktop_installer_report.py" 2>/dev/null || true

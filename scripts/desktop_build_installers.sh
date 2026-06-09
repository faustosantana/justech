#!/usr/bin/env bash
# Build instaladores JAIOS Desktop (.dmg/.app Mac, .msi/.exe Windows)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/desktop"
QA="$ROOT/.qa"
OUT="$QA/desktop-installers"
MAC_OUT="$OUT/mac"
WIN_OUT="$OUT/windows"
BUNDLE="$DESKTOP/src-tauri/target/release/bundle"

echo "=== JAIOS Desktop — build instaladores ==="

# Preparar entorno (Rust, npm, tauri-cli)
chmod +x "$ROOT/scripts/desktop_prepare_build_env.sh"
"$ROOT/scripts/desktop_prepare_build_env.sh"

# shellcheck disable=SC1091
source "$HOME/.cargo/env" 2>/dev/null || true
export PATH="$HOME/.cargo/bin:$PATH"

echo "→ Generando iconos JAIOS…"
python3 "$ROOT/scripts/generate_jaios_icons.py"

cd "$DESKTOP"
export CARGO_TARGET_DIR="$DESKTOP/src-tauri/target"
echo "→ vite build…"
npm run build

echo "→ tauri build (instaladores)…"
npm run desktop:build

mkdir -p "$MAC_OUT" "$WIN_OUT"

copy_if_exists() {
  local pattern="$1"
  local dest="$2"
  shopt -s nullglob
  local files=( $pattern )
  shopt -u nullglob
  if (( ${#files[@]} == 0 )); then
    return 0
  fi
  for f in "${files[@]}"; do
    echo "  → $f"
    if [[ -d "$f" ]]; then
      rm -rf "$dest/$(basename "$f")"
      cp -R "$f" "$dest/"
    else
      cp "$f" "$dest/"
    fi
  done
}

echo ""
echo "=== Copiando artefactos ==="

if [[ "$(uname -s)" == "Darwin" ]]; then
  copy_if_exists "$BUNDLE/dmg/"*.dmg "$MAC_OUT"
  if [[ -d "$BUNDLE/macos/JAIOS.app" ]]; then
    rm -rf "$MAC_OUT/JAIOS.app"
    cp -R "$BUNDLE/macos/JAIOS.app" "$MAC_OUT/"
  fi
  copy_if_exists "$BUNDLE/macos/"*.app "$MAC_OUT"
  shopt -s nullglob
  dmg_files=( "$MAC_OUT"/JAIOS_*.dmg )
  if (( ${#dmg_files[@]} == 0 )) && [[ -d "$MAC_OUT/JAIOS.app" ]]; then
    echo "→ Creando .dmg con hdiutil (fallback)…"
    hdiutil create -volname "JAIOS" -srcfolder "$MAC_OUT/JAIOS.app" -ov -format UDZO \
      "$MAC_OUT/JAIOS_0.1.0_x64.dmg" || true
  fi
  shopt -u nullglob
fi

if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ -n "${OS:-}" && "${OS}" == "Windows_NT" ]]; then
  copy_if_exists "$BUNDLE/msi/"*.msi "$WIN_OUT"
  copy_if_exists "$BUNDLE/nsis/"*.exe "$WIN_OUT"
fi

# Si se ejecuta en Mac pero hay artefactos Windows (cross), copiarlos también
copy_if_exists "$BUNDLE/msi/"*.msi "$WIN_OUT"
copy_if_exists "$BUNDLE/nsis/"*.exe "$WIN_OUT"

echo ""
echo "=== Instaladores en $OUT ==="
find "$OUT" -type f \( -name '*.dmg' -o -name '*.msi' -o -name '*.exe' \) 2>/dev/null || true
find "$OUT" -type d -name '*.app' 2>/dev/null || true

python3 "$ROOT/scripts/generate_desktop_installer_report.py" || true

echo ""
echo "✅ Build completado."
echo "   Mac:     $MAC_OUT"
echo "   Windows: $WIN_OUT (requiere build en Windows o GitHub Actions)"

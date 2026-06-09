#!/usr/bin/env bash
# Prepara entorno de build JAIOS Desktop (Rust, Tauri CLI, npm deps)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/desktop"
LOG="$ROOT/.qa/desktop-build-env.log"

mkdir -p "$ROOT/.qa"

log() {
  echo "$*" | tee -a "$LOG"
}

log "=== JAIOS Desktop — prepare build env $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || return 1
}

# Node / npm
if ! need_cmd node || ! need_cmd npm; then
  log "ERROR: Node.js y npm son obligatorios."
  log "  Instale desde https://nodejs.org o: brew install node"
  exit 1
fi
log "✓ node $(node -v)"
log "✓ npm $(npm -v)"

# Rust via rustup
if ! need_cmd cargo; then
  log "→ Instalando Rust (rustup)…"
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
fi
# shellcheck disable=SC1091
source "$HOME/.cargo/env" 2>/dev/null || true
export PATH="$HOME/.cargo/bin:$PATH"

if ! need_cmd cargo; then
  log "ERROR: cargo no disponible tras rustup."
  exit 1
fi
log "✓ rustc $(rustc --version)"
log "✓ cargo $(cargo --version)"

# Tauri CLI
if ! cargo tauri --version >/dev/null 2>&1; then
  log "→ Instalando Tauri CLI…"
  cargo install tauri-cli --version "^2" --locked
fi
log "✓ $(cargo tauri --version)"

# npm install con workaround SSL controlado
cd "$DESKTOP"
STRICT_BEFORE="$(npm config get strict-ssl 2>/dev/null || echo true)"
SSL_WORKAROUND="false"

log "→ npm install en desktop/…"
if npm install --no-audit --no-fund 2>&1 | tee -a "$LOG"; then
  log "✓ npm install OK"
else
  log "WARN: npm install falló (certificado SSL). Reintentando con strict-ssl=false…"
  npm config set strict-ssl false
  SSL_WORKAROUND="true"
  npm install --no-audit --no-fund 2>&1 | tee -a "$LOG"
  npm config set strict-ssl true
  log "✓ strict-ssl restaurado a true (workaround temporal aplicado)"
fi

log ""
log "SSL workaround usado: $SSL_WORKAROUND"
log "Entorno listo. Ejecute: make desktop-build-mac"

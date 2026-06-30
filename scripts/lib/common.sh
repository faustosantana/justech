#!/usr/bin/env bash
# Funciones compartidas — scripts Hellenia Odoo
# Uso: source "$(dirname "$SCRIPT_DIR")/lib/common.sh"  desde scripts/*.sh

hellenia_log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

hellenia_require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    hellenia_log "ERROR: Archivo requerido no encontrado: $file"
    exit 1
  fi
}

hellenia_load_env() {
  hellenia_require_file "$1"
  # shellcheck disable=SC1090
  source "$1"
}

# Nombre de contenedor Docker Compose v2: {project}-{service}-1
hellenia_container() {
  local project="${1:?}"
  local service="${2:?}"
  echo "${project}-${service}-1"
}

# Nombre de volumen: {project}_{volume}
hellenia_volume() {
  local project="${1:?}"
  local volume="${2:?}"
  echo "${project}_${volume}"
}

hellenia_container_running() {
  docker ps --format '{{.Names}}' | grep -qx "$1"
}

# Marca backup semanal/mensual con symlinks en backup_root (no dentro del dest)
hellenia_mark_backup_tier() {
  local backup_root="$1"
  local dest="$2"
  local ts_name dow dom
  ts_name="$(basename "$dest")"
  dow=$(date +%u)
  dom=$(date +%d)
  if [[ "${dom}" == "01" ]]; then
    ln -sfn "$ts_name" "${backup_root}/${ts_name}_monthly"
  fi
  if [[ "${dow}" == "7" ]]; then
    ln -sfn "$ts_name" "${backup_root}/${ts_name}_weekly"
  fi
}

hellenia_apply_retention() {
  local backup_root="$1"
  local daily_days="${2:-7}"
  local weekly_weeks="${3:-4}"
  local monthly_months="${4:-6}"

  find "${backup_root}" -maxdepth 1 -type d -name '20*' \
    ! -name '*_weekly' ! -name '*_monthly' -mtime +"${daily_days}" \
    -exec rm -rf {} + 2>/dev/null || true

  # ls sin coincidencias devuelve exit 2 — usar nullglob (no fallar con set -e)
  local -a weekly_links monthly_links
  shopt -s nullglob
  weekly_links=("${backup_root}"/20*_weekly)
  monthly_links=("${backup_root}"/20*_monthly)
  shopt -u nullglob

  if ((${#weekly_links[@]} > weekly_weeks)); then
    printf '%s\n' "${weekly_links[@]}" | sort -r | tail -n +$((weekly_weeks + 1)) | xargs -r rm -rf
  fi
  if ((${#monthly_links[@]} > monthly_months)); then
    printf '%s\n' "${monthly_links[@]}" | sort -r | tail -n +$((monthly_months + 1)) | xargs -r rm -rf
  fi
}

# Sincroniza artefactos versionados desde repository/ hacia PROJECT_ROOT
hellenia_sync_from_repo() {
  local repo="$1"
  local root="$2"
  rsync -av --delete "${repo}/custom/" "${root}/custom/"
  rsync -av "${repo}/docker/" "${root}/docker/"
  rsync -av --exclude='.env' --exclude='credentials/' "${repo}/config/" "${root}/config/"
  rsync -av "${repo}/scripts/" "${root}/scripts/"
  rsync -av "${repo}/data/" "${root}/data/" 2>/dev/null || true
  chmod +x "${root}/scripts/"*.sh 2>/dev/null || true
}

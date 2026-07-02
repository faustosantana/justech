#!/usr/bin/env bash
# Construye imagen hellenia-odoo:19-enterprise (Enterprise + custom horneados)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="${HELLENIA_ODOO_IMAGE:-hellenia-odoo:19-enterprise}"
BASE_IMAGE="${BASE_IMAGE:-odoo:19.0-20260619}"
DOCKERFILE="$PROJECT_ROOT/docker/dev/Dockerfile.enterprise"
LOG_FILE="$PROJECT_ROOT/logs/deploy/build-hellenia-odoo-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$LOG_FILE")"

[[ -f "$PROJECT_ROOT/enterprise/addons/web_enterprise/__manifest__.py" ]] || {
  hellenia_log "ERROR: ejecutar prepare-enterprise-addons.sh primero"
  exit 1
}

hellenia_log "Build $IMAGE_NAME desde $BASE_IMAGE" | tee -a "$LOG_FILE"

docker build \
  --build-arg BASE_IMAGE="$BASE_IMAGE" \
  -f "$DOCKERFILE" \
  -t "$IMAGE_NAME" \
  "$PROJECT_ROOT" 2>&1 | tee -a "$LOG_FILE"

docker run --rm "$IMAGE_NAME" test -f /opt/odoo/enterprise/addons/web_enterprise/__manifest__.py
docker run --rm "$IMAGE_NAME" test -d /opt/odoo/custom

hellenia_log "OK  imagen $IMAGE_NAME lista" | tee -a "$LOG_FILE"

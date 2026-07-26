#!/usr/bin/env bash
# Selective Lottery IA bake over j10x — does NOT replace whole app (keeps Hermes).
# Usage on production host after: git fetch origin tag <TAG>
set -euo pipefail

TAG="${1:-lottery-ia-ux-v1.1}"
BASE_IMAGE="${BASE_IMAGE:-jaios-app-backend:j10x-20260724}"
APP_ROOT="${APP_ROOT:-/opt/jaios-app}"
BAKE_ROOT="${BAKE_ROOT:-/var/jaios/lottery-bake/${TAG}-$(date -u +%Y%m%d)}"
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.harden.yml)

mkdir -p "$BAKE_ROOT/logs" "$BAKE_ROOT/overlay" "$BAKE_ROOT/selective"
cd "$APP_ROOT"
git fetch origin "tag" "$TAG" 2>/dev/null || git fetch origin "refs/tags/$TAG:refs/tags/$TAG"
git archive "$TAG" | tar -x -C "$BAKE_ROOT/overlay"

# Start from currently running j10x config, then inject ALL lottery_* fields from release config.
docker run --rm "$BASE_IMAGE" cat /app/app/config.py > "$BAKE_ROOT/selective/config.base.py"
python3 - <<PY
from pathlib import Path
import re
base = Path("$BAKE_ROOT/selective/config.base.py").read_text()
feat = Path("$BAKE_ROOT/overlay/backend/app/config.py").read_text()
# Extract lottery_* field lines from feature Settings class body
feat_lines = []
in_settings = False
for line in feat.splitlines():
    if line.startswith("class Settings"):
        in_settings = True
        continue
    if in_settings and line.startswith("class "):
        break
    if in_settings and re.match(r"\s+lottery_[a-z0-9_]+:", line):
        feat_lines.append(line.rstrip())
# Remove existing lottery_ fields from base
out = []
skip_block = False
for line in base.splitlines():
    if re.match(r"\s+lottery_[a-z0-9_]+:", line):
        continue
    out.append(line)
text = "\n".join(out)
needle = "    # Resultados de Loterías"
insert = "    # Resultados de Loterías / Lotería IA (merged from release)\n" + "\n".join(feat_lines) + "\n"
if needle in text:
    # drop old comment if present then insert
    text = re.sub(r"\n\s*# Resultados de Loterías[^\n]*\n(?:\s+lottery_[^\n]*\n)*", "\n", text)
    # insert before first non-lottery settings after hermes section — append before model_config if needed
    if "lottery_module_enabled" not in text:
        # place before end of class: look for model_config
        if "    model_config" in text:
            text = text.replace("    model_config", insert + "\n    model_config", 1)
        else:
            text = text.rstrip() + "\n" + insert + "\n"
Path("$BAKE_ROOT/selective/config.py").write_text(text)
print("config lottery fields:", len(feat_lines))
PY

# Patch router from live j10x image
docker run --rm "$BASE_IMAGE" cat /app/app/api/v1/router.py > "$BAKE_ROOT/selective/router.j10x.py"
python3 - <<'PY'
from pathlib import Path
import os
bake = os.environ.get("BAKE_ROOT") or "/tmp"
# path set below via rewrite
PY
BAKE_ROOT="$BAKE_ROOT" python3 - <<PY
from pathlib import Path
src = Path("$BAKE_ROOT/selective/router.j10x.py").read_text()
old_imp = """    lottery_ai_admin,
    lottery_numeric_relations,
    lottery_nr_historical,
    lottery_predictions,"""
new_imp = """    lottery_ai_admin,
    lottery_complete_analysis,
    lottery_numeric_relations,
    lottery_nr_historical,
    lottery_predictions,
    lottery_resultados,
    lottery_ia,"""
if "lottery_ia" not in src:
    if old_imp not in src:
        raise SystemExit("router import block not found")
    src = src.replace(old_imp, new_imp, 1)
old_inc = """api_router.include_router(lottery_ai_admin.router)
api_router.include_router(lottery_numeric_relations.router)
api_router.include_router(lottery_nr_historical.router)
api_router.include_router(lottery_predictions.router)"""
new_inc = """api_router.include_router(lottery_ai_admin.router)
api_router.include_router(lottery_numeric_relations.router)
api_router.include_router(lottery_nr_historical.router)
api_router.include_router(lottery_predictions.router)
api_router.include_router(lottery_resultados.router)
api_router.include_router(lottery_ia.router)
api_router.include_router(lottery_complete_analysis.router)"""
if "lottery_ia.router" not in src:
    if old_inc not in src:
        raise SystemExit("router include block not found")
    src = src.replace(old_inc, new_inc, 1)
Path("$BAKE_ROOT/selective/router.py").write_text(src)
print("router ok")
PY

cat > "$BAKE_ROOT/Dockerfile.backend.selective" <<EOF
FROM ${BASE_IMAGE}
USER root
COPY overlay/backend/app/lottery /app/app/lottery
COPY overlay/backend/app/api/v1/lottery.py /app/app/api/v1/lottery.py
COPY overlay/backend/app/api/v1/lottery_ai_admin.py /app/app/api/v1/lottery_ai_admin.py
COPY overlay/backend/app/api/v1/lottery_complete_analysis.py /app/app/api/v1/lottery_complete_analysis.py
COPY overlay/backend/app/api/v1/lottery_ia.py /app/app/api/v1/lottery_ia.py
COPY overlay/backend/app/api/v1/lottery_nr_historical.py /app/app/api/v1/lottery_nr_historical.py
COPY overlay/backend/app/api/v1/lottery_numeric_relations.py /app/app/api/v1/lottery_numeric_relations.py
COPY overlay/backend/app/api/v1/lottery_predictions.py /app/app/api/v1/lottery_predictions.py
COPY overlay/backend/app/api/v1/lottery_resultados.py /app/app/api/v1/lottery_resultados.py
COPY selective/router.py /app/app/api/v1/router.py
COPY selective/config.py /app/app/config.py
COPY overlay/backend/app/services/lottery_result_service.py /app/app/services/lottery_result_service.py
COPY overlay/backend/app/services/lottery_admin_service.py /app/app/services/lottery_admin_service.py
COPY overlay/backend/app/services/lottery_ai_admin_service.py /app/app/services/lottery_ai_admin_service.py
COPY overlay/backend/app/services/lottery_ai_alert_detector.py /app/app/services/lottery_ai_alert_detector.py
COPY overlay/backend/app/services/lottery_prediction_service.py /app/app/services/lottery_prediction_service.py
COPY overlay/backend/app/services/lottery_sync_gate_backup.py /app/app/services/lottery_sync_gate_backup.py
COPY overlay/backend/app/schemas/lottery_admin.py /app/app/schemas/lottery_admin.py
COPY overlay/backend/app/schemas/lottery_product.py /app/app/schemas/lottery_product.py
COPY overlay/backend/app/services/lottery_product_service.py /app/app/services/lottery_product_service.py
COPY overlay/backend/app/models/lottery_prospective.py /app/app/models/lottery_prospective.py
COPY overlay/backend/alembic/versions/062_lottery_prospective_pilot.py /app/alembic/versions/062_lottery_prospective_pilot.py
COPY overlay/artifacts/tiebreak /app/artifacts/tiebreak
COPY overlay/artifacts/motor_freeze /app/artifacts/motor_freeze
RUN python -c "from app.main import app; from app.config import get_settings; s=get_settings(); assert hasattr(s,'lottery_nr_rate_limit_per_minute'); from app.lottery.numeric_relations.analysis_engine import run_complete_analysis; r=run_complete_analysis({'numbers':[35,14],'mode':'socio','derivation_depth':0,'create_signals':False}, persist=False); assert r.primary_signal['number']==54; r2=run_complete_analysis({'numbers':[39,58],'mode':'socio','derivation_depth':0,'create_signals':False}, persist=False); assert r2.primary_signal['number']==94; print('selective-ok', s.lottery_nr_rate_limit_per_minute)"
EOF

cd "$BAKE_ROOT"
docker build -f Dockerfile.backend.selective \
  -t "jaios-app-backend:${TAG}" \
  -t jaios-app-backend:lottery-ia-motor-v1.0 \
  . 2>&1 | tee logs/backend_selective_build.log

cd "$BAKE_ROOT/overlay/frontend"
docker build -f Dockerfile --target production \
  --build-arg NEXT_PUBLIC_API_URL=https://jaios.justech.do/api/v1 \
  --build-arg NEXT_PUBLIC_APP_NAME=JAIOS \
  --build-arg INTERNAL_API_URL=http://backend:8000 \
  -t "jaios-app-frontend:${TAG}" \
  -t jaios-app-frontend:lottery-ia-motor-v1.0 \
  . 2>&1 | tee "$BAKE_ROOT/logs/frontend_build.log"

cd "$APP_ROOT"
# Rewrite harden overlay atomically (avoid duplicate YAML keys from prior runs).
cat > docker-compose.harden.yml <<EOF
services:
  backend:
    image: jaios-app-backend:${TAG}
    volumes:
      - /var/jaios/backups/lottery-sync-gates:/var/jaios/backups/lottery-sync-gates
    environment:
      LOTTERY_SYNC_WORKER_STANDALONE: "true"
      LOTTERY_SYNC_GATE_BACKUP_DIR: /var/jaios/backups/lottery-sync-gates
      LOTTERY_SYNC_GATE_BACKUP_AUTO_REFRESH: "true"
      LOTTERY_PROSPECTIVE_PERSIST_ENABLED: "false"
      LOTTERY_PROSPECTIVE_SCHEDULER_ENABLED: "false"
  frontend:
    image: jaios-app-frontend:${TAG}
    environment:
      PORT: "3000"
      HOSTNAME: "0.0.0.0"
  lottery-sync-worker:
    image: jaios-app-backend:${TAG}
EOF
docker compose "${COMPOSE_FILES[@]}" config >/dev/null
echo "compose harden retargeted to ${TAG}"

docker compose "${COMPOSE_FILES[@]}" up -d backend frontend lottery-sync-worker
docker compose "${COMPOSE_FILES[@]}" restart gateway
echo "$TAG" > "$BAKE_ROOT/RUNTIME_GIT_TAG.txt"
git rev-parse "$TAG^{}" > "$BAKE_ROOT/RUNTIME_GIT_COMMIT.txt" || true
echo "Deployed selective $TAG"

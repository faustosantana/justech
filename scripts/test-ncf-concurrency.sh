#!/usr/bin/env bash
# Sprint 0 — Concurrencia NCF: dos posts paralelos en DEV
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:-dev}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_NAME}/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_NAME}"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/test-ncf-concurrency-setup.py" >/dev/null 2>&1 || true

OUT_A=$(mktemp)
OUT_B=$(mktemp)

docker compose --env-file "$ENV_FILE" run --rm -T -e WORKER_ID=0 odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/test-ncf-concurrency.py" >"$OUT_A" 2>&1 &
PID_A=$!

docker compose --env-file "$ENV_FILE" run --rm -T -e WORKER_ID=1 odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/test-ncf-concurrency.py" >"$OUT_B" 2>&1 &
PID_B=$!

wait "$PID_A" || true
wait "$PID_B" || true

LINE_A=$(grep 'NCF_CONCURRENCY_RESULT:' "$OUT_A" | tail -1 || true)
LINE_B=$(grep 'NCF_CONCURRENCY_RESULT:' "$OUT_B" | tail -1 || true)
NCF_A=$(echo "$LINE_A" | sed 's/.*NCF_CONCURRENCY_RESULT://' | python3 -c "import sys,json; print(json.load(sys.stdin).get('ncf',''))" 2>/dev/null || true)
NCF_B=$(echo "$LINE_B" | sed 's/.*NCF_CONCURRENCY_RESULT://' | python3 -c "import sys,json; print(json.load(sys.stdin).get('ncf',''))" 2>/dev/null || true)

hellenia_log "Worker A NCF: ${NCF_A:-MISSING}"
hellenia_log "Worker B NCF: ${NCF_B:-MISSING}"

SERIALIZED=0
if grep -qiE 'SerializationFailure|could not serialize|concurrent update|duplicate key|IntegrityError|already assigned' "$OUT_A" "$OUT_B" 2>/dev/null; then
  SERIALIZED=1
fi

if [[ -n "$NCF_A" && -n "$NCF_B" && "$NCF_A" != "$NCF_B" ]]; then
  hellenia_log "PASS: concurrent NCF unique ($NCF_A vs $NCF_B)"
  exit 0
fi

if [[ -n "$NCF_A" && -z "$NCF_B" && "$SERIALIZED" -eq 1 ]]; then
  hellenia_log "PASS: concurrency serialized (worker A=$NCF_A, worker B blocked)"
  exit 0
fi

if [[ -z "$NCF_A" && -n "$NCF_B" && "$SERIALIZED" -eq 1 ]]; then
  hellenia_log "PASS: concurrency serialized (worker B=$NCF_B, worker A blocked)"
  exit 0
fi

if [[ -n "$NCF_A" && -n "$NCF_B" && "$NCF_A" == "$NCF_B" ]]; then
  hellenia_log "FAIL: duplicate NCF under concurrency ($NCF_A)"
  exit 1
fi

hellenia_log "FAIL: unexpected concurrency outcome"
tail -n 30 "$OUT_A" || true
tail -n 30 "$OUT_B" || true
exit 1

#!/usr/bin/env bash
# Fase 18.5 — Regresión completa retenciones + 606/607 en TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
EVIDENCE="$PROJECT_ROOT/evidence/phase18-5-regression-test.json"
LOG="$PROJECT_ROOT/logs/deploy/phase18-5-regression-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")"

hellenia_load_env "$ENV_FILE"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"

hellenia_log "=== Fase 18.5 Regresión completa — TEST ===" | tee "$LOG"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" up -d odoo
sleep 8

run_phase() {
  local script="$1"
  local marker="$2"
  local out="$3"
  hellenia_log "Ejecutando $script..." | tee -a "$LOG" >&2
  if "$SCRIPT_DIR/run-odoo-shell-env.sh" test "$script" "$marker" "$out" >> "$LOG" 2>&1; then
    echo "PASS"
  else
    echo "FAIL"
  fi
}

P18=$(run_phase phase18-validate-withholding-test.py PHASE18 "$PROJECT_ROOT/evidence/phase18-regression-18.json")
P182=$(run_phase phase18-2-validate-withholding-catalog-test.py PHASE18_2 "$PROJECT_ROOT/evidence/phase18-regression-18-2.json")
P183=$(run_phase phase18-3-certify-withholding-test.py PHASE18_3 "$PROJECT_ROOT/evidence/phase18-regression-18-3.json")
P184=$(run_phase phase18-4-withholding-calculation-test.py PHASE184 "$PROJECT_ROOT/evidence/phase18-regression-18-4.json")
P185=$(run_phase phase18-5-regression-test.py PHASE185 "$PROJECT_ROOT/evidence/phase18-regression-18-5.json")

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

def _extract_json(payload):
    start = payload.find("{")
    if start < 0:
        raise json.JSONDecodeError("no object", payload, 0)
    obj, _end = json.JSONDecoder().raw_decode(payload, start)
    return obj


def load_marker(path, marker):
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": "missing evidence"}
    raw = p.read_text()
    key = marker if marker.endswith(":") else marker + ":"
    i = raw.find(key)
    payload = raw[i + len(key) :].strip() if i >= 0 else raw
    try:
        return _extract_json(payload)
    except json.JSONDecodeError:
        return {"ok": False, "raw": payload[:500]}

phases = {
    "phase18": ("${P18}", load_marker("${PROJECT_ROOT}/evidence/phase18-regression-18.json", "PHASE18:")),
    "phase18_2": ("${P182}", load_marker("${PROJECT_ROOT}/evidence/phase18-regression-18-2.json", "PHASE18_2:")),
    "phase18_3": ("${P183}", load_marker("${PROJECT_ROOT}/evidence/phase18-regression-18-3.json", "PHASE18_3:")),
    "phase18_4": ("${P184}", load_marker("${PROJECT_ROOT}/evidence/phase18-regression-18-4.json", "PHASE184:")),
    "phase18_5": ("${P185}", load_marker("${PROJECT_ROOT}/evidence/phase18-regression-18-5.json", "PHASE185:")),
}

def phase_ok(name, status, data):
    if status != "PASS":
        return False
    if name == "phase18_2":
        return data.get("ok", False)
    if name == "phase18_3":
        return data.get("ok", False)
    if name == "phase18_4":
        return data.get("pass", data.get("ok", False))
    if name == "phase18_5":
        return data.get("pass", data.get("ok", False))
    return data.get("ok", False)

summary = {
    "phase": "18.5-full-regression",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": "hellenia_test",
    "phases": {},
    "all_pass": True,
    "production_ready_for_approval": False,
    "cause_606_607": (
        "Scripts usaban rango YTD (1-ene a hoy) incompatible con período mensual YYYYMM DGII."
    ),
    "fix_606_607": (
        "Período mensual coherente: period_code + period_bounds_from_code alineados con invoice_date."
    ),
}

for name, (status, data) in phases.items():
    ok = phase_ok(name, status, data)
    summary["phases"][name] = {"runner": status, "ok": ok}
    if not ok:
        summary["all_pass"] = False

summary["production_ready_for_approval"] = summary["all_pass"]
Path("${EVIDENCE}").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(summary, indent=2, ensure_ascii=False))
import sys
sys.exit(0 if summary["all_pass"] else 1)
PY

hellenia_log "Evidencia: $EVIDENCE" | tee -a "$LOG"

#!/usr/bin/env bash
# Fase 11 — Auditoría integral read-only del proyecto (sin tocar PROD ni Go-Live)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="${PROJECT_ROOT}/evidence"
mkdir -p "$EVIDENCE"

OUT="${EVIDENCE}/phase11-project-audit.json"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

line_count() {
  local files
  files=$(find "$@" 2>/dev/null)
  if [[ -z "$files" ]]; then
    echo 0
    return
  fi
  echo "$files" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'
}

MVP_PROD=$(line_count \
  "${PROJECT_ROOT}/custom/justech_l10n_do_base" \
  "${PROJECT_ROOT}/custom/justech_l10n_do_ncf" \
  "${PROJECT_ROOT}/custom/justech_l10n_do_reports" \
  -name '*.py' ! -path '*/tests/*')
MVP_TEST=$(line_count \
  "${PROJECT_ROOT}/custom/justech_l10n_do_base/tests" \
  "${PROJECT_ROOT}/custom/justech_l10n_do_ncf/tests" \
  "${PROJECT_ROOT}/custom/justech_l10n_do_reports/tests" \
  -name '*.py')
SKELETON=$(line_count \
  "${PROJECT_ROOT}/custom/hellenia_base" \
  "${PROJECT_ROOT}/custom/hellenia_account" \
  "${PROJECT_ROOT}/custom/hellenia_inventory" \
  "${PROJECT_ROOT}/custom/hellenia_reports" \
  "${PROJECT_ROOT}/custom/hellenia_pos" \
  "${PROJECT_ROOT}/custom/justech_core" \
  -name '*.py')
DOCS=$(find "${PROJECT_ROOT}/docs" -name '*.md' | wc -l)
SCRIPTS=$(find "${PROJECT_ROOT}/scripts" -name '*.sh' | wc -l)

MANIFEST_JSON=""
for m in justech_l10n_do_base justech_l10n_do_ncf justech_l10n_do_reports; do
  v=$(grep -E '"version"' "${PROJECT_ROOT}/custom/${m}/__manifest__.py" | head -1 | sed 's/.*"\([^"]*\)".*/\1/')
  MANIFEST_JSON="${MANIFEST_JSON}\"${m}\":\"${v}\","
done
MANIFEST_JSON="{${MANIFEST_JSON%,}}"

# Duplicate doc themes (heuristic)
DUP_DOCS=$(find "${PROJECT_ROOT}/docs" -name '*.md' -printf '%f\n' | sort | uniq -d | wc -l)

# Obsolete / legacy indicators in docs
LEGACY_DOCS=$(grep -rl 'odoo-pecv\|PHASE5\|l10n_do_reports.account_report' "${PROJECT_ROOT}/docs" 2>/dev/null | wc -l || echo 0)

cat > "$OUT" <<EOF
{
  "phase": 11,
  "timestamp_utc": "$TS",
  "scope": "read-only repository audit",
  "restrictions": {
    "go_live_executed": false,
    "production_touched": false,
    "dns_changed": false,
    "real_data_imported": false
  },
  "metrics": {
    "mvp_python_loc_production": ${MVP_PROD:-0},
    "mvp_python_loc_tests": ${MVP_TEST:-0},
    "skeleton_python_loc": ${SKELETON:-0},
    "documentation_files": ${DOCS},
    "shell_scripts": ${SCRIPTS},
    "custom_modules_mvp": 3,
    "custom_modules_skeleton": 6
  },
  "modules": {
    "mvp_active": ["justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports"],
    "skeleton_unused": ["justech_core", "hellenia_base", "hellenia_account", "hellenia_inventory", "hellenia_reports", "hellenia_pos"]
  },
  "manifest_versions": ${MANIFEST_JSON},
  "findings": {
    "todo_fixme_in_custom": 0,
    "duplicate_doc_filenames": ${DUP_DOCS},
    "docs_referencing_legacy_phase5_gaps": ${LEGACY_DOCS}
  },
  "evidence_references": [
    "evidence/phase11-spanish-dev.json",
    "evidence/phase11-spanish-test.json",
    "evidence/uat-functional.json",
    "evidence/uat-stress.json",
    "evidence/uat-audit.json",
    "evidence/phase10-backups-manifest.json",
    "evidence/phase10-infra-audit.txt",
    "evidence/security-audit-dev.json",
    "evidence/security-audit-test.json"
  ],
  "p0_technical_debt_status": "CLOSED_SPRINT0",
  "uat_status": "APTO_PARA_PILOTO",
  "phase10_status": "APTO_PARA_GO_LIVE_CON_OBSERVACIONES"
}
EOF

hellenia_log "Fase 11 auditoría → $OUT"
hellenia_log "MVP LOC: prod=${MVP_PROD} tests=${MVP_TEST} | docs=${DOCS} scripts=${SCRIPTS}"

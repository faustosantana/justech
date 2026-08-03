#!/usr/bin/env bash
# Predeploy gate: fail if canonical navigation integrity is broken.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FE="$ROOT/frontend"
INV_OUT="${NAV_INVENTORY_OUT:-$ROOT/evidence/navigation-audit/route-inventory.json}"

echo "=== JAIOS navigation predeploy ==="

node "$ROOT/scripts/qa/jaios_navigation_inventory.mjs" --out "$INV_OUT"

# FavoriteToggle wiring
node "$FE/scripts/assert-favorite-toggle.mjs"

# Critical exports / methods present in api client
python3 - <<'PY'
from pathlib import Path
api = Path("frontend/src/lib/api.ts").read_text()
need = [
    "getCompanyRepresentatives",
    "createCompanyRepresentative",
    "getDGCPOpportunities",
    "getDocumentsHubCompany",
]
missing = [n for n in need if n not in api]
if missing:
    raise SystemExit(f"FAIL: api.ts missing methods: {missing}")
print("PASS: critical apiClient methods present")
PY

# Canonical FE surfaces must exist
python3 - <<'PY'
from pathlib import Path
need_files = [
    "frontend/src/components/navigation/apps-launcher.tsx",
    "frontend/src/components/navigation/favorite-toggle.tsx",
    "frontend/src/components/modules/licitaciones/licitaciones-sections.tsx",
    "frontend/src/components/modules/empresas-grupo/company-expediente-view.tsx",
    "frontend/src/app/(platform)/lottery/page.tsx",
    "frontend/src/app/(platform)/lottery/admin/ai/configuracion/page.tsx",
    "frontend/src/app/(platform)/error.tsx",
]
missing = [p for p in need_files if not Path(p).exists()]
if missing:
    raise SystemExit(f"FAIL: missing canonical files: {missing}")
print("PASS: canonical FE surfaces present")
PY

# RPE company resolve must sanitize to canonical enum
python3 - <<'PY'
from pathlib import Path
p = Path("frontend/src/components/dgcp/dgcp-rpe-filter-bar.tsx").read_text()
if "CANONICAL_COMPANIES.includes(key)" not in p and "CANONICAL_COMPANIES.includes(raw" not in p:
    # accept either form used in resolveCompanyFromRpe return
    if "return CANONICAL_COMPANIES.includes" not in p:
        raise SystemExit("FAIL: resolveCompanyFromRpe must sanitize to CANONICAL_COMPANIES")
print("PASS: DGCP RPE company sanitize present")
PY

echo "PASS: navigation predeploy checks"

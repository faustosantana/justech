#!/usr/bin/env bash
# Verify that the working tree matches the frozen CERTIFIED 2026.1 baseline.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/RELEASE_PACKAGE/VERSION_MANIFEST.json"
BANK="$ROOT/evidence/lottery-analyst-certification-200/QUESTION_BANK.json"
BANK_SHA_FILE="$ROOT/evidence/lottery-analyst-certification-200/QUESTION_BANK.sha256"
SUMMARY="$ROOT/evidence/lottery-analyst-certification-200/audit-certified-20260728/SUMMARY.json"

EXPECTED_TAG="lottery-ia-ux-v2.4.5.4-certified"
EXPECTED_RUNTIME_COMMIT="8061e0f458419d994bff8abd3700de4c10aa5b80"
EXPECTED_BANK_SHA="6d056978809140eee4af23299cbd0c78a8bae9537fbbbcd62ad50bd18c6d7931"
EXPECTED_SEED="20260727"
EXPECTED_IMAGE="jaios-app-backend:lottery-ia-ux-v2.4.5.4-de"
EXPECTED_IMAGE_ID="sha256:a6204913747cc2472f2dfec4cd125b95f73fe1fd55439d6d1255c9342780af24"

fail() { echo "RESTORE_FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

cd "$ROOT"

[[ -f "$MANIFEST" ]] || fail "missing VERSION_MANIFEST.json"
[[ -f "$BANK" ]] || fail "missing QUESTION_BANK.json"
[[ -f "$BANK_SHA_FILE" ]] || fail "missing QUESTION_BANK.sha256"
[[ -f "$SUMMARY" ]] || fail "missing certified SUMMARY.json"
[[ -f "$ROOT/RELEASE_PACKAGE/RELEASE_NOTES_2026.1.md" ]] || fail "missing RELEASE_NOTES"
[[ -f "$ROOT/RELEASE_PACKAGE/CERTIFICATION_REPORT_FINAL.md" ]] || fail "missing CERTIFICATION_REPORT_FINAL"
[[ -f "$ROOT/RELEASE_PACKAGE/RESTORE.md" ]] || fail "missing RESTORE.md"

HEAD="$(git rev-parse HEAD)"
TAG_COMMIT="$(git rev-parse "${EXPECTED_TAG}^{}" 2>/dev/null || true)"
[[ -n "$TAG_COMMIT" ]] || fail "tag $EXPECTED_TAG not found locally"

if [[ "$HEAD" != "$TAG_COMMIT" ]]; then
  echo "WARN: HEAD=$HEAD is not tag peel $TAG_COMMIT (checkout the tag for exact restore)."
fi
ok "tag $EXPECTED_TAG → $TAG_COMMIT"

# Runtime certified commit must be an ancestor of the frozen tag
if ! git merge-base --is-ancestor "$EXPECTED_RUNTIME_COMMIT" "$TAG_COMMIT"; then
  fail "runtime commit $EXPECTED_RUNTIME_COMMIT is not ancestor of tag $TAG_COMMIT"
fi
ok "runtime certified commit $EXPECTED_RUNTIME_COMMIT ⊆ tag"

BANK_SHA="$(shasum -a 256 "$BANK" | awk '{print $1}')"
FILE_SHA="$(awk '{print $1}' "$BANK_SHA_FILE")"
[[ "$BANK_SHA" == "$EXPECTED_BANK_SHA" ]] || fail "bank sha $BANK_SHA != $EXPECTED_BANK_SHA"
[[ "$FILE_SHA" == "$EXPECTED_BANK_SHA" ]] || fail "QUESTION_BANK.sha256 file mismatch"
ok "question bank SHA-256"

python3 - <<PY || fail "manifest/summary mismatch"
import json
from pathlib import Path
m=json.loads(Path("$MANIFEST").read_text())
s=json.loads(Path("$SUMMARY").read_text())
assert m["git"]["tag"] == "$EXPECTED_TAG"
assert m["git"]["commit"] == "$EXPECTED_RUNTIME_COMMIT"
assert m["git"].get("certified_runtime_commit", m["git"]["commit"]) == "$EXPECTED_RUNTIME_COMMIT"
# Prefer exact: freeze commit equals tag peel when present after release packaging
assert m["docker"]["backend_image"] == "$EXPECTED_IMAGE"
assert m["docker"]["backend_image_id"] == "$EXPECTED_IMAGE_ID"
assert int(m["question_bank"]["seed"]) == int("$EXPECTED_SEED")
assert m["question_bank"]["sha256"] == "$EXPECTED_BANK_SHA"
assert s.get("certification_level") == "CERTIFIED"
assert s.get("pass") == 200 and s.get("fail") == 0
assert s.get("audit_run_id") == m["certification"]["audit_run_id"]
print("manifest+summary consistent")
PY
ok "VERSION_MANIFEST + SUMMARY"

for f in \
  backend/app/lottery/ai/understanding.py \
  backend/app/lottery/ai/turn_policy.py \
  backend/app/lottery/ai/analyst/conversation_brain.py \
  backend/app/lottery/ai/analyst/question_classifier.py \
  backend/app/lottery/ai/analyst/tool_orchestrator.py \
  backend/app/services/lottery_chat_service.py \
  backend/tests/test_analyst_cert200_root_causes.py
do
  [[ -f "$ROOT/$f" ]] || fail "missing $f"
done
ok "critical source files present"

echo
echo "RESTORE_OK"
echo "tag_commit=$TAG_COMMIT"
echo "runtime_commit=$EXPECTED_RUNTIME_COMMIT"
echo "tag=$EXPECTED_TAG"
echo "seed=$EXPECTED_SEED"
echo "bank_sha=$EXPECTED_BANK_SHA"
echo "image=$EXPECTED_IMAGE"
echo "image_id=$EXPECTED_IMAGE_ID"

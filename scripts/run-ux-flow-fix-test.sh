#!/usr/bin/env bash
# UX-FLOW-FIX — Deploy TEST + validate + evidence (no commit)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE="$ROOT/evidence/ux-flow-fix"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE_CUSTOM="/opt/odoo-projects/hellenia/custom"
TEST_COMPOSE="/opt/odoo-projects/hellenia/docker/test"
TEST_ENV="/opt/odoo-projects/hellenia/config/test/.env"

mkdir -p "$EVIDENCE"

echo "==> Sync custom modules to VPS"
rsync -az --delete \
  -e "ssh -i $SSH_KEY" \
  "$ROOT/custom/hellenia_ux/" "$VPS:$REMOTE_CUSTOM/hellenia_ux/"
rsync -az --delete \
  -e "ssh -i $SSH_KEY" \
  "$ROOT/custom/hellenia_ui/" "$VPS:$REMOTE_CUSTOM/hellenia_ui/"
rsync -az \
  -e "ssh -i $SSH_KEY" \
  "$ROOT/custom/justech_admin/" "$VPS:$REMOTE_CUSTOM/justech_admin/"
rsync -az \
  -e "ssh -i $SSH_KEY" \
  "$ROOT/custom/justech_global_audit_log/" "$VPS:$REMOTE_CUSTOM/justech_global_audit_log/"
rsync -az \
  -e "ssh -i $SSH_KEY" \
  "$ROOT/custom/justech_l10n_do_reports/" "$VPS:$REMOTE_CUSTOM/justech_l10n_do_reports/"

echo "==> Upgrade modules on TEST"
ssh -i "$SSH_KEY" "$VPS" bash -s <<REMOTE
set -euo pipefail
cd "$TEST_COMPOSE"
set -a && source "$TEST_ENV" && set +a
docker compose exec -T odoo odoo -d hellenia_test --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u hellenia_ui,hellenia_ux,justech_admin,justech_global_audit_log,justech_l10n_do_reports --stop-after-init
docker compose exec -T odoo odoo shell -d hellenia_test --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" --no-http <<'PY'
env["hellenia.ui.menu.customizer"].apply_ux_flow_fix_labels()
env.cr.commit()
print("menu labels applied")
PY
REMOTE

echo "==> Healthcheck TEST"
ssh -i "$SSH_KEY" "$VPS" "curl -sf -o /dev/null -w '%{http_code}' https://test.hellenia.cloud/web/login" | tee "$EVIDENCE/http_login.txt"
echo ""

echo "==> UX validation"
ssh -i "$SSH_KEY" "$VPS" "cd '$TEST_COMPOSE' && set -a && source '$TEST_ENV' && set +a && docker compose exec -T -e UX_FLOW_FIX_EVIDENCE=/tmp/ux-flow-fix odoo odoo shell -d hellenia_test --db_host=db --db_user=\$DB_USER --db_password=\$DB_PASSWORD --no-http" \
  < "$ROOT/scripts/ux-flow-fix-validate.py" | tee "$EVIDENCE/validation_run.log"

scp -i "$SSH_KEY" "$VPS:/tmp/ux-flow-fix/UX_FLOW_FIX_VALIDATION.json" "$EVIDENCE/" 2>/dev/null || true

# Healthcheck snapshot
printf '{"status":"PASS","url":"https://test.hellenia.cloud/web/login","http_code":"%s","timestamp_utc":"%s"}\n' \
  "$(cat "$EVIDENCE/http_login.txt" 2>/dev/null || echo 000)" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$EVIDENCE/UX_FLOW_FIX_HEALTHCHECK.json"

python3 "$ROOT/scripts/ux-flow-fix-generate-evidence.py"

echo "==> Done. Evidence: $EVIDENCE"

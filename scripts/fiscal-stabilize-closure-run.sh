#!/usr/bin/env bash
# Cierre estabilización fiscal — erp.justech.do / justech_dev (sin merge)
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
REPO="/Users/faustosantana/Projects/jaios"
EV="$REPO/evidence/fiscal-stabilize"
REMOTE_SCRIPTS="/opt/odoo-dev/scripts"
SSH="jaios-vps"

mkdir -p "$EV"

echo "==> Sync scripts"
for s in fiscal-audit-menu-hierarchy.py fiscal-payment-inspect.py fiscal-stabilize-cleanup-payment.py fiscal-stabilize-post-validate.py fiscal-stabilize-session.py; do
  scp -q "$REPO/scripts/$s" "$SSH:$REMOTE_SCRIPTS/$s"
  ssh "$SSH" "chmod +x $REMOTE_SCRIPTS/$s"
done

echo "==> Menu hierarchy diagnostic"
ssh "$SSH" "sudo -u odoo /usr/bin/odoo shell -c $CONF -d $DB --no-http < $REMOTE_SCRIPTS/fiscal-audit-menu-hierarchy.py" | tee "$EV/menu_hierarchy.json"

echo "==> Payment inspect (pre-cleanup)"
ssh "$SSH" "sudo -u odoo /usr/bin/odoo shell -c $CONF -d $DB --no-http < $REMOTE_SCRIPTS/fiscal-payment-inspect.py" | tee "$EV/payment_inspect_pre.json"

echo "==> Cleanup test payment"
ssh "$SSH" "sudo -u odoo /usr/bin/odoo shell -c $CONF -d $DB --no-http < $REMOTE_SCRIPTS/fiscal-stabilize-cleanup-payment.py" | tee "$EV/cleanup_payment.json"

echo "==> Post-validate backend"
ssh "$SSH" "sudo -u odoo /usr/bin/odoo shell -c $CONF -d $DB --no-http < $REMOTE_SCRIPTS/fiscal-stabilize-post-validate.py" | tee "$EV/post_validate.json"

echo "==> Session for visual validation"
ssh "$SSH" "sudo -u odoo /usr/bin/odoo shell -c $CONF -d $DB --no-http < $REMOTE_SCRIPTS/fiscal-stabilize-session.py" > /tmp/fiscal_stabilize_session.json

echo "==> Visual validation (Playwright local)"
python3 "$REPO/scripts/fiscal-stabilize-visual-validate.py" | tee "$EV/visual_validation.json"

echo "STABILIZE_CLOSURE_OK"

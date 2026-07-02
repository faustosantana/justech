#!/usr/bin/env bash
# Regenera el paquete de revisión Fase 24.1 (PDFs, PNGs, fuentes, README, ZIP)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/packages/phase24-1-hellenia-quotation-review"
EVID="$ROOT/evidence/phase24-1-report-design"
MOD="$ROOT/custom/justech_report_design"

mkdir -p "$PKG"
cp "$EVID"/quotation_{1,5}_product*.pdf "$EVID"/quotation_25_products.pdf "$EVID"/quotation_5_products_discount.pdf "$PKG/" 2>/dev/null || true
cp "$EVID"/quotation_{1,5}_product*.png "$EVID"/quotation_25_products.png "$EVID"/quotation_5_products_discount.png "$PKG/" 2>/dev/null || true
cp "$EVID"/validation.json "$PKG/"
cp "$ROOT/evidence/phase24-1g-audit/audit.json" "$PKG/" 2>/dev/null || true
cp "$MOD/report/quotation/hellenia_quotation_template.xml" "$PKG/"
cp "$MOD/static/src/scss/hellenia_quotation.scss" "$PKG/"

cd "$ROOT/packages"
zip -qr phase24-1-hellenia-quotation-review.zip phase24-1-hellenia-quotation-review/
echo "Paquete listo: $PKG"
echo "ZIP: $ROOT/packages/phase24-1-hellenia-quotation-review.zip ($(du -h phase24-1-hellenia-quotation-review.zip | cut -f1))"

/**
 * Validación UI Odoo vía API (misma capa que la pantalla /odoo).
 * Ejecutar: node scripts/e2e-odoo-ui.mjs
 * Requiere JAIOS_E2E_TOKENS_JSON con tokens de e2e_auth_token.py
 */
const base = process.env.JAIOS_API_BASE || "http://gateway/api/v1";
import { readFileSync } from "node:fs";

const tokenFile = process.env.JAIOS_E2E_TOKENS_FILE || "/app/.qa/e2e-tokens.json";
const tokens = JSON.parse(
  process.env.JAIOS_E2E_TOKENS_JSON ||
    (() => {
      try {
        return readFileSync(tokenFile, "utf8");
      } catch {
        return "{}";
      }
    })(),
);
const headers = {
  Authorization: `Bearer ${tokens.access_token}`,
  "X-Tenant-Id": tokens.tenant_id || "",
};

const checks = [
  ["customers", "/odoo/customers"],
  ["products", "/odoo/products"],
  ["invoices/open", "/odoo/invoices/open"],
  ["invoices/overdue", "/odoo/invoices/overdue"],
  ["quotations", "/odoo/quotations"],
  ["opportunities", "/odoo/opportunities"],
  ["projects", "/odoo/projects"],
];

async function get(path) {
  const res = await fetch(`${base}${path}`, { headers });
  const body = await res.json().catch(() => ({}));
  return { status: res.status, body };
}

async function main() {
  if (!tokens.access_token) {
    console.error("FAIL: sin tokens E2E");
    process.exit(1);
  }
  const health = await get("/odoo/health");
  if (health.status !== 200 || !health.body.connected) {
    console.error("FAIL: Odoo no conectado", health);
    process.exit(1);
  }
  let ok = 0;
  for (const [name, path] of checks) {
    const { status, body } = await get(path);
    const items = body.items?.length ?? 0;
    const total = body.total ?? 0;
    const pass = status === 200 && body.connected && total > 0 && items > 0;
    console.log(`${pass ? "PASS" : "FAIL"} ${name}: status=${status} total=${total} items=${items}`);
    if (pass) ok += 1;
    else process.exitCode = 1;
  }
  console.log(`UI-DATA-CHECK: ${ok}/${checks.length} tabs con datos reales`);
}

main();

/**
 * Phase F focused Playwright UAT captures (DEV only).
 */
import { createRequire } from "module";
import fs from "fs";
import path from "path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const BASE = process.env.UAT_BASE || "http://host.docker.internal:3011";
const API = process.env.UAT_API || "http://host.docker.internal:8011";
const OUT = "/work/docs/lottery/numeric_relations_artifacts/phase_f/screenshots";
const EMAIL = process.env.UAT_ADMIN_EMAIL || "uat-nr-admin@example.com";
const CLIENT = process.env.UAT_CLIENT_EMAIL || "uat-nr-client@example.com";
const PASS = process.env.UAT_PASSWORD || "";
const TENANT = process.env.UAT_TENANT || "uat-numeric-relations";

if (!PASS) {
  console.error("Set UAT_PASSWORD (and optionally UAT_* emails) before running.");
  process.exit(2);
}

fs.mkdirSync(OUT, { recursive: true });

async function login(email) {
  const res = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: PASS, tenant_slug: TENANT }),
  });
  if (!res.ok) throw new Error(`login ${email} ${res.status} ${await res.text()}`);
  return res.json();
}

async function main() {
  const tokens = await login(EMAIL);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript((t) => {
    localStorage.setItem("jaios_access_token", t.access_token);
    localStorage.setItem("jaios_refresh_token", t.refresh_token);
    if (t.tenant_id) localStorage.setItem("jaios_tenant_id", t.tenant_id);
    if (t.role) localStorage.setItem("jaios_role", t.role);
  }, tokens);

  const page = await context.newPage();
  await page.goto(`${BASE}/lottery/admin/numeric-relations`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForTimeout(2500);
  await page.keyboard.press("Escape").catch(() => {});
  await page.locator('button:has-text("Cerrar asistente")').click({ timeout: 1000 }).catch(() => {});
  await page.locator('button[aria-label="Cerrar asistente"]').click({ timeout: 1000 }).catch(() => {});

  const shot = async (name) => {
    await page.screenshot({ path: path.join(OUT, name), fullPage: true });
    console.log("saved", name);
  };

  await page.getByRole("button", { name: "Tabla 1" }).click();
  await page.waitForTimeout(400);
  await shot("A_tabla1.png");

  await page.getByRole("button", { name: "Tabla 2" }).click();
  await page.waitForTimeout(400);
  await shot("B_tabla2.png");

  await page.getByRole("button", { name: "Agrupaciones T1" }).click();
  await page.waitForTimeout(500);
  await shot("C_groups_t1.png");
  await page.getByText("Código 34", { exact: false }).first().scrollIntoViewIfNeeded().catch(() => {});
  await shot("C_code34_t1.png");

  await page.getByRole("button", { name: "Agrupaciones T2" }).click();
  await page.waitForTimeout(500);
  await shot("C_groups_t2.png");
  await page.getByText("Código 53", { exact: false }).first().scrollIntoViewIfNeeded().catch(() => {});
  await shot("C_code53_t2.png");

  await page.getByRole("button", { name: "Análisis histórico" }).click();
  await page.waitForTimeout(1200);
  await shot("D_form.png");

  // Validation: clear lotteries and run
  await page.getByRole("button", { name: "Ejecutar análisis del motor" }).click();
  await page.waitForTimeout(600);
  await shot("D_validation.png");

  // Selectors 5/10/20/Todas
  for (const label of ["Últimas 5", "Últimas 10", "Últimas 20", "Todas"]) {
    await page.getByRole("button", { name: label }).click();
    await page.waitForTimeout(200);
  }
  await shot("D_selectors.png");

  // Observed + Leidsa
  await page.getByLabel(/Número observado/i).fill("26");
  const leidsa = page.locator("label").filter({ hasText: /Quiniela Leidsa/i }).locator("input");
  if (await leidsa.count()) await leidsa.check();
  await page.getByRole("button", { name: "Últimas 10" }).click();
  await shot("D_case1_ready.png");
  await page.getByRole("button", { name: "Ejecutar análisis del motor" }).click();
  await page.waitForTimeout(3500);
  await shot("E_case1.png");
  await page.getByText(/a1c9bcef|2026-06-23|compañero|Trazabilidad|expand/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.locator("button, summary, details").filter({ hasText: /traz|detalle|expand|ver/i }).first().click({ timeout: 2000 }).catch(() => {});
  await shot("F_case1_trace.png");

  // Case 2
  await page.getByLabel(/Número observado/i).fill("34");
  await page.getByRole("button", { name: "Todas" }).click();
  await page.getByRole("button", { name: "Ejecutar análisis del motor" }).click();
  await page.waitForTimeout(5000);
  await shot("E_case2.png");

  // Case 3
  await page.getByLabel(/Número observado/i).fill("45");
  await page.getByRole("button", { name: "Últimas 20" }).click();
  const loteka = page.locator("label").filter({ hasText: /Quiniela Loteka/i }).locator("input");
  if (await loteka.count()) await loteka.check();
  await page.getByRole("button", { name: "Ejecutar análisis del motor" }).click();
  await page.waitForTimeout(4000);
  await shot("E_case3.png");

  // Case 4
  await page.getByLabel(/Número observado/i).fill("100");
  // uncheck leidsa/loteka, check anguila
  for (const name of [/Quiniela Leidsa/i, /Quiniela Loteka/i]) {
    const box = page.locator("label").filter({ hasText: name }).locator("input");
    if (await box.count()) await box.uncheck().catch(() => {});
  }
  const ang = page.locator("label").filter({ hasText: /Anguila 08:00 AM/i }).locator("input");
  if (await ang.count()) await ang.check();
  await page.getByRole("button", { name: "Últimas 10" }).click();
  await page.getByRole("button", { name: "Ejecutar análisis del motor" }).click();
  await page.waitForTimeout(3000);
  await shot("E_case4.png");

  // Case 5
  await page.getByLabel(/Número observado/i).fill("58");
  if (await ang.count()) await ang.uncheck().catch(() => {});
  if (await loteka.count()) await loteka.check();
  await page.getByRole("button", { name: "Todas" }).click();
  await page.getByRole("button", { name: "Ejecutar análisis del motor" }).click();
  await page.waitForTimeout(5000);
  await shot("E_case5_dups.png");

  // responsive
  await page.setViewportSize({ width: 834, height: 1112 });
  await page.getByRole("button", { name: "Tabla 1" }).click();
  await page.waitForTimeout(400);
  await shot("G_tablet.png");

  // client denied UI
  const ctok = await login(CLIENT);
  const p2 = await browser.newPage();
  await p2.addInitScript((t) => {
    localStorage.setItem("jaios_access_token", t.access_token);
    localStorage.setItem("jaios_refresh_token", t.refresh_token);
    if (t.tenant_id) localStorage.setItem("jaios_tenant_id", t.tenant_id);
    if (t.role) localStorage.setItem("jaios_role", t.role);
  }, ctok);
  await p2.goto(`${BASE}/lottery/admin/numeric-relations`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await p2.waitForTimeout(2500);
  await p2.screenshot({ path: path.join(OUT, "H_client_ui.png"), fullPage: true });
  const denied = await p2.evaluate(async () => {
    const t = localStorage.getItem("jaios_access_token");
    const r = await fetch("/api/v1/lottery/admin/numeric-relations/tables", {
      headers: { Authorization: `Bearer ${t}` },
    });
    return { status: r.status, body: (await r.text()).slice(0, 240) };
  });
  fs.writeFileSync(
    "/work/docs/lottery/numeric_relations_artifacts/phase_f/client_tables_browser.json",
    JSON.stringify(denied, null, 2),
  );
  console.log("client denied", denied);

  await browser.close();
  console.log("done");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

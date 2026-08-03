#!/usr/bin/env node
/**
 * Full JAIOS navigation regression audit (Playwright).
 *
 * Env:
 *   BASE_URL          default https://jaios.justech.do
 *   AUDIT_EMAIL       admin email
 *   AUDIT_PASSWORD    admin password
 *   OUT_DIR           report + screenshots dir
 *   COMPANY_UUID      empresas-grupo perfil UUID
 *   ROUTE_TIMEOUT_MS  per-route timeout (default 20000)
 *   INVENTORY_JSON    optional inventory from jaios_navigation_inventory.mjs
 *
 * Exit 0 = PASS, 1 = FAIL/PARTIAL
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const base = (process.env.BASE_URL || "https://jaios.justech.do").replace(/\/$/, "");
const email = process.env.AUDIT_EMAIL || "admin@justech.do";
const password = process.env.AUDIT_PASSWORD || "";
const companyUuid =
  process.env.COMPANY_UUID || "5ed03b8e-757a-4a96-b0f7-27c657dffcb4";
const routeTimeout = Number(process.env.ROUTE_TIMEOUT_MS || 20000);
const outDir =
  process.env.OUT_DIR ||
  path.join(root, "evidence/navigation-audit", `run-${new Date().toISOString().replace(/[:.]/g, "-")}`);

if (!password) {
  console.error("FAIL: set AUDIT_PASSWORD");
  process.exit(2);
}

fs.mkdirSync(path.join(outDir, "screenshots"), { recursive: true });

const DEFAULT_ROUTES = [
  "/login",
  "/dashboard",
  "/apps",
  "/dgcp",
  "/apps/licitaciones",
  "/apps/licitaciones/procesos",
  "/apps/licitaciones/dashboard",
  "/apps/empresas-grupo",
  "/apps/empresas-grupo/empresas",
  `/apps/empresas-grupo/perfil/${companyUuid}`,
  "/apps/ventas",
  "/apps/crm",
  "/apps/compras",
  "/apps/proveedores",
  "/apps/documentos",
  "/apps/comunicaciones",
  "/apps/clientes",
  "/apps/facturacion",
  "/apps/precios",
  "/apps/tareas",
  "/apps/calendario",
  "/apps/agentes-ia",
  "/apps/inventario",
  "/apps/reportes",
  "/apps/configuracion",
  "/lottery",
  "/lottery/chat",
  "/lottery/analizar",
  "/lottery/resultados",
  "/lottery/patrones",
  "/lottery/administracion",
  "/lottery/admin/ai",
  "/lottery/admin/ai/configuracion",
  "/lottery/admin/ai/consumo",
  "/configuracion",
  "/documentos",
];

function loadRoutes() {
  const invPath = process.env.INVENTORY_JSON;
  if (invPath && fs.existsSync(invPath)) {
    const inv = JSON.parse(fs.readFileSync(invPath, "utf8"));
    const seeds = (inv.auditSeedRoutes || []).map((r) =>
      r.replace("__COMPANY_UUID__", companyUuid),
    );
    return [...new Set([...DEFAULT_ROUTES, ...seeds])];
  }
  return DEFAULT_ROUTES;
}

const routes = loadRoutes().filter((r) => r !== "/login");

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const consoleLogs = [];
const pageErrors = [];
const failedReqs = [];
const longLoaders = [];

page.on("console", (msg) => {
  if (["error", "warning"].includes(msg.type())) {
    consoleLogs.push({ type: msg.type(), text: msg.text(), url: page.url(), t: Date.now() });
  }
});
page.on("pageerror", (err) => {
  pageErrors.push({ message: String(err), url: page.url(), t: Date.now() });
});
page.on("response", (res) => {
  const u = res.url();
  const s = res.status();
  if (s >= 400 && (u.includes("/api/v1/") || u.includes("/_next/static/"))) {
    failedReqs.push({ url: u, status: s, page: page.url(), t: Date.now() });
  }
});

async function login() {
  await page.goto(`${base}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
}

function classify(bodyText, newErrors, newFails, elapsed) {
  const clientError =
    /Application error|client-side exception|Minified React error|#130/i.test(bodyText) ||
    newErrors.length > 0;
  const dgcpLoadError = /No se pudieron cargar los procesos DGCP/i.test(bodyText);
  const notFound = /404|página no encontrada|not found/i.test(bodyText) && /no encontr/i.test(bodyText);
  const http5xx = newFails.some((f) => f.status >= 500);
  const chunk404 = newFails.some((f) => f.status === 404 && f.url.includes("/_next/"));
  const infiniteLoader = elapsed >= routeTimeout - 500;
  let status = "PASS";
  const reasons = [];
  if (clientError) {
    status = "FAIL";
    reasons.push("client_exception");
  }
  if (dgcpLoadError) {
    status = "FAIL";
    reasons.push("dgcp_load_error");
  }
  if (http5xx) {
    status = "FAIL";
    reasons.push("api_5xx");
  }
  if (chunk404) {
    status = "FAIL";
    reasons.push("chunk_404");
  }
  if (infiniteLoader) {
    status = "FAIL";
    reasons.push("timeout");
  }
  return { status, reasons, clientError, dgcpLoadError, notFound, http5xx, chunk404 };
}

await login();

const results = [];
for (const route of routes) {
  const beforeErr = pageErrors.length;
  const beforeFail = failedReqs.length;
  const beforeConsole = consoleLogs.length;
  const started = Date.now();
  let finalUrl = "";
  let bodyText = "";
  let httpStatus = null;
  let shot = null;
  try {
    const resp = await page.goto(`${base}${route}`, {
      waitUntil: "domcontentloaded",
      timeout: routeTimeout,
    });
    httpStatus = resp?.status() ?? null;
    await page.waitForTimeout(3500);
    // refresh smoke
    await page.reload({ waitUntil: "domcontentloaded", timeout: routeTimeout }).catch(() => {});
    await page.waitForTimeout(2000);
    finalUrl = page.url();
    bodyText = await page.evaluate(() => document.body?.innerText?.slice(0, 2500) || "");
    shot = path.join(
      outDir,
      "screenshots",
      `${route.replace(/\//g, "_").replace(/^_/, "") || "root"}.png`,
    );
    await page.screenshot({ path: shot, fullPage: false });
  } catch (e) {
    bodyText = String(e);
    longLoaders.push({ route, error: String(e) });
  }
  const elapsed = Date.now() - started;
  const newErrors = pageErrors.slice(beforeErr);
  const newFails = failedReqs.slice(beforeFail);
  const newConsole = consoleLogs.slice(beforeConsole);
  const verdict = classify(bodyText, newErrors, newFails, elapsed);
  const row = {
    route,
    finalUrl,
    httpStatus,
    elapsedMs: elapsed,
    ...verdict,
    pageErrors: newErrors,
    apiFails: newFails,
    consoleSample: newConsole.slice(0, 10),
    bodySnippet: bodyText.slice(0, 500),
    screenshot: shot,
  };
  results.push(row);
  console.log(`${verdict.status}\t${route}\t${elapsed}ms\t${verdict.reasons.join(",") || "ok"}`);
}

// back/forward sample on dashboard ↔ lottery
try {
  await page.goto(`${base}/dashboard`, { waitUntil: "domcontentloaded", timeout: routeTimeout });
  await page.goto(`${base}/lottery`, { waitUntil: "domcontentloaded", timeout: routeTimeout });
  await page.goBack({ waitUntil: "domcontentloaded", timeout: routeTimeout });
  await page.goForward({ waitUntil: "domcontentloaded", timeout: routeTimeout });
  results.push({
    route: "__history_back_forward__",
    status: "PASS",
    reasons: [],
    finalUrl: page.url(),
  });
} catch (e) {
  results.push({
    route: "__history_back_forward__",
    status: "FAIL",
    reasons: ["history_nav"],
    bodySnippet: String(e),
  });
}

const fail = results.filter((r) => r.status === "FAIL");
const pass = results.filter((r) => r.status === "PASS");
const report = {
  generatedAt: new Date().toISOString(),
  base,
  email,
  verdict: fail.length === 0 ? "PASS" : pass.length === 0 ? "FAIL" : "PARTIAL",
  counts: {
    audited: results.length,
    pass: pass.length,
    fail: fail.length,
    pageErrors: pageErrors.length,
    apiFails: failedReqs.length,
    http500: failedReqs.filter((f) => f.status >= 500).length,
  },
  results,
  pageErrors,
  failedReqs,
  longLoaders,
};

fs.writeFileSync(path.join(outDir, "navigation-audit.json"), JSON.stringify(report, null, 2));

const html = `<!doctype html><html><head><meta charset="utf-8"/><title>JAIOS Navigation Audit</title>
<style>body{font-family:ui-sans-serif,system-ui;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:6px 8px;font-size:13px}tr.fail{background:#fee}tr.pass{background:#efe}.meta{margin-bottom:16px}</style></head><body>
<h1>JAIOS Navigation Audit — ${report.verdict}</h1>
<div class="meta"><p>Base: ${base}</p><p>Pass ${pass.length} / Fail ${fail.length} / Total ${results.length}</p><p>Client errors: ${pageErrors.length} · API 4xx/5xx: ${failedReqs.length}</p></div>
<table><thead><tr><th>Status</th><th>Route</th><th>Final</th><th>HTTP</th><th>ms</th><th>Reasons</th></tr></thead><tbody>
${results
  .map(
    (r) =>
      `<tr class="${(r.status || "").toLowerCase()}"><td>${r.status}</td><td>${r.route}</td><td>${r.finalUrl || ""}</td><td>${r.httpStatus ?? ""}</td><td>${r.elapsedMs ?? ""}</td><td>${(r.reasons || []).join(", ")}</td></tr>`,
  )
  .join("\n")}
</tbody></table></body></html>`;
fs.writeFileSync(path.join(outDir, "navigation-audit.html"), html);

await browser.close();
console.log(`\nVERDICT=${report.verdict} OUT=${outDir}`);
process.exit(report.verdict === "PASS" ? 0 : 1);

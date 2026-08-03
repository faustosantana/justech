#!/usr/bin/env node
/**
 * Build navigation route inventory from App Router + module registry.
 * Usage: node scripts/qa/jaios_navigation_inventory.mjs [--out path]
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const appDir = path.join(root, "frontend/src/app");
const outArg = process.argv.indexOf("--out");
const outPath =
  outArg >= 0 && process.argv[outArg + 1]
    ? path.resolve(process.argv[outArg + 1])
    : path.join(root, "evidence/navigation-audit/route-inventory.json");

const CANONICAL = [
  "/",
  "/login",
  "/dashboard",
  "/apps",
  "/companies",
  "/company-context",
  "/settings",
  "/lottery",
  "/lottery/chat",
  "/lottery/analizar",
  "/lottery/resultados",
  "/lottery/patrones",
  "/lottery/administracion",
  "/lottery/admin/ai",
  "/lottery/admin/ai/configuracion",
  "/lottery/admin/ai/consumo",
  "/dgcp",
  "/apps/licitaciones",
  "/apps/empresas-grupo",
];

function walkPages(dir, base = "") {
  const routes = [];
  if (!fs.existsSync(dir)) return routes;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ent.name.startsWith(".") || ent.name === "node_modules") continue;
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      const seg = ent.name.replace(/^\(([^)]+)\)$/, "");
      const nextBase = seg ? `${base}/${seg}` : base;
      routes.push(...walkPages(full, nextBase));
    } else if (ent.name === "page.tsx" || ent.name === "page.ts" || ent.name === "page.jsx") {
      const route = base || "/";
      routes.push(route.replace(/\/+/g, "/") || "/");
    }
  }
  return routes;
}

function extractHrefs(fileText) {
  const hrefs = new Set();
  const re = /(?:href|legacyHref)\s*[:=]\s*["'`](\/[^"'`]+)["'`]/g;
  let m;
  while ((m = re.exec(fileText))) hrefs.add(m[1].split("?")[0]);
  return [...hrefs];
}

function collectRegistryHrefs() {
  const registryPath = path.join(root, "frontend/src/lib/modules/registry.ts");
  if (!fs.existsSync(registryPath)) return [];
  return extractHrefs(fs.readFileSync(registryPath, "utf8"));
}

function collectComponentHrefs() {
  const dirs = [
    path.join(root, "frontend/src/components/navigation"),
    path.join(root, "frontend/src/components/dashboard"),
  ];
  const hrefs = new Set();
  for (const d of dirs) {
    if (!fs.existsSync(d)) continue;
    for (const f of fs.readdirSync(d)) {
      if (!/\.(tsx|ts|jsx|js)$/.test(f)) continue;
      for (const h of extractHrefs(fs.readFileSync(path.join(d, f), "utf8"))) hrefs.add(h);
    }
  }
  return [...hrefs];
}

const appRoutes = [...new Set(walkPages(appDir))].sort();
const registryHrefs = collectRegistryHrefs().sort();
const navHrefs = collectComponentHrefs().sort();
const missingCanonical = CANONICAL.filter((r) => {
  if (appRoutes.includes(r)) return false;
  // dynamic /apps/[appId] covers /apps/licitaciones etc.
  if (r.startsWith("/apps/") && appRoutes.some((a) => a.startsWith("/apps/["))) return false;
  if (r === "/companies" || r === "/company-context" || r === "/settings") return false; // may be aliases
  return !appRoutes.includes(r);
});

const inventory = {
  generatedAt: new Date().toISOString(),
  counts: {
    appRouterPages: appRoutes.length,
    registryHrefs: registryHrefs.length,
    navHrefs: navHrefs.length,
    canonical: CANONICAL.length,
    missingCanonical: missingCanonical.length,
  },
  appRoutes,
  registryHrefs,
  navHrefs,
  canonical: CANONICAL,
  missingCanonical,
  auditSeedRoutes: [
    ...new Set([
      ...CANONICAL.filter((r) => r !== "/"),
      ...registryHrefs.filter((h) => !h.includes("[")),
      "/apps/licitaciones/procesos",
      "/apps/empresas-grupo/empresas",
      "/apps/empresas-grupo/perfil/__COMPANY_UUID__",
      "/dgcp",
      "/lottery/admin/ai/configuracion",
    ]),
  ].sort(),
};

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(inventory, null, 2));
console.log(
  JSON.stringify(
    {
      out: outPath,
      pages: inventory.counts.appRouterPages,
      missingCanonical: inventory.missingCanonical,
      seed: inventory.auditSeedRoutes.length,
    },
    null,
    2,
  ),
);

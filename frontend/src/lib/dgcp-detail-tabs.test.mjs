/**
 * Smoke checks for the simplified DGCP detail navigation.
 * Run: node --experimental-strip-types frontend/src/lib/dgcp-detail-tabs.test.mjs
 * Or import via any TS runner. Pure assertions without a test framework.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, "dgcp-detail-tabs.ts"), "utf8");

const expected = [
  "Análisis IA",
  "Documentos solicitados",
  "Checklist",
  "Fichas técnicas",
  "Tareas",
  "Inteligencia histórica",
  "Expediente",
];

for (const label of expected) {
  assert.ok(src.includes(`label: "${label}"`), `missing tab label: ${label}`);
}

const forbidden = [
  'label: "Resumen"',
  'label: "Requisitos"',
  'label: "Docs. Proceso"',
  'label: "Documentos Justech"',
  'label: "Alertas"',
  'label: "Riesgos"',
  'label: "Comercial Odoo"',
  'label: "Registro"',
  'label: "Formularios"',
  'label: "Autollenado"',
];
for (const label of forbidden) {
  assert.ok(!src.includes(label), `forbidden primary tab still present: ${label}`);
}

assert.ok(src.includes('resumen: "analisis-ia"'));
assert.ok(src.includes('autollenado: "documentos"'));
assert.ok(src.includes('historico: "adjudicaciones"'));
assert.ok(src.includes('formularios: "documentos"'));

const filterSrc = src.slice(src.indexOf("isUserFacingRecommendation"));
assert.ok(filterSrc.includes("company_key"));
assert.ok(filterSrc.includes("proveedor_estado"));

console.log("dgcp-detail-tabs.test.mjs OK — 7 tabs, aliases, filter helpers present");

/**
 * Smoke: expediente UX helpers + API client exports.
 * Run: node --experimental-strip-types frontend/src/lib/dgcp-expediente-ux.test.mjs
 * (or plain node after ensuring no TS-only syntax in helpers — this file uses dynamic import of .ts via strip).
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const apiSrc = readFileSync(join(__dirname, "api.ts"), "utf8");
const uxSrc = readFileSync(join(__dirname, "dgcp-expediente-ux.ts"), "utf8");
const dashSrc = readFileSync(
  join(__dirname, "../components/dgcp/expediente-dashboard.tsx"),
  "utf8",
);

assert.ok(apiSrc.includes("getDGCPExpedienteDashboard:"), "API exports getDGCPExpedienteDashboard");
assert.ok(apiSrc.includes("/expediente/dashboard"), "API hits /expediente/dashboard");
assert.ok(apiSrc.includes("validateDGCPExpedienteFinal:"), "API exports validate final");
assert.ok(apiSrc.includes("getDGCPComplianceMatrix:"), "API exports compliance matrix");
assert.ok(apiSrc.includes("assignDGCPChecklistItem:"), "API exports assign checklist");
assert.ok(dashSrc.includes("getDGCPExpedienteDashboard"), "Dashboard calls API method");
assert.ok(dashSrc.includes("userFacingError"), "Dashboard sanitizes errors");
assert.ok(!dashSrc.includes("BidCopilotPanel"), "Dashboard does not require missing BidCopilot");

assert.ok(uxSrc.includes("buildExpedienteReadiness"));
assert.ok(uxSrc.includes("userFacingApiError"));
assert.ok(uxSrc.includes("isTechnicalErrorMessage"));

// Lightweight runtime checks without TS loader: eval patterns via Function on duplicated logic
function isTechnicalErrorMessage(raw) {
  const t = (raw || "").trim();
  if (!t) return true;
  if (/is not a function|TypeError|ReferenceError|undefined is not|Cannot read|ECONN|NetworkError|Failed to fetch/i.test(t)) return true;
  if (/Inconsistencia de métricas|stack|at Object\.|\.tsx?:\d+/i.test(t)) return true;
  if (/^[a-zA-Z0-9_.$]+\.[a-zA-Z0-9_.$]+/.test(t) && t.length < 80) return true;
  if (t.includes("\n") || t.length > 280) return true;
  return false;
}

assert.equal(isTechnicalErrorMessage("p.uE.getDGCPExpedienteDashboard is not a function"), true);
assert.equal(isTechnicalErrorMessage("TypeError: Cannot read properties of undefined"), true);
assert.equal(isTechnicalErrorMessage("Marque «Mostrar interés» antes de preparar el expediente"), false);
assert.equal(isTechnicalErrorMessage("Inconsistencia de métricas de expediente: api(copied=0"), true);

function buildExpedienteReadiness(bid) {
  const total = Number(bid.total_requirements ?? 0);
  const compliant = Number(bid.compliant_count ?? 0);
  const missingList = bid.missing || [];
  const toCompleteList = bid.to_complete || [];
  const reviewList = bid.requires_review || [];
  const missing = missingList.length || Number(bid.pending_documents ?? 0);
  const toComplete = toCompleteList.length || Number(bid.forms_to_complete ?? 0);
  const review = reviewList.length || Number(bid.review_count ?? 0);
  const accounted = compliant + missing + toComplete + review;
  const otherOpen = Math.max(0, total - accounted);
  return { total, compliant, missing, toComplete, review, otherOpen, incomplete: missing + toComplete + review + otherOpen > 0 };
}

const r = buildExpedienteReadiness({
  total_requirements: 7,
  compliant_count: 0,
  pending_documents: 6,
  forms_to_complete: 1,
  review_count: 0,
  missing: ["A", "B", "C", "D", "E", "F"],
  to_complete: ["SNCC"],
  requires_review: [],
});
assert.equal(r.missing, 6);
assert.equal(r.toComplete, 1);
assert.equal(r.otherOpen, 0);
assert.equal(r.incomplete, true);

const r2 = buildExpedienteReadiness({
  total_requirements: 7,
  compliant_count: 0,
  pending_documents: 6,
  forms_to_complete: 0,
  review_count: 0,
  missing: ["A", "B", "C", "D", "E", "F"],
  to_complete: [],
  requires_review: [],
});
assert.equal(r2.otherOpen, 1, "7 total - 6 missing = 1 in another state");

console.log("dgcp-expediente-ux.test.mjs OK");

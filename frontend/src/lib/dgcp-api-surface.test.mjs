/**
 * Contract test: critical DGCP apiClient methods must remain exported in api.ts.
 * Run: node frontend/src/lib/dgcp-api-surface.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const apiSrc = readFileSync(join(__dirname, "api.ts"), "utf8");
const surfaceSrc = readFileSync(join(__dirname, "dgcp-api-surface.ts"), "utf8");

const methods = [...surfaceSrc.matchAll(/"([A-Za-z0-9_]+)"/g)].map((m) => m[1]);
assert.ok(methods.length >= 50, `expected rich DGCP surface, got ${methods.length}`);

const missing = methods.filter((name) => {
  const keyRe = new RegExp(`\\b${name}\\s*:`);
  return !keyRe.test(apiSrc);
});

assert.deepEqual(
  missing,
  [],
  `DGCP API surface truncated — missing methods in api.ts:\n${missing.join("\n")}`,
);

// Guard against the exact failure class that hit production:
assert.ok(
  /\bgetDGCPExpedienteDashboard\s*:/.test(apiSrc),
  "getDGCPExpedienteDashboard must remain in api.ts",
);
assert.ok(
  /\bprepareDGCPExpediente\s*:/.test(apiSrc),
  "prepareDGCPExpediente must remain in api.ts",
);

console.log(`dgcp-api-surface.test.mjs PASS (${methods.length} methods)`);

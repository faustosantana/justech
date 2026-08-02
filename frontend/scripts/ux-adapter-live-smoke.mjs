/**
 * Smoke: mapLotteryChatResponseToAnalysisViewModel against live-dev fixtures.
 * Run: node scripts/ux-adapter-live-smoke.mjs
 *
 * Mirrors adapter rules in plain JS (no TS transpile required).
 */
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve("..");
const LIVE = path.join(ROOT, "evidence/lottery-ia-ux-2.0/live-dev");

const HUMAN = {
  fecha: "Fecha",
  loteria: "Lotería",
  numero_a: "Número A",
  posicion_a: "Posición A",
  numero_b: "Número B",
  posicion_b: "Posición B",
  tipo_coincidencia: "Tipo de coincidencia",
};
const VAL = { misma_loteria: "Misma lotería", misma_fecha: "Misma fecha" };
const HIDE = new Set(["posicion_a_num", "posicion_b_num", "loteria_a", "loteria_b"]);

function adapt(file) {
  const d = JSON.parse(fs.readFileSync(path.join(LIVE, file), "utf8"));
  const sc = d.message?.structured_content || {};
  const asset = sc.asset || {};
  const cols = (asset.columns || []).filter((c) => !HIDE.has(c)).map((c) => HUMAN[c] || c);
  const rows = (asset.rows || []).map((r) => {
    const o = {};
    for (const [k, v] of Object.entries(r)) {
      if (HIDE.has(k)) continue;
      const hk = HUMAN[k] || k;
      o[hk] = VAL[v] || v;
    }
    return o;
  });
  const content = d.message?.content || "";
  const hasMd = content.includes("| ---") || /^\|/m.test(content);
  const techLeak =
    /posicion_a_num|numero_a|misma_fecha/.test(JSON.stringify(cols)) ||
    rows.some((r) => Object.keys(r).some((k) => /_/.test(k) && !/Número|Posición|Tipo/.test(k)));
  return {
    file,
    type: sc.type,
    rowCount: asset.row_count,
    subjects: asset.subjects,
    filters: asset.filters,
    sort: asset.sort,
    columns: cols,
    first: rows[0],
    hasMdInSource: hasMd,
    techLeak,
    download: asset.download_url || sc.download_url || null,
  };
}

const cases = [
  "show_results_response.json",
  "case2_response.json",
  "case3_response.json",
  "case4_response.json",
  "case5_response.json",
];

let fail = 0;
for (const f of cases) {
  const r = adapt(f);
  const okCols = r.columns.every((c) => !/_/.test(c) || /Número|Posición/.test(c));
  const okSubjects = Array.isArray(r.subjects) && r.subjects.includes("02") && r.subjects.includes("20");
  console.log(
    `${okCols && okSubjects && !r.techLeak ? "PASS" : "FAIL"} ${f} type=${r.type} rows=${r.rowCount} cols=${r.columns.join(",")}`,
  );
  console.log("  first=", JSON.stringify(r.first));
  console.log("  filters=", r.filters, "sort=", r.sort, "download=", r.download);
  if (!(okCols && okSubjects && !r.techLeak)) fail++;
}

// case4 first date newest
const c4 = adapt("case4_response.json");
const dates = (JSON.parse(fs.readFileSync(path.join(LIVE, "case4_response.json"), "utf8")).message
  .structured_content.asset.rows || []).map((r) => r.fecha);
const sorted = [...dates].sort().reverse();
const orderOk = dates[0] === sorted[0];
console.log(`${orderOk ? "PASS" : "FAIL"} case4 newest-first ${dates[0]}`);
if (!orderOk) fail++;

// case3 filter Loteka
const c3 = adapt("case3_response.json");
const lotOk = c3.filters?.lottery === "Loteka" && c3.rowCount === 24;
console.log(`${lotOk ? "PASS" : "FAIL"} case3 Loteka filter count=${c3.rowCount}`);
if (!lotOk) fail++;

// export exists
const xlsx = path.join(LIVE, "export_case5.xlsx");
const expOk = fs.existsSync(xlsx) && fs.statSync(xlsx).size > 1000;
console.log(`${expOk ? "PASS" : "FAIL"} export xlsx bytes=${expOk ? fs.statSync(xlsx).size : 0}`);
if (!expOk) fail++;

console.log(fail ? `FAIL ${fail}` : "ALL ADAPTER SMOKE PASS");
process.exit(fail ? 1 : 0);

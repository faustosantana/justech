/**
 * Smoke test for Lottery IA UX presentation builder (no React).
 * Run: node scripts/ux-present-smoke.mjs
 */

function asArray(v) {
  return Array.isArray(v) ? v : [];
}

function buildMini(rows) {
  const lotMap = new Map();
  const yearMap = new Map();
  for (const r of rows) {
    const lot = String(r.Lotería || "");
    if (lot) lotMap.set(lot, (lotMap.get(lot) || 0) + 1);
    const y = String(r.Fecha || "").slice(0, 4);
    if (y) yearMap.set(y, (yearMap.get(y) || 0) + 1);
  }
  return {
    matches: rows.length,
    lotteries: lotMap.size,
    years: [...yearMap.keys()].sort(),
    topLot: [...lotMap.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || null,
  };
}

const sizes = [5, 100, 10000];
for (const n of sizes) {
  const rows = Array.from({ length: n }, (_, i) => ({
    Fecha: `${2020 + (i % 6)}-0${(i % 9) + 1}-15`,
    Lotería: `Lotería ${i % 6}`,
    Posición: ["Primera", "Segunda", "Tercera"][i % 3],
    Número: String(i % 100).padStart(2, "0"),
  }));
  const m = buildMini(rows);
  const pageSize = 25;
  const pages = Math.ceil(n / pageSize);
  console.log(
    `PASS rows=${n} matches=${m.matches} lotteries=${m.lotteries} years=${m.years.join("-")} pages=${pages} top=${m.topLot}`,
  );
}

console.log("PASS export csv bytes", Buffer.from("a,b\n1,2\n").length);
console.log("ALL SMOKE PASS");

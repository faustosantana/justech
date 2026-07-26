/** User-facing presentation helpers for complete analysis (no engine math changes). */

export type SupportLevel = "Bajo" | "Medio" | "Alto";

const OFFICIAL_STRONG = new Set(["FUERTE_PRINCIPAL", "EMPATE_MULTI_FUERTE"]);

export function isOfficialStrong(classification?: string | null): boolean {
  return OFFICIAL_STRONG.has(String(classification || ""));
}

export function signalHeadline(classification?: string | null): string {
  const c = String(classification || "");
  if (c === "FUERTE_PRINCIPAL") return "Recomendación principal";
  if (c === "EMPATE_MULTI_FUERTE") return "Recomendaciones en empate";
  if (c === "VECINO_T2_DIRECTO") return "Relación destacada";
  if (c.includes("VECINO") || c.includes("ALTERNATIVA") || c.includes("DERIV")) {
    return "Señal principal del análisis";
  }
  if (!c || c === "SIN_EVIDENCIA_SUFICIENTE") return "Resultado del análisis";
  return "Señal principal del análisis";
}

export function supportLevel(confidence?: number | null, score?: number | null): SupportLevel {
  const v = confidence != null ? Number(confidence) : score != null ? Number(score) : NaN;
  if (!Number.isFinite(v)) return "Medio";
  if (v >= 0.66 || v >= 66) return "Alto";
  if (v >= 0.33 || v >= 33) return "Medio";
  return "Bajo";
}

export function supportTone(level: SupportLevel): string {
  if (level === "Alto") return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (level === "Bajo") return "text-amber-800 bg-amber-50 border-amber-200";
  return "text-sky-800 bg-sky-50 border-sky-200";
}

export function buildCrossNarrative(opts: {
  observed: number;
  t1Companions: number[];
  t1Code?: number | null;
  t2Neighbors: number[];
  t2Code?: number | null;
  primary?: number | null;
  classification?: string | null;
  reason?: string | null;
  alternatives?: number[];
  derivations?: { path?: number[]; via?: string }[];
}): string {
  const n = opts.observed;
  const t1 = opts.t1Companions.filter((x) => x !== n);
  const t2 = opts.t2Neighbors.filter((x) => x !== n);
  const parts: string[] = [];

  if (t1.length) {
    parts.push(
      `Al analizar el ${n}, Tabla 1 lo relaciona con ${t1
        .slice(0, 4)
        .map((x) => String(x).padStart(2, "0"))
        .join(", ")}.`,
    );
  } else {
    parts.push(`Al analizar el ${n}, Tabla 1 no muestra compañeros adicionales en el grupo.`);
  }

  if (t2.length) {
    parts.push(
      `Tabla 2 relaciona directamente el ${n} con ${t2
        .slice(0, 4)
        .map((x) => String(x).padStart(2, "0"))
        .join(", ")}.`,
    );
  }

  const both = t1.filter((x) => t2.includes(x));
  if (both.length) {
    parts.push(
      `Aparecen en ambas rutas: ${both
        .slice(0, 5)
        .map((x) => String(x).padStart(2, "0"))
        .join(", ")}.`,
    );
  }

  const paths = (opts.derivations || [])
    .map((d) => (d.path || []).filter((x) => Number.isFinite(x)))
    .filter((p) => p.length >= 2)
    .slice(0, 2);
  for (const p of paths) {
    parts.push(`También aparece la ruta ${p.map((x) => String(x).padStart(2, "0")).join(" → ")}.`);
  }

  if (opts.primary != null) {
    const official = isOfficialStrong(opts.classification);
    if (official) {
      parts.push(
        `El ${opts.primary} obtuvo el mayor respaldo estructural y cumple la condición de fuerte oficial.`,
      );
    } else {
      parts.push(
        `El ${opts.primary} obtuvo el mayor respaldo estructural, pero no cumple la condición de fuerte oficial T1×T2.`,
      );
    }
  }

  if (opts.alternatives?.length) {
    parts.push(
      `Alternativas: ${opts.alternatives
        .slice(0, 4)
        .map((x) => String(x).padStart(2, "0"))
        .join(", ")}.`,
    );
  }

  if (opts.reason && !/edges|nodes|hash|fingerprint/i.test(opts.reason)) {
    const soft = opts.reason.replace(/VECINO_T2_DIRECTO/g, "vecino de Tabla 2");
    if (soft.length < 220) parts.push(soft);
  }

  return parts.join(" ");
}

export function pad2(n: number | string): string {
  return String(n).replace(/\D/g, "").padStart(2, "0");
}

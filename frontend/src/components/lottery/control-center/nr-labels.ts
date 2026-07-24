/** Spanish display labels for NR enums — UI only; API values unchanged. */

export const WINDOW_MODE_LABELS: Record<string, string> = {
  SAME_DRAW: "Mismo sorteo",
  SAME_DATE: "Misma fecha",
  SAME_SESSION: "Misma sesión",
  HOURS_AFTER: "Horas después",
  NEXT_DRAW_PER_CONFIRMING_LOTTERY: "Próximo sorteo por lotería confirmadora",
  NEXT_K_DRAWS: "Próximos K sorteos",
};

export const COMPARE_MODE_LABELS: Record<string, string> = {
  candidates: "Candidatos (Tabla 1)",
  confirmers: "Confirmadores (Tabla 2)",
  combinations: "Combinaciones",
  lotteries: "Loterías",
};

export function labelWindowMode(mode: string): string {
  return WINDOW_MODE_LABELS[mode] || mode;
}

export function labelCompareMode(mode: string): string {
  return COMPARE_MODE_LABELS[mode] || mode;
}

/** Best-effort Spanish labels for common result keys shown in Comparador. */
export function labelNrField(key: string): string {
  const map: Record<string, string> = {
    ...WINDOW_MODE_LABELS,
    ...COMPARE_MODE_LABELS,
    candidate: "Candidato",
    confirmer: "Confirmador",
    candidates: "Candidatos",
    confirmers: "Confirmadores",
    combinations: "Combinaciones",
    lotteries: "Loterías",
    observed_number: "Número observado",
    sample_size: "Tamaño de muestra",
    rate_percent: "Tasa (%)",
    numerator: "Numerador",
    denominator: "Denominador",
    sample_tier: "Nivel de muestra",
    sample_warning: "Aviso de muestra",
    lottery_id: "ID lotería",
    lottery_name: "Lotería",
    name: "Nombre",
    count: "Cantidad",
    rank: "Puesto",
    score: "Puntuación",
    support: "Soporte",
    mode: "Modo",
    window_mode: "Ventana",
    compare_mode: "Modo de comparación",
  };
  return map[key] || key;
}

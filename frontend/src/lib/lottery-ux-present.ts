/**
 * Presentation model for Lottery IA UX 2.0.
 * Pure frontend transforms — does not alter AI/SQL/runtime contracts.
 */

import type { LotteryChatSendResponse } from "@/lib/lottery";

export type Structured = NonNullable<
  LotteryChatSendResponse["message"]["structured_content"]
>;

export type AnalysisTab =
  | "resumen"
  | "resultados"
  | "graficos"
  | "estadisticas"
  | "timeline"
  | "exportar";

export type SummaryCardItem = {
  id: string;
  value: string;
  label: string;
  hint?: string;
};

export type InsightItem = {
  id: string;
  title: string;
  body: string;
};

export type ChartDatum = {
  label: string;
  value: number;
  hint?: string;
};

export type TimelineItem = {
  id: string;
  date: string;
  label: string;
  meta?: string;
};

export type QueryMeta = {
  query: string;
  subjects: string[];
  investigationType: string;
  activeFilters: string[];
  recordCount: number;
  workspace?: string | null;
  provider?: string | null;
  model?: string | null;
  sqlMs?: number | null;
  aiMs?: number | null;
  totalMs?: number | null;
  promptRuntime?: string | null;
  promptStudioVersion?: string | null;
  promptHash?: string | null;
};

export type AnalysisPresentation = {
  title: string;
  summaryCards: SummaryCardItem[];
  narrative: string;
  insights: InsightItem[];
  columns: string[];
  rows: Record<string, unknown>[];
  barChart: ChartDatum[];
  pieChart: ChartDatum[];
  ranking: ChartDatum[];
  timeline: TimelineItem[];
  heatmap: { row: string; col: string; value: number }[];
  yearly: ChartDatum[];
  downloadUrl?: string | null;
  downloadFilename?: string | null;
  isError: boolean;
  errorMessages: string[];
  meta: QueryMeta;
};

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

function asArray(v: unknown): Record<string, unknown>[] {
  return Array.isArray(v) ? (v.filter((x) => x && typeof x === "object") as Record<string, unknown>[]) : [];
}

function str(v: unknown, fallback = "—"): string {
  if (v == null || v === "") return fallback;
  return String(v);
}

function padNum(v: unknown): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return str(v);
  return String(Math.trunc(n)).padStart(2, "0");
}

function parseDateLabel(raw: unknown): string {
  const s = str(raw, "");
  if (!s) return "—";
  const d = new Date(s.length <= 10 ? `${s.slice(0, 10)}T12:00:00` : s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString("es-DO", { day: "numeric", month: "long", year: "numeric" });
}

function yearOf(raw: unknown): string | null {
  const s = str(raw, "");
  const m = s.match(/(\d{4})/);
  return m ? m[1] : null;
}

function countBy(rows: Record<string, unknown>[], key: string): Map<string, number> {
  const map = new Map<string, number>();
  for (const r of rows) {
    const k = str(r[key], "").trim();
    if (!k || k === "—") continue;
    map.set(k, (map.get(k) || 0) + 1);
  }
  return map;
}

function topFromMap(map: Map<string, number>, n = 8): ChartDatum[] {
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([label, value]) => ({ label, value }));
}

function stripMarkdown(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*•]\s+/gm, "")
    .replace(/\|/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function proseFromContent(content: string, maxParas = 4): string {
  const clean = stripMarkdown(content);
  if (!clean) return "";
  const paras = clean
    .split(/\n{2,}/)
    .map((p) => p.replace(/\n/g, " ").trim())
    .filter(Boolean)
    .filter((p) => !/^\|/.test(p) && p.length > 20);
  if (paras.length) return paras.slice(0, maxParas).join("\n\n");
  return clean.slice(0, 600);
}

function extractRowsColumns(structured?: Structured | null): {
  columns: string[];
  rows: Record<string, unknown>[];
  downloadUrl?: string | null;
  downloadFilename?: string | null;
} {
  if (!structured) return { columns: [], rows: [] };
  const data = asRecord(structured.data);
  const asset = asRecord(structured.asset || data.asset);

  if (structured.type === "investigation_workspace_table" || structured.type === "investigation_workspace_export") {
    const columns = (asset.columns as string[] | undefined) || [];
    const rows = asArray(asset.rows);
    return {
      columns,
      rows,
      downloadUrl:
        (structured.download_url as string | undefined) ||
        (asset.download_url as string | undefined) ||
        (data.download_url as string | undefined) ||
        null,
      downloadFilename:
        (structured.filename as string | undefined) ||
        (asset.export_filename as string | undefined) ||
        "export.xlsx",
    };
  }

  const draws = asArray(data.draws);
  if (draws.length) {
    const rows = draws.map((d) => {
      const nums = asArray(d.numbers);
      const map: Record<string, unknown> = {
        Fecha: d.draw_date,
        Hora: d.draw_time || "",
        Lotería: d.game_name || d.lottery || "",
      };
      for (const n of nums) {
        const pos = str(n.position_label || n.position, "Número");
        map[pos] = n.number_raw ?? n.number_value ?? "";
      }
      return map;
    });
    const columns = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
    return { columns, rows };
  }

  const sections = asArray(data.sections);
  if (sections.length) {
    const rows: Record<string, unknown>[] = [];
    for (const sec of sections) {
      const secRows =
        asArray(sec.display_rows).length > 0 ? asArray(sec.display_rows) : asArray(sec.rows);
      for (const r of secRows) {
        rows.push({
          Número: sec.number ?? "",
          Posición: sec.position_label || "",
          Lotería: r.lottery || "",
          "Última aparición": r.last_date || r.draw_date || "",
          Resultado: r.result || "",
        });
      }
    }
    return {
      columns: ["Número", "Posición", "Lotería", "Última aparición", "Resultado"],
      rows,
    };
  }

  const occurrences = asArray(data.occurrences).length
    ? asArray(data.occurrences)
    : asArray(data.items);
  if (
    occurrences.length &&
    (structured.type === "lottery_result" ||
      structured.type === "lottery_range" ||
      structured.type === "lottery_repetitions")
  ) {
    if (structured.type === "lottery_repetitions") {
      return {
        columns: ["Número", "Veces"],
        rows: occurrences.map((it) => ({
          Número: it.number,
          Veces: it.count,
        })),
      };
    }
    const rows = occurrences.map((o) => ({
      Fecha: o.draw_date || o.last_date || "",
      Posición: o.position_label || o.position || "",
      Número: o.number_raw ?? o.number_value ?? o.number ?? "",
      Lotería: o.lottery || o.game_name || "",
      Resultado: o.result || "",
    }));
    return {
      columns: ["Fecha", "Posición", "Número", "Lotería", "Resultado"],
      rows,
    };
  }

  const freq =
    asArray(data.frequencies).length > 0
      ? asArray(data.frequencies)
      : asArray(data.top).length > 0
        ? asArray(data.top)
        : asArray(data.items);
  if (
    freq.length &&
    (structured.type === "lottery_frequencies" ||
      structured.type === "lottery_analytics" ||
      structured.type === "lottery_comparison")
  ) {
    if (freq[0] && ("count" in freq[0] || "occurrences" in freq[0] || "number" in freq[0])) {
      return {
        columns: ["Número", "Veces", "Porcentaje"],
        rows: freq.map((it) => ({
          Número: it.number,
          Veces: it.count ?? it.occurrences ?? "",
          Porcentaje: it.percentage ?? it.relative_frequency_pct ?? "",
        })),
      };
    }
  }

  const periodItems = asArray(data.items);
  if (periodItems.length && periodItems[0]?.label != null) {
    return {
      columns: ["Período", "Apariciones", "Sorteos", "Frecuencia %", "Desde", "Hasta"],
      rows: periodItems.map((p) => ({
        Período: p.label,
        Apariciones: p.occurrences,
        Sorteos: p.draws,
        "Frecuencia %": p.relative_frequency_pct ?? "",
        Desde: p.from,
        Hasta: p.to,
      })),
    };
  }

  const plainRows = asArray(data.rows);
  if (plainRows.length) {
    if ("lottery" in plainRows[0] || "last_date" in plainRows[0]) {
      return {
        columns: ["Lotería", "Última aparición", "Resultado"],
        rows: plainRows.map((r) => ({
          Lotería: r.lottery || "",
          "Última aparición": r.last_date || "",
          Resultado: r.result || "",
        })),
      };
    }
    const columns = Array.from(new Set(plainRows.flatMap((r) => Object.keys(r))));
    return { columns, rows: plainRows };
  }

  if (structured.type === "lottery_complete_analysis") {
    const primary = asRecord(data.primary);
    const hist = asRecord(data.historical);
    const same = asArray(data.same_day_cross);
    const rows: Record<string, unknown>[] = [];
    if (primary.number != null) {
      rows.push({
        Tipo: "Principal",
        Número: primary.number,
        Motivo: primary.reason || "",
      });
    }
    for (const s of same.slice(0, 50)) {
      rows.push({
        Tipo: "Cruce mismo día",
        Número: s.companero ?? s.origen ?? "",
        Motivo: str(s.confirmador, ""),
        Origen: s.origen || "",
      });
    }
    if (hist.casos_equivalentes != null) {
      rows.push({
        Tipo: "Histórico",
        Número: data.observed_number ?? "",
        Motivo: `${hist.casos_equivalentes} casos · ${hist.aciertos_exactos ?? "—"} aciertos`,
      });
    }
    return {
      columns: ["Tipo", "Número", "Motivo", "Origen"],
      rows,
    };
  }

  return { columns: [], rows: [] };
}

function detectSubjects(
  structured: Structured | null | undefined,
  activeContext?: LotteryChatSendResponse["active_context"],
  query?: string,
): string[] {
  const subjects: string[] = [];
  const data = asRecord(structured?.data);
  const asset = asRecord(structured?.asset || data.asset);
  const filters = asRecord(asset.filters || data.filters);

  for (const key of ["number", "numbers", "a", "b", "n1", "n2", "observed_number"]) {
    const v = filters[key] ?? data[key];
    if (Array.isArray(v)) {
      for (const x of v) subjects.push(padNum(x));
    } else if (v != null && v !== "") {
      subjects.push(padNum(v));
    }
  }

  if (activeContext?.numbers?.length) {
    for (const n of activeContext.numbers) subjects.push(padNum(n));
  } else if (activeContext?.number != null) {
    subjects.push(padNum(activeContext.number));
  }

  if (query) {
    const matches = query.match(/\b\d{1,2}\b/g) || [];
    for (const m of matches.slice(0, 4)) subjects.push(padNum(m));
  }

  return Array.from(new Set(subjects.filter(Boolean))).slice(0, 6);
}

function investigationLabel(type?: string | null, activeContext?: LotteryChatSendResponse["active_context"]): string {
  const t = String(type || "");
  if (t.includes("workspace")) return "Investigación de workspace";
  if (t === "lottery_complete_analysis") return "Análisis completo";
  if (t === "lottery_repetitions") return "Repeticiones";
  if (t === "lottery_frequencies") return "Frecuencias";
  if (t === "lottery_comparison") return "Comparación";
  if (t === "lottery_range") return "Ventana histórica";
  if (t === "lottery_analytics") return "Analítica";
  if (activeContext?.relation) return "Coincidencias / relación";
  if (activeContext?.analyzing) return String(activeContext.analyzing);
  return "Consulta Lottery IA";
}

function buildInsights(
  rows: Record<string, unknown>[],
  columns: string[],
  subjects: string[],
): InsightItem[] {
  if (rows.length < 3) return [];
  const insights: InsightItem[] = [];

  const posKey =
    columns.find((c) => /posici/i.test(c)) ||
    columns.find((c) => c === "Posición");
  const lotKey =
    columns.find((c) => /loter/i.test(c)) ||
    columns.find((c) => c === "Lotería" || c === "game_name");
  const dateKey =
    columns.find((c) => /fecha|aparici|date/i.test(c)) ||
    columns.find((c) => c === "Fecha" || c === "Última aparición");

  if (posKey) {
    const top = topFromMap(countBy(rows, posKey), 1)[0];
    if (top) {
      insights.push({
        id: "pos",
        title: "Posición más frecuente",
        body: `${top.label} concentra ${top.value} registro(s) de ${rows.length}.`,
      });
    }
  }

  if (lotKey) {
    const top = topFromMap(countBy(rows, lotKey), 1)[0];
    if (top) {
      insights.push({
        id: "lot",
        title: "Lotería dominante",
        body: `${top.label} lidera con ${top.value} coincidencia(s).`,
      });
    }
  }

  if (dateKey) {
    const years = new Map<string, number>();
    let latest: { raw: string; t: number } | null = null;
    for (const r of rows) {
      const y = yearOf(r[dateKey]);
      if (y) years.set(y, (years.get(y) || 0) + 1);
      const raw = str(r[dateKey], "");
      const t = new Date(raw.length <= 10 ? `${raw.slice(0, 10)}T12:00:00` : raw).getTime();
      if (Number.isFinite(t) && (!latest || t > latest.t)) latest = { raw, t };
    }
    const topYear = topFromMap(years, 1)[0];
    if (topYear) {
      insights.push({
        id: "year",
        title: "Año con más coincidencias",
        body: `${topYear.label} concentra ${topYear.value} registro(s).`,
      });
    }
    if (latest) {
      insights.push({
        id: "recent",
        title: "Comportamiento reciente",
        body: `La aparición más reciente fue el ${parseDateLabel(latest.raw)}.`,
      });
    }
    const sortedYears = [...years.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    if (sortedYears.length >= 2) {
      const prev = sortedYears[sortedYears.length - 2][1];
      const last = sortedYears[sortedYears.length - 1][1];
      const delta = last - prev;
      insights.push({
        id: "trend",
        title: "Tendencia",
        body:
          delta > 0
            ? `El último año muestra ${delta} coincidencia(s) más que el anterior.`
            : delta < 0
              ? `El último año muestra ${Math.abs(delta)} coincidencia(s) menos que el anterior.`
              : "La actividad del último año se mantiene estable respecto al anterior.",
      });
    }
  }

  if (subjects.length >= 2) {
    insights.push({
      id: "rel",
      title: "Relación analizada",
      body: `Se evaluó la relación ${subjects.slice(0, 2).join(" → ")} sobre ${rows.length} registro(s).`,
    });
  }

  return insights.slice(0, 6);
}

function buildNarrative(
  content: string,
  rows: Record<string, unknown>[],
  subjects: string[],
  summaryCards: SummaryCardItem[],
  insights: InsightItem[],
): string {
  const fromAi = proseFromContent(content);
  if (fromAi && fromAi.length > 40 && !/^\|/.test(fromAi) && rows.length > 0) {
    // Prefer short analyst prose over raw table dumps
    if (!fromAi.includes("---|") && fromAi.split("\n").length <= 12) {
      return fromAi;
    }
  }

  const parts: string[] = [];
  const matches = summaryCards.find((c) => /coinciden/i.test(c.label))?.value;
  const last = summaryCards.find((c) => /última|ultim/i.test(c.label))?.value;
  const lots = summaryCards.find((c) => /loter/i.test(c.label))?.value;
  const period = summaryCards.find((c) => /per[ií]odo/i.test(c.label))?.value;

  if (subjects.length >= 2 && matches) {
    parts.push(
      `Los números ${subjects[0]} y ${subjects[1]} han coincidido en ${matches} ocasión(es).`,
    );
  } else if (subjects.length === 1 && matches) {
    parts.push(`El número ${subjects[0]} aparece en ${matches} registro(s) analizados.`);
  } else if (rows.length) {
    parts.push(`Se identificaron ${rows.length} registro(s) relevantes para esta consulta.`);
  }

  if (last && last !== "—") {
    parts.push(`La coincidencia más reciente ocurrió el ${last}.`);
  }
  if (insights.find((i) => i.id === "pos")) {
    parts.push(insights.find((i) => i.id === "pos")!.body);
  }
  if (lots && lots !== "—") {
    parts.push(`Estas coincidencias se distribuyen entre ${lots} lotería(s) distinta(s).`);
  }
  if (period && period !== "—") {
    parts.push(`El período analizado abarca ${period}.`);
  }

  if (!parts.length && fromAi) return fromAi;
  if (!parts.length) {
    return "La consulta se completó. Explora el resumen, los gráficos y la tabla para profundizar.";
  }
  return parts.join(" ");
}

function buildCharts(rows: Record<string, unknown>[], columns: string[]) {
  const lotKey = columns.find((c) => /loter/i.test(c));
  const posKey = columns.find((c) => /posici/i.test(c));
  const dateKey = columns.find((c) => /fecha|aparici|date/i.test(c));
  const numKey = columns.find((c) => c === "Número" || /n[uú]mero/i.test(c));
  const countKey = columns.find((c) => /veces|count|aparicion/i.test(c));

  let barChart: ChartDatum[] = [];
  let pieChart: ChartDatum[] = [];
  let ranking: ChartDatum[] = [];
  let yearly: ChartDatum[] = [];
  const timeline: TimelineItem[] = [];
  const heatmap: { row: string; col: string; value: number }[] = [];

  if (lotKey) {
    barChart = topFromMap(countBy(rows, lotKey), 10);
    pieChart = topFromMap(countBy(rows, lotKey), 6);
  } else if (posKey) {
    barChart = topFromMap(countBy(rows, posKey), 10);
    pieChart = barChart.slice(0, 6);
  } else if (numKey && countKey) {
    ranking = rows
      .map((r) => ({
        label: padNum(r[numKey]),
        value: Number(r[countKey]) || 0,
      }))
      .filter((x) => x.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 12);
    barChart = ranking.slice(0, 10);
    pieChart = ranking.slice(0, 6);
  } else if (numKey) {
    barChart = topFromMap(countBy(rows, numKey), 10);
    pieChart = barChart.slice(0, 6);
    ranking = barChart;
  }

  if (dateKey) {
    yearly = topFromMap(
      (() => {
        const m = new Map<string, number>();
        for (const r of rows) {
          const y = yearOf(r[dateKey]);
          if (y) m.set(y, (m.get(y) || 0) + 1);
        }
        return m;
      })(),
      12,
    ).sort((a, b) => a.label.localeCompare(b.label));

    const dated = rows
      .map((r, i) => {
        const raw = str(r[dateKey], "");
        const t = new Date(raw.length <= 10 ? `${raw.slice(0, 10)}T12:00:00` : raw).getTime();
        return { r, i, raw, t };
      })
      .filter((x) => Number.isFinite(x.t))
      .sort((a, b) => b.t - a.t)
      .slice(0, 24);

    for (const d of dated) {
      timeline.push({
        id: `t-${d.i}`,
        date: parseDateLabel(d.raw),
        label: str(d.r[lotKey || "Lotería"] || d.r[numKey || "Número"] || d.r.Resultado || "Registro"),
        meta: posKey ? str(d.r[posKey], "") : undefined,
      });
    }
  }

  if (lotKey && posKey) {
    const map = new Map<string, number>();
    for (const r of rows) {
      const row = str(r[lotKey], "—");
      const col = str(r[posKey], "—");
      const k = `${row}|||${col}`;
      map.set(k, (map.get(k) || 0) + 1);
    }
    for (const [k, value] of map) {
      const [row, col] = k.split("|||");
      heatmap.push({ row, col, value });
    }
    heatmap.sort((a, b) => b.value - a.value);
  }

  if (!ranking.length && barChart.length) ranking = barChart;

  return { barChart, pieChart, ranking, timeline, heatmap, yearly };
}

function buildSummaryCards(
  rows: Record<string, unknown>[],
  columns: string[],
  subjects: string[],
  structured?: Structured | null,
): SummaryCardItem[] {
  const data = asRecord(structured?.data);
  const asset = asRecord(structured?.asset || data.asset);
  const dateKey = columns.find((c) => /fecha|aparici|date/i.test(c));
  const lotKey = columns.find((c) => /loter/i.test(c));
  const posKey = columns.find((c) => /posici/i.test(c));

  const rowCount = Number(asset.row_count ?? structured?.row_count ?? rows.length) || rows.length;

  let lastDate = "—";
  let period = "—";
  if (dateKey && rows.length) {
    const times: number[] = [];
    for (const r of rows) {
      const raw = str(r[dateKey], "");
      const t = new Date(raw.length <= 10 ? `${raw.slice(0, 10)}T12:00:00` : raw).getTime();
      if (Number.isFinite(t)) times.push(t);
    }
    if (times.length) {
      times.sort((a, b) => a - b);
      lastDate = parseDateLabel(new Date(times[times.length - 1]).toISOString());
      const y0 = new Date(times[0]).getFullYear();
      const y1 = new Date(times[times.length - 1]).getFullYear();
      period = y0 === y1 ? String(y0) : `${y0}–${y1}`;
    }
  }

  const lotteries = lotKey ? countBy(rows, lotKey).size : 0;
  const cards: SummaryCardItem[] = [
    { id: "matches", value: String(rowCount), label: "Coincidencias" },
    { id: "last", value: lastDate, label: "Última aparición" },
    {
      id: "lots",
      value: lotteries ? String(lotteries) : str(data.lotteries_count ?? "—"),
      label: "Loterías",
    },
    { id: "period", value: period, label: "Período" },
  ];

  if (subjects.length >= 2) {
    cards.push({
      id: "rel",
      value: `${subjects[0]} → ${subjects[1]}`,
      label: "Relación analizada",
    });
  } else if (subjects.length === 1) {
    cards.push({ id: "rel", value: subjects[0], label: "Número analizado" });
  }

  if (posKey) {
    const top = topFromMap(countBy(rows, posKey), 2);
    if (top[0]) {
      cards.push({
        id: "pos",
        value: top.map((t) => t.label).slice(0, 2).join(" · "),
        label: "Posiciones frecuentes",
        hint: subjects[0] ? `${subjects[0]} → ${top[0].label}` : undefined,
      });
    }
  }

  return cards;
}

export function buildAnalysisPresentation(opts: {
  content: string;
  structured?: Structured | null;
  query?: string;
  activeContext?: LotteryChatSendResponse["active_context"];
  toolTrace?: LotteryChatSendResponse["message"]["tool_trace"];
  latencyMs?: number | null;
  sessionContext?: Record<string, unknown> | null;
}): AnalysisPresentation {
  const { content, structured, query = "", activeContext, toolTrace, latencyMs, sessionContext } =
    opts;
  const type = structured?.type || "";
  const isError =
    type === "lottery_error" || type === "lottery_ambiguity" || type === "lottery_no_results";
  const errorMessages = (structured?.warnings || []).map((w) => w.message);

  const { columns, rows, downloadUrl, downloadFilename } = extractRowsColumns(structured);
  const subjects = detectSubjects(structured, activeContext, query);
  let summaryCards = isError ? [] : buildSummaryCards(rows, columns, subjects, structured);
  if (!isError && !summaryCards.length) {
    const prose = proseFromContent(content);
    summaryCards = [
      {
        id: "status",
        value: rows.length ? String(rows.length) : "Listo",
        label: rows.length ? "Registros" : "Estado",
      },
      {
        id: "type",
        value: investigationLabel(type, activeContext),
        label: "Tipo",
      },
      {
        id: "subjects",
        value: subjects.join(" · ") || "—",
        label: "Sujetos",
      },
      {
        id: "preview",
        value: prose ? prose.slice(0, 42) + (prose.length > 42 ? "…" : "") : "—",
        label: "Lectura rápida",
      },
    ];
  }
  const insights = isError ? [] : buildInsights(rows, columns, subjects);
  const narrative = isError
    ? errorMessages.join(" ") || proseFromContent(content) || "No hay resultados para mostrar."
    : buildNarrative(content, rows, subjects, summaryCards, insights);
  const charts = isError
    ? { barChart: [], pieChart: [], ranking: [], timeline: [], heatmap: [], yearly: [] }
    : buildCharts(rows, columns);

  const data = asRecord(structured?.data);
  const asset = asRecord(structured?.asset || data.asset);
  const filters = asRecord(asset.filters || data.filters);
  const activeFilters = Object.entries(filters)
    .filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`);
  if (activeContext?.filters_label) activeFilters.unshift(String(activeContext.filters_label));

  const sqlMs =
    toolTrace?.find((t) => /sql|query|db|workspace/i.test(t.tool))?.duration_ms ?? null;
  const aiMs =
    toolTrace?.find((t) => /ai|llm|synth|hermes|prompt/i.test(t.tool))?.duration_ms ?? null;
  const totalTrace = toolTrace?.reduce((a, t) => a + (Number(t.duration_ms) || 0), 0) ?? null;

  const ctx = sessionContext || {};
  const v4 = asRecord(ctx.conversation_v4);
  const runtime = asRecord(v4.prompt_runtime || ctx.prompt_runtime || data.prompt_runtime);
  const studio = asRecord(v4.prompt_studio || ctx.prompt_studio || data.prompt_studio);

  const title =
    subjects.length >= 2
      ? `Coincidencias entre ${subjects[0]} y ${subjects[1]}`
      : subjects.length === 1
        ? `Análisis del ${subjects[0]}`
        : str(asset.title || data.title || investigationLabel(type, activeContext));

  return {
    title,
    summaryCards,
    narrative,
    insights,
    columns,
    rows,
    ...charts,
    downloadUrl,
    downloadFilename,
    isError,
    errorMessages,
    meta: {
      query,
      subjects,
      investigationType: investigationLabel(type, activeContext),
      activeFilters,
      recordCount: Number(asset.row_count ?? structured?.row_count ?? rows.length) || rows.length,
      workspace: str(asset.workspace || data.workspace || v4.workspace || null, "") || null,
      provider: str(runtime.provider || v4.provider || data.provider || null, "") || null,
      model: str(runtime.model || v4.model || data.model || null, "") || null,
      sqlMs,
      aiMs,
      totalMs: latencyMs ?? totalTrace,
      promptRuntime: str(runtime.version || runtime.name || null, "") || null,
      promptStudioVersion: str(studio.version || studio.name || null, "") || null,
      promptHash: str(runtime.hash || studio.hash || data.prompt_hash || null, "") || null,
    },
  };
}

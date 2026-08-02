/**
 * Single adapter: live Lottery chat / investigation workspace → UX 2.0 view model.
 * All payload normalization lives here — not in UI components.
 */

import {
  buildAnalysisPresentation,
  type AnalysisPresentation,
  type Structured,
} from "@/lib/lottery-ux-present";
import type { LotteryChatSendResponse } from "@/lib/lottery";

/** Technical column → human label */
export const HUMAN_COLUMNS: Record<string, string> = {
  fecha: "Fecha",
  loteria: "Lotería",
  loteria_a: "Lotería A",
  loteria_b: "Lotería B",
  numero_a: "Número A",
  posicion_a: "Posición A",
  numero_b: "Número B",
  posicion_b: "Posición B",
  tipo_coincidencia: "Tipo de coincidencia",
  posicion_a_num: "Posición A (núm.)",
  posicion_b_num: "Posición B (núm.)",
  date: "Fecha",
  lottery: "Lotería",
  number: "Número",
  position: "Posición",
  position_label: "Posición",
  result: "Resultado",
};

const HIDDEN_TECH_COLUMNS = new Set([
  "posicion_a_num",
  "posicion_b_num",
  "loteria_a",
  "loteria_b",
  "source_query_hash",
  "evidence_hash",
]);

const HUMAN_VALUES: Record<string, string> = {
  misma_loteria: "Misma lotería",
  misma_fecha: "Misma fecha",
  same_day: "Mismo día",
  same_lottery: "Misma lotería",
  same_position: "Misma posición",
};

const DISPLAY_COLUMNS = [
  "Fecha",
  "Lotería",
  "Número A",
  "Posición A",
  "Número B",
  "Posición B",
  "Tipo de coincidencia",
];

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

function asArray(v: unknown): Record<string, unknown>[] {
  return Array.isArray(v)
    ? (v.filter((x) => x && typeof x === "object") as Record<string, unknown>[])
    : [];
}

function humanLabel(col: string): string {
  if (HUMAN_COLUMNS[col]) return HUMAN_COLUMNS[col];
  if (/^[A-ZÁÉÍÓÚÑ]/.test(col) && !col.includes("_")) return col;
  return col
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bA\b/g, "A")
    .replace(/\bB\b/g, "B");
}

function humanCell(value: unknown, col?: string): string {
  if (value == null || value === "") return "";
  const s = String(value);
  if (HUMAN_VALUES[s]) return HUMAN_VALUES[s];
  if (col && /tipo|relation/i.test(col) && HUMAN_VALUES[s.toLowerCase()]) {
    return HUMAN_VALUES[s.toLowerCase()];
  }
  return s;
}

/** Strip markdown tables / technical dumps from assistant prose. */
export function stripTechnicalMarkdown(text: string): string {
  if (!text) return "";
  const lines = text.split("\n");
  const kept: string[] = [];
  let inTable = false;
  for (const line of lines) {
    const t = line.trim();
    if (/^\|/.test(t) || /^\|?\s*:?-{3,}/.test(t) || /\|\s*-{3,}/.test(t)) {
      inTable = true;
      continue;
    }
    if (inTable && !t) {
      inTable = false;
      continue;
    }
    if (inTable) continue;
    // Drop lines that expose technical field names
    if (
      /\b(posicion_a_num|numero_a|misma_fecha|misma_loteria|tipo_coincidencia)\b/i.test(t) &&
      (t.includes("|") || /Orden:|Filtros activos:|fila\(s\)/i.test(t))
    ) {
      continue;
    }
    if (/^Orden:\s*\w+_/.test(t)) continue;
    if (/^Filtros activos:\s*\{/.test(t)) continue;
    if (/^Descarga:\s*\/api\//i.test(t)) continue;
    kept.push(line);
  }
  return kept
    .join("\n")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function humanizeAssetRows(
  columns: string[],
  rows: Record<string, unknown>[],
): { columns: string[]; rows: Record<string, unknown>[] } {
  const visible = columns.filter((c) => !HIDDEN_TECH_COLUMNS.has(c));
  const mappedCols = visible.map(humanLabel);
  // Prefer canonical display order when same-day asset
  const isSameDay =
    visible.includes("fecha") &&
    visible.includes("numero_a") &&
    visible.includes("numero_b");
  const finalCols = isSameDay
    ? DISPLAY_COLUMNS.filter((c) => mappedCols.includes(c) || c === "Lotería")
    : mappedCols;

  const keyByHuman = new Map(visible.map((c) => [humanLabel(c), c]));
  const outRows = rows.map((r) => {
    const o: Record<string, unknown> = {};
    for (const h of finalCols.length ? finalCols : mappedCols) {
      const rawKey = keyByHuman.get(h) || h;
      o[h] = humanCell(r[rawKey] ?? r[h], rawKey);
    }
    return o;
  });
  return { columns: finalCols.length ? finalCols : mappedCols, rows: outRows };
}

/** Expand lottery_result items (date + appearances) into tabular rows. */
function expandCoincidenceItems(
  items: Record<string, unknown>[],
  subjects: string[],
): { columns: string[]; rows: Record<string, unknown>[] } {
  const rows: Record<string, unknown>[] = [];
  for (const it of items) {
    const date = String(it.date || it.fecha || "");
    const apps = asArray(it.appearances);
    if (!apps.length) {
      rows.push({
        Fecha: date,
        Lotería: String(it.lottery || it.loteria || ""),
        "Número A": subjects[0] || "",
        "Posición A": "",
        "Número B": subjects[1] || "",
        "Posición B": "",
        "Tipo de coincidencia": "Mismo día",
      });
      continue;
    }
    const byNum = new Map(apps.map((a) => [String(a.number ?? "").padStart(2, "0"), a]));
    const a = byNum.get(String(subjects[0] || "").padStart(2, "0")) || apps[0];
    const b =
      byNum.get(String(subjects[1] || "").padStart(2, "0")) ||
      apps.find((x) => x !== a) ||
      apps[1] ||
      {};
    const lotA = String(a.lottery || "");
    const lotB = String(b.lottery || "");
    rows.push({
      Fecha: date,
      Lotería: lotA && lotB && lotA !== lotB ? `${lotA} / ${lotB}` : lotA || lotB,
      "Número A": String(a.number ?? subjects[0] ?? "").padStart(2, "0"),
      "Posición A": String(a.position_label || a.position || ""),
      "Número B": String(b.number ?? subjects[1] ?? "").padStart(2, "0"),
      "Posición B": String(b.position_label || b.position || ""),
      "Tipo de coincidencia":
        lotA && lotB && lotA === lotB ? "Misma lotería" : "Misma fecha",
    });
  }
  return { columns: DISPLAY_COLUMNS, rows };
}

function briefNarrative(opts: {
  content: string;
  subjects: string[];
  rowCount: number;
  filters: Record<string, unknown>;
  sort?: Record<string, unknown> | null;
  relation?: string | null;
}): string {
  const clean = stripTechnicalMarkdown(opts.content);
  // Prefer a short human paragraph when we have structured counts
  if (opts.rowCount > 0 && opts.subjects.length >= 2) {
    const parts: string[] = [];
    parts.push(
      `Los números ${opts.subjects[0]} y ${opts.subjects[1]} tienen ${opts.rowCount} coincidencia(s) registradas` +
        (opts.relation === "same_day" || opts.relation === "mismo día"
          ? " el mismo día."
          : "."),
    );
    const lot = opts.filters.lottery;
    if (lot) parts.push(`Filtro activo: lotería «${lot}».`);
    const sortField = opts.sort?.field ? humanLabel(String(opts.sort.field)) : null;
    const sortDir = opts.sort?.direction === "asc" ? "ascendente" : "descendente";
    if (sortField) parts.push(`Orden: ${sortField} (${sortDir}).`);
    // Keep one short sentence from AI if useful and non-technical
    const first = clean
      .split(/\n{2,}/)
      .map((p) => p.replace(/\n/g, " ").trim())
      .find((p) => p.length > 40 && !/fila\(s\)/i.test(p) && !/Ordené por/i.test(p));
    if (first && first.length < 280 && !/_/.test(first)) {
      parts.push(first);
    }
    return parts.join(" ");
  }
  if (clean) {
    const paras = clean
      .split(/\n{2,}/)
      .map((p) => p.replace(/\n/g, " ").trim())
      .filter((p) => p.length > 20)
      .slice(0, 3);
    return paras.join(" ") || clean.slice(0, 500);
  }
  return "Consulta completada. Explora el resumen, los gráficos y la tabla.";
}

export type AnalysisViewModel = AnalysisPresentation & {
  hasStructuredAsset: boolean;
  suppressMarkdown: boolean;
  workspaceActionHints: {
    filterLottery?: string;
    sortRecent?: boolean;
    exportExcel?: boolean;
    nextPage?: boolean;
    breakdownPositions?: boolean;
  };
  rawDownloadUrl?: string | null;
  pagination?: { page: number; pageSize: number; totalPages: number } | null;
  filters?: Record<string, unknown>;
  sort?: Record<string, unknown> | null;
  suggestions: string[];
};

/**
 * Map a live chat send/retry response (or message slice) into UX 2.0 view model.
 */
export function mapLotteryChatResponseToAnalysisViewModel(input: {
  response?: LotteryChatSendResponse | null;
  content?: string;
  structured?: Structured | null;
  query?: string;
  activeContext?: LotteryChatSendResponse["active_context"];
  toolTrace?: LotteryChatSendResponse["message"]["tool_trace"];
  latencyMs?: number | null;
  sessionContext?: Record<string, unknown> | null;
  suggestions?: string[];
}): AnalysisViewModel {
  const res = input.response;
  const message = res?.message;
  const content = input.content ?? message?.content ?? "";
  const structured = (input.structured ?? message?.structured_content ?? null) as Structured | null;
  const activeContext = input.activeContext ?? res?.active_context ?? null;
  const toolTrace = input.toolTrace ?? message?.tool_trace;
  const latencyMs = input.latencyMs ?? res?.latency_ms ?? null;
  const sessionContext = input.sessionContext ?? (res?.context as Record<string, unknown>) ?? null;
  const suggestions = input.suggestions ?? res?.suggestions ?? [];

  const data = asRecord(structured?.data);
  const asset = asRecord(structured?.asset || data.asset);
  const type = structured?.type || "";

  const isWorkspace =
    type === "investigation_workspace_table" || type === "investigation_workspace_export";

  let subjects: string[] =
    (Array.isArray(asset.subjects) ? asset.subjects.map(String) : []) ||
    (Array.isArray(data.numbers) ? data.numbers.map(String) : []) ||
    [];
  if (!subjects.length && activeContext?.numbers?.length) {
    subjects = activeContext.numbers.map((n) => String(n).padStart(2, "0"));
  } else {
    subjects = subjects.map((s) => String(s).padStart(2, "0"));
  }

  const filters = asRecord(asset.filters || data.filters);
  const sort = (asset.sort || data.sort || null) as Record<string, unknown> | null;
  const paginationRaw = asRecord(asset.pagination || data.pagination);
  const pagination =
    paginationRaw.page != null
      ? {
          page: Number(paginationRaw.page) || 1,
          pageSize: Number(paginationRaw.page_size || paginationRaw.pageSize) || 20,
          totalPages: Number(paginationRaw.total_pages || paginationRaw.totalPages) || 1,
        }
      : null;

  let columns: string[] = [];
  let rows: Record<string, unknown>[] = [];
  let rowCount = 0;
  let downloadUrl =
    (structured?.download_url as string | undefined) ||
    (asset.download_url as string | undefined) ||
    null;
  let downloadFilename =
    (structured?.filename as string | undefined) ||
    (asset.export_filename as string | undefined) ||
    null;

  if (isWorkspace) {
    const rawCols = (asset.columns as string[] | undefined) || [];
    const rawRows = asArray(asset.rows);
    const human = humanizeAssetRows(rawCols, rawRows);
    columns = human.columns;
    rows = human.rows;
    rowCount = Number(asset.row_count ?? structured?.row_count ?? rows.length) || rows.length;
  } else if (
    type === "lottery_result" &&
    asArray(data.items).length &&
    asArray(data.items)[0]?.appearances != null
  ) {
    const expanded = expandCoincidenceItems(asArray(data.items), subjects);
    columns = expanded.columns;
    rows = expanded.rows;
    rowCount = Number(data.total ?? rows.length) || rows.length;
  }

  // Build a normalized structured payload for the presentation builder
  const normalizedStructured: Structured | null = structured
    ? {
        ...structured,
        type: isWorkspace || rows.length ? "investigation_workspace_table" : structured.type,
        data: {
          ...data,
          title:
            asset.title ||
            (subjects.length >= 2
              ? `Coincidencias entre ${subjects[0]} y ${subjects[1]}`
              : data.title),
        },
        asset: {
          ...asset,
          title:
            asset.title ||
            (subjects.length >= 2
              ? `Coincidencias entre ${subjects[0]} y ${subjects[1]}`
              : "Resultados"),
          columns,
          rows,
          row_count: rowCount || Number(asset.row_count || data.total || 0),
          subjects,
          relation: asset.relation || data.relation || activeContext?.relation || null,
          filters,
          sort: sort || undefined,
          pagination: paginationRaw,
          download_url: downloadUrl,
          export_filename: downloadFilename,
          workspace: "investigation",
        },
        download_url: downloadUrl || undefined,
        filename: downloadFilename || undefined,
        row_count: rowCount || undefined,
      }
    : null;

  const base = buildAnalysisPresentation({
    content: stripTechnicalMarkdown(content),
    structured: normalizedStructured,
    query: input.query,
    activeContext,
    toolTrace,
    latencyMs,
    sessionContext,
  });

  // Override with humanized rows/columns and brief narrative
  if (columns.length && rows.length) {
    base.columns = columns;
    base.rows = rows;
  }
  base.meta.recordCount = rowCount || base.meta.recordCount;
  base.meta.subjects = subjects.length ? subjects : base.meta.subjects;
  base.meta.investigationType =
    (asset.relation as string) === "same_day" || data.relation === "same_day"
      ? "Coincidencias el mismo día"
      : base.meta.investigationType;
  base.meta.workspace = "investigation";
  base.meta.activeFilters = Object.entries(filters)
    .filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `${humanLabel(k)}: ${humanCell(v, k)}`);
  if (activeContext?.filters_label) {
    base.meta.activeFilters = [
      String(activeContext.filters_label),
      ...base.meta.activeFilters.filter((x) => x !== activeContext.filters_label),
    ];
  }

  if (subjects.length >= 2) {
    base.title = `Coincidencias entre ${subjects[0]} y ${subjects[1]}`;
    base.meta.subjects = subjects;
  } else if (subjects.length === 1) {
    base.title = `Análisis del ${subjects[0]}`;
    base.meta.subjects = subjects;
  }

  base.narrative = briefNarrative({
    content,
    subjects: base.meta.subjects,
    rowCount: base.meta.recordCount,
    filters,
    sort,
    relation: String(asset.relation || data.relation || activeContext?.relation || ""),
  });

  // Ensure summary cards use live totals
  if (base.meta.recordCount > 0) {
    const cards = [...base.summaryCards];
    const idx = cards.findIndex((c) => /coinciden|registro/i.test(c.label));
    if (idx >= 0) cards[idx] = { ...cards[idx], value: String(base.meta.recordCount) };
    base.summaryCards = cards;
  }

  // Rebuild charts from humanized rows if we have them
  if (rows.length) {
    const rebuilt = buildAnalysisPresentation({
      content: base.narrative,
      structured: normalizedStructured,
      query: input.query,
      activeContext,
      toolTrace,
      latencyMs,
      sessionContext,
    });
    base.barChart = rebuilt.barChart;
    base.pieChart = rebuilt.pieChart;
    base.ranking = rebuilt.ranking;
    base.timeline = rebuilt.timeline;
    base.heatmap = rebuilt.heatmap;
    base.yearly = rebuilt.yearly;
    base.insights = rebuilt.insights.length ? rebuilt.insights : base.insights;
    base.summaryCards = rebuilt.summaryCards.length ? rebuilt.summaryCards : base.summaryCards;
    base.narrative = briefNarrative({
      content,
      subjects: base.meta.subjects,
      rowCount: base.meta.recordCount,
      filters,
      sort,
      relation: String(asset.relation || data.relation || ""),
    });
  }

  base.downloadUrl = downloadUrl;
  base.downloadFilename = downloadFilename;

  const hasStructuredAsset =
    isWorkspace ||
    (type === "lottery_result" && rowCount > 0) ||
    Boolean(columns.length && rows.length);

  return {
    ...base,
    hasStructuredAsset,
    suppressMarkdown: hasStructuredAsset || Boolean(structured && type !== "lottery_error"),
    workspaceActionHints: {
      filterLottery: "Loteka",
      sortRecent: true,
      exportExcel: true,
      nextPage: Boolean(pagination && pagination.page < pagination.totalPages),
      breakdownPositions: true,
    },
    rawDownloadUrl: downloadUrl,
    pagination,
    filters,
    sort,
    suggestions,
  };
}

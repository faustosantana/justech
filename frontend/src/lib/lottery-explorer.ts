/** Lottery IA Explorer — types, cache, action helpers. */

export type ExplorerView =
  | "root"
  | "analizar"
  | "tabla1"
  | "tabla2"
  | "companeros"
  | "vecinos"
  | "historico"
  | "coincidencias"
  | "estadisticas"
  | "comparar"
  | "relacion"
  | string;

export type ExplorerCrumb = {
  id: string;
  label: string;
  number?: string | null;
  view?: ExplorerView;
  at?: string;
};

export type ExplorerNav = {
  stack?: ExplorerCrumb[];
  index?: number;
  current?: ExplorerCrumb | null;
  breadcrumbs?: ExplorerCrumb[];
  compare?: string[];
  favorites?: string[];
  recent_numbers?: string[];
  origin?: string | null;
  view?: ExplorerView;
  started_at?: string | null;
  can_back?: boolean;
  can_forward?: boolean;
};

export type NumberCard = {
  number: number;
  label: string;
  table1: { code: number | null; companions: number[]; companions_count: number };
  table2: { code: number | null; neighbors: number[]; neighbors_count: number };
  actions?: string[];
  source?: string;
  cached?: boolean;
};

export type CompareBoard = {
  numbers: number[];
  cards: NumberCard[];
  dimensions?: string[];
};

export type TableExplorerPayload = {
  table: string;
  table_key: string;
  rows: Array<{
    number: number;
    code: number;
    group_numbers: number[];
    formula?: string;
    interactive?: boolean;
  }>;
  row_count: number;
};

export type ExplorerAction =
  | "focus"
  | "analizar"
  | "comparar"
  | "toggle_compare"
  | "toggle_favorite"
  | "tabla1"
  | "tabla2"
  | "companeros"
  | "vecinos"
  | "historico"
  | "coincidencias"
  | "estadisticas"
  | "abrir_investigacion"
  | "back"
  | "forward"
  | "breadcrumb"
  | "relacion";

const cardCache = new Map<number, NumberCard>();
const tableCache = new Map<string, TableExplorerPayload>();

export function getCachedCard(n: number): NumberCard | undefined {
  return cardCache.get(n);
}

export function setCachedCard(card: NumberCard): void {
  cardCache.set(card.number, card);
}

export function getCachedTable(key: string): TableExplorerPayload | undefined {
  return tableCache.get(key);
}

export function setCachedTable(payload: TableExplorerPayload): void {
  tableCache.set(payload.table_key || payload.table, payload);
}

export function formatAnalyzingDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

export function formatStartedAt(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-DO", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export const NUMBER_ACTIONS: { id: ExplorerAction; label: string; chat?: boolean }[] = [
  { id: "analizar", label: "Analizar", chat: true },
  { id: "toggle_compare", label: "Comparar" },
  { id: "tabla1", label: "Tabla 1" },
  { id: "tabla2", label: "Tabla 2" },
  { id: "companeros", label: "Compañeros", chat: true },
  { id: "vecinos", label: "Vecinos", chat: true },
  { id: "historico", label: "Histórico", chat: true },
  { id: "coincidencias", label: "Coincidencias", chat: true },
  { id: "estadisticas", label: "Estadísticas", chat: true },
  { id: "abrir_investigacion", label: "Abrir investigación" },
];

export function smartActionButtons(content: string, number?: string | number | null) {
  const t = (content || "").toLowerCase();
  const n = number != null ? String(number) : null;
  const buttons: { id: ExplorerAction; label: string }[] = [];
  if (/compa[nñ]ero/.test(t) || /tabla\s*1/.test(t)) {
    buttons.push({ id: "companeros", label: "Ver compañeros" });
    buttons.push({ id: "tabla1", label: "Ir a Tabla 1" });
  }
  if (/vecino/.test(t) || /tabla\s*2/.test(t)) {
    buttons.push({ id: "vecinos", label: "Explorar vecinos" });
    buttons.push({ id: "tabla2", label: "Ir a Tabla 2" });
  }
  if (/compa[nñ]ero/.test(t)) {
    buttons.push({ id: "toggle_compare", label: "Compararlos" });
  }
  if (/hist[oó]rico|salida/.test(t)) {
    buttons.push({ id: "historico", label: "Ver histórico" });
  }
  if (!buttons.length && n) {
    buttons.push(
      { id: "companeros", label: "Ver compañeros" },
      { id: "vecinos", label: "Explorar vecinos" },
      { id: "tabla1", label: "Ir a Tabla 1" },
      { id: "tabla2", label: "Ir a Tabla 2" },
      { id: "historico", label: "Ver histórico" },
    );
  }
  // dedupe
  const seen = new Set<string>();
  return buttons.filter((b) => {
    if (seen.has(b.id)) return false;
    seen.add(b.id);
    return true;
  });
}

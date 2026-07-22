/** Feature flag Fase 1 — auto contexto al abrir expediente DGCP. */
export function isDgcpAutoExpedienteContextEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_DGCP_AUTO_EXPEDIENTE_CONTEXT;
  if (raw === undefined || raw === "") return true;
  return raw === "1" || raw.toLowerCase() === "true";
}

export interface DGCPCommercialSimilarItem {
  id: string;
  document_type: string;
  document_number?: string | null;
  product_name?: string | null;
  customer_name?: string | null;
  unit_price?: string | null;
  currency?: string | null;
  date?: string | null;
  salesperson?: string | null;
  margin?: string | null;
  margin_pct?: string | null;
  relevance_score?: number;
}

export interface DGCPCommercialContextPayload {
  query: string;
  total: number;
  index_available: boolean;
  message?: string | null;
  quotes: DGCPCommercialSimilarItem[];
  sales: DGCPCommercialSimilarItem[];
  last_sold_price?: string | null;
  avg_sold_price?: string | null;
  min_price?: string | null;
  max_price?: string | null;
  currency?: string | null;
}

export function normalizeDGCPCommercialContextPayload(
  raw: DGCPCommercialContextPayload | null | undefined,
): DGCPCommercialContextPayload | null {
  if (!raw) return null;
  return {
    query: raw.query ?? "",
    total: Number.isFinite(raw.total) ? raw.total : 0,
    index_available: Boolean(raw.index_available),
    message: raw.message ?? null,
    quotes: Array.isArray(raw.quotes) ? raw.quotes : [],
    sales: Array.isArray(raw.sales) ? raw.sales : [],
    last_sold_price: raw.last_sold_price ?? null,
    avg_sold_price: raw.avg_sold_price ?? null,
    min_price: raw.min_price ?? null,
    max_price: raw.max_price ?? null,
    currency: raw.currency ?? "DOP",
  };
}

export interface DGCPExpedienteContextResponse {
  enabled: boolean;
  opportunity_id: string;
  bootstrap_at: string | null;
  historical_status: string;
  historical_message: string | null;
  historical: import("@/lib/dgcp").DGCPHistoricalSimilarResponse | null;
  commercial_status: string;
  commercial_message: string | null;
  commercial: DGCPCommercialContextPayload | null;
  error_message: string | null;
}

export interface DGCPExpedienteContextState {
  enabled: boolean;
  loading: boolean;
  phase: "idle" | "loading" | "ready" | "error";
  statusMessage: string;
  lastUpdated: string | null;
  historicalStatus: string;
  historicalMessage: string | null;
  historical: import("@/lib/dgcp").DGCPHistoricalSimilarResponse | null;
  commercialStatus: string;
  commercialMessage: string | null;
  commercial: DGCPCommercialContextPayload | null;
  errorMessage: string | null;
  refresh: (force?: boolean) => Promise<void>;
}

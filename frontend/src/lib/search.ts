export interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  source: string;
  url: string;
  company?: string | null;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResultGroup {
  type: string;
  label: string;
  count: number;
  items: SearchResultItem[];
}

export interface EnterpriseSearchResponse {
  query: string;
  total: number;
  groups: SearchResultGroup[];
  sources_searched: string[];
  future_sources: string[];
  cache_hit?: boolean;
  index_hit?: boolean;
  latency_ms?: number | null;
  resolved_entities?: ResolvedEntity[];
  expanded_terms?: string[];
  knowledge_graph?: KnowledgeGraphPayload;
  search_mode?: string;
}

export interface ResolvedEntity {
  entity_id: string;
  entity_type: string;
  canonical_name: string;
  matched_alias: string;
  match_kind: string;
  confidence: number;
  aliases: string[];
}

export interface KnowledgeGraphPayload {
  nodes: Array<{ id: string; label: string; type: string; module?: string; count?: number; url?: string }>;
  edges: Array<{ from: string; to: string; relation: string }>;
  summary: Record<string, number>;
}

export type KnowledgeEngineResponse = EnterpriseSearchResponse;

export interface SearchAnalyticsSummary {
  total_queries: number;
  avg_latency_ms: number;
  cache_hit_ratio: number;
  index_hit_ratio: number;
}

export interface SearchAnalyticsResponse {
  days: number;
  summary: SearchAnalyticsSummary;
  top_queries: Array<{ query: string; count: number; avg_latency_ms: number }>;
}

export const SOURCE_LABELS: Record<string, string> = {
  odoo: "Odoo",
  dgcp: "DGCP",
  jaios: "JAIOS",
  documents: "Documentos",
  m365: "Microsoft 365",
};

export const TYPE_LABELS: Record<string, string> = {
  customers: "Clientes",
  products: "Productos",
  invoices: "Facturas",
  quotations: "Cotizaciones",
  opportunities: "Oportunidades",
  vendors: "Proveedores",
  projects: "Proyectos",
  tasks: "Tareas",
  notifications: "Notificaciones",
  dgcp: "Licitaciones DGCP",
  documents: "Documentos",
  document: "Documentos",
};

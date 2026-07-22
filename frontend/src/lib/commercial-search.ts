export interface CommercialSearchItem {
  id: string;
  source_system: string;
  source_model: string;
  source_id: number;
  company_id?: number | null;
  document_type: string;
  document_number?: string | null;
  document_status?: string | null;
  customer_id?: number | null;
  customer_name?: string | null;
  customer_rnc?: string | null;
  product_id?: number | null;
  product_name?: string | null;
  sku?: string | null;
  brand?: string | null;
  model?: string | null;
  description?: string | null;
  quantity?: string | null;
  unit_price?: string | null;
  total?: string | null;
  currency?: string | null;
  date?: string | null;
  salesperson?: string | null;
  supplier_name?: string | null;
  margin?: string | null;
  margin_pct?: string | null;
  relevance_score: number;
  odoo_url?: string | null;
}

export interface CommercialSearchResponse {
  query: string;
  intent?: string | null;
  target_category?: string | null;
  total: number;
  items: CommercialSearchItem[];
  index_available: boolean;
  message?: string | null;
}

export interface CommercialPriceHistoryResponse {
  items: Array<{
    id: string;
    product_name?: string | null;
    sku?: string | null;
    brand?: string | null;
    customer_name?: string | null;
    unit_price?: string | null;
    currency?: string | null;
    date?: string | null;
    document_number?: string | null;
    document_type?: string | null;
    margin?: string | null;
    salesperson?: string | null;
    source_model: string;
    source_id: number;
  }>;
  total: number;
  min_price?: string | null;
  max_price?: string | null;
  avg_price?: string | null;
}

export interface CommercialSyncResponse {
  status: string;
  started_at: string;
  finished_at?: string | null;
  results: Array<{ model: string; indexed: number; error?: string | null }>;
  aggregates_rebuilt: boolean;
  message?: string | null;
}

export interface CommercialSyncStatusResponse {
  models: Array<{
    model: string;
    watermark?: string | null;
    last_run_at?: string | null;
    records_indexed: number;
    last_error?: string | null;
  }>;
  total_items: number;
  total_documents: number;
  last_sync_at?: string | null;
}

/** Tipos — Price Intelligence Engine v2 */

export interface PriceProduct {
  id: string;
  supplier: string | null;
  manufacturer: string | null;
  brand: string | null;
  sku: string | null;
  mpn: string | null;
  model: string | null;
  description: string | null;
  category: string | null;
  product_type: string;
  excluded_from_laptop?: boolean;
  is_cotizable?: boolean;
  price_review_status?: string;
  classification_label?: string;
  stock_source_column?: string | null;
  processor: string | null;
  ram_gb: number | null;
  storage_gb: number | null;
  storage_type: string | null;
  display: string | null;
  operating_system: string | null;
  price: string | null;
  preferred_price: string | null;
  preferred_price_field: string | null;
  price_regular: string | null;
  price_rebate: string | null;
  price_discount: string | null;
  prices_original: Record<string, unknown>;
  currency: string;
  stock: number | null;
  in_transit: number | null;
  stock_text_original: string | null;
  warranty: string | null;
  source_filename: string;
  source_sheet: string | null;
  source_row: number | null;
  source_file_date: string | null;
  source_file_date_estimated: boolean;
  file_id: string;
  indexed_at: string;
}

export interface PriceProductDetail extends PriceProduct {
  raw_row_json: Record<string, unknown>;
  raw_columns_json: Array<{ column: string; index: number; value: unknown }>;
  comparison_price_label: string;
  cotizable_warning?: string | null;
}

export interface PriceSearchResponse {
  query: string | null;
  total: number;
  items: PriceProduct[];
}

export interface PriceCompareAlternative {
  supplier: string | null;
  brand: string | null;
  description: string | null;
  sku: string | null;
  price: string | null;
  preferred_price: string | null;
  currency: string;
  stock: number | null;
  source_filename: string;
  source_sheet: string | null;
  source_row: number | null;
  file_date: string | null;
  file_date_estimated: boolean;
}

export interface PriceCompareResponse {
  question: string;
  best_supplier: string | null;
  best_product: PriceProduct | null;
  alternatives: PriceCompareAlternative[];
  warnings: string[];
  summary: string;
}

export interface PriceSearchParams {
  q?: string;
  marca?: string;
  proveedor?: string;
  fabricante?: string;
  categoria?: string;
  tipo_producto?: string;
  ram_gb?: number;
  almacenamiento_gb?: number;
  procesador?: string;
  pantalla?: string;
  sistema_operativo?: string;
  precio_min?: number;
  precio_max?: number;
  moneda?: string;
  stock_min?: number;
  stock_disponible?: boolean;
  solo_disponibles?: boolean;
  limit?: number;
}

export interface PriceQuoteDraft {
  id: string;
  product_id: string;
  task_id?: string | null;
  client_name: string | null;
  quantity: number;
  description: string | null;
  cost_price: string | null;
  currency: string;
  supplier: string | null;
  margin_percent: string | null;
  sale_price_suggested: string | null;
  source_filename: string | null;
  source_sheet: string | null;
  source_row: number | null;
  source_file_date: string | null;
  status: string;
  copy_line: string | null;
}

export interface PriceOdooMatch {
  found: boolean;
  product_id?: number | null;
  product_name?: string | null;
  message: string;
  action?: string;
  odoo_default_code?: string | null;
}

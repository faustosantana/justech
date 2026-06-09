export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  display_name?: string;
  format: string;
  category: string;
  company: string | null;
  client_name: string | null;
  supplier_name: string | null;
  mime_type: string | null;
  file_size: number;
  tags: string[];
  keywords: string[];
  intelligence: Record<string, unknown>;
  compliance: Record<string, unknown>;
  metadata: Record<string, unknown>;
  valid_from: string | null;
  valid_until: string | null;
  indexed_at: string | null;
  analyzed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
}

export interface DocumentSearchHit {
  document_id: string;
  title: string;
  filename: string;
  page_number: number | null;
  snippet: string;
  score: number;
  category: string | null;
  client_name: string | null;
}

export interface DocumentSearchResponse {
  query: string;
  total: number;
  hits: DocumentSearchHit[];
}

export interface DocumentAlert {
  id: string;
  document_id: string | null;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  is_resolved: boolean;
  created_at: string;
}

export interface DocumentHealth {
  enabled: boolean;
  storage_path: string;
  documents_count: number;
  indexed_count: number;
  alerts_open: number;
  archived_count?: number;
  chunks_count?: number;
  ocr_ready: boolean;
  qdrant_ready: boolean;
  semantic_search_ready: boolean;
}

export interface KnowledgeHealth {
  enabled: boolean;
  source_path: string;
  source_available: boolean;
  assets_count: number;
  entities_count: number;
  alerts_open: number;
  last_sync_at: string | null;
  sync_folders: string[];
  category_counts?: Record<string, number>;
  chunks_count?: number;
}

export interface KnowledgeAssetItem {
  id: string;
  filename: string;
  title: string;
  display_name: string;
  relative_path: string;
  folder_category: string;
  document_type: string;
  repository_category: string;
  repository_category_label: string;
  display_type: string;
  display_status: string;
  sncc_label?: string | null;
  detected_supplier?: string | null;
  requires_vigency?: boolean;
  company_key: string | null;
  vigency_status: string;
  valid_from: string | null;
  valid_until: string | null;
}

export const REPOSITORY_CATEGORY_FILTERS = [
  { id: "", label: "Todas las categorías" },
  { id: "documento_legal", label: "Documentos legales" },
  { id: "datos_empresa", label: "Datos de empresa" },
  { id: "plantilla_formulario", label: "Plantillas/Formularios" },
  { id: "proveedor_lista_precios", label: "Proveedores/Listas" },
  { id: "clientes_cotizaciones", label: "Clientes/Cotizaciones" },
  { id: "ficha_tecnica", label: "Fichas técnicas" },
] as const;

export interface DocumentScanResult {
  scanned: number;
  registered: number;
  skipped: number;
  errors: string[];
}

export const DOCUMENT_CATEGORIES = [
  { id: "", label: "Todas las categorías" },
  { id: "general", label: "General" },
  { id: "legal", label: "Legal" },
  { id: "contrato", label: "Contratos" },
  { id: "factura", label: "Facturas" },
  { id: "licitacion", label: "Licitaciones" },
  { id: "sncc", label: "SNCC" },
  { id: "certificacion_tss", label: "Certificación TSS" },
  { id: "certificacion_dgii", label: "Certificación DGII" },
  { id: "registro_mercantil", label: "Registro Mercantil" },
  { id: "rpe", label: "RPE" },
] as const;

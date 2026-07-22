export interface LegalDocumentItem {
  id: string;
  name: string;
  document_type: string;
  vigency_status: string;
  valid_until?: string | null;
  web_url?: string | null;
  source: string;
}

export interface CompanyLegalSummary {
  company_key: string;
  company_label: string;
  completeness_score: number;
  missing_profile_fields: string[];
  documents: LegalDocumentItem[];
  missing_documents: string[];
  expired_documents: string[];
  upcoming_documents: string[];
}

export interface LegalDocumentsDashboard {
  companies: CompanyLegalSummary[];
  total_documents: number;
  total_expired: number;
  total_missing: number;
}

export interface DgcpTemplateItem {
  id: string;
  name: string;
  source: string;
  document_category?: string | null;
  mime_type?: string | null;
  template_type?: string | null;
  web_url?: string | null;
  parent_path: string;
  fillable_fields_estimate: number;
}

export interface DgcpTemplatesDashboard {
  templates: DgcpTemplateItem[];
  total: number;
  by_category: Record<string, number>;
}

export interface PriceFileItem {
  id: string;
  name: string;
  supplier?: string | null;
  records: number;
  status: string;
  indexed_at?: string | null;
  parent_path: string;
}

export interface PriceIntelligenceDashboard {
  pending_files: PriceFileItem[];
  processed_files: PriceFileItem[];
  total_products: number;
  total_suppliers: number;
  lists_today: number;
  recent_errors: string[];
}

export interface TemplatePreviewField {
  key: string;
  label: string;
  value: string;
  source?: string;
}

export interface TemplatePreview {
  template_type: string;
  template_label: string;
  fields: TemplatePreviewField[];
  missing_fields: string[];
  generate_enabled: boolean;
}

export const COMPANY_OPTIONS = [
  { key: "justech", label: "JUSTECH" },
  { key: "just_office", label: "JUST OFFICE" },
  { key: "mf_plug_safe", label: "PLUG SAFE" },
  { key: "omni_solutions", label: "OMNI" },
] as const;

export const VIGENCY_STYLES: Record<string, string> = {
  vigente: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30",
  proximo_a_vencer: "bg-amber-500/15 text-amber-800 border-amber-500/30",
  vencido: "bg-red-500/15 text-red-700 border-red-500/30",
  sin_fecha: "bg-muted text-muted-foreground",
};

export const TEMPLATE_TYPE_LABELS: Record<string, string> = {
  sncc: "Formulario SNCC",
  oferta_economica: "Oferta económica",
  declaracion_jurada: "Declaración jurada",
  autorizacion_fabricante: "Autorización fabricante",
  informacion_oferente: "Información oferente",
  carta: "Carta",
  dgcp: "Documento DGCP",
};

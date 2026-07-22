export interface M365SuggestedAction {
  id: string;
  label: string;
  action_type: string;
  href?: string | null;
}

export interface M365MailIntelligence {
  message_id: string;
  classification: string;
  classification_label: string;
  classification_confidence: number;
  matched_signals: string[];
  summary: string;
  sentiment: string;
  priority_score: number;
  priority_label: string;
  vendor?: string | null;
  client?: string | null;
  amount?: number | null;
  currency?: string | null;
  dgcp_process_code?: string | null;
  products: string[];
  document_type?: string | null;
  dates: string[];
  risks: string[];
  opportunities: string[];
  suggested_actions: M365SuggestedAction[];
}

export interface M365RepositoryFile {
  id: string;
  name: string;
  source: string;
  parent_path: string;
  document_category: string;
  document_category_label: string;
  document_type: string;
  classification_confidence: number;
  tags: string[];
  company_key?: string | null;
  is_folder: boolean;
  mime_type?: string | null;
  size_bytes?: number | null;
  web_url?: string | null;
  download_url?: string | null;
  graph_item_id: string;
}

export interface M365TemplatePreview {
  template_type: string;
  template_label: string;
  fields: Array<{ key: string; label: string; value: string; source: string; confidence: number }>;
  missing_fields: string[];
  generate_enabled: boolean;
}

export const REPOSITORY_CATEGORIES: { id: string; label: string; color: string }[] = [
  { id: "legal", label: "Legales", color: "bg-red-500/15 text-red-700" },
  { id: "formulario", label: "Formularios", color: "bg-blue-500/15 text-blue-700" },
  { id: "constitucion", label: "Constitución", color: "bg-purple-500/15 text-purple-700" },
  { id: "plantilla", label: "Plantillas", color: "bg-indigo-500/15 text-indigo-700" },
  { id: "contrato", label: "Contratos", color: "bg-orange-500/15 text-orange-700" },
  { id: "licitacion", label: "Licitaciones", color: "bg-emerald-500/15 text-emerald-700" },
  { id: "proveedor", label: "Proveedores", color: "bg-cyan-500/15 text-cyan-700" },
  { id: "financiero", label: "Finanzas", color: "bg-amber-500/15 text-amber-700" },
  { id: "ficha_tecnica", label: "Fichas técnicas", color: "bg-slate-500/15 text-slate-700" },
  { id: "cotizacion", label: "Cotizaciones", color: "bg-teal-500/15 text-teal-700" },
  { id: "general", label: "General", color: "bg-muted text-muted-foreground" },
];

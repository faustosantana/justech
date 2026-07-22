export interface GeneralRepositoryCard {
  key: string;
  label: string;
  folder_path?: string | null;
  href: string;
  indexed_files: number;
  status: string;
  description: string;
}

export interface CompanyHubCard {
  id: string;
  company_key: string;
  razon_social: string;
  rnc?: string | null;
  completeness_score: number;
  legal_documents_loaded: number;
  documents_missing: number;
  documents_expired: number;
  identity_available: boolean;
  identity_missing: string[];
  missing_fields_count: number;
  onedrive_data_path?: string | null;
  onedrive_legal_path?: string | null;
  onedrive_identity_path?: string | null;
  href: string;
}

export interface DocumentsHubDashboard {
  total_companies: number;
  legal_documents_loaded: number;
  documents_missing: number;
  documents_expired: number;
  dgcp_templates_available: number;
  price_lists_pending: number;
  price_lists_processed: number;
  stamps_registered: number;
  signatures_registered: number;
  pending_items_open: number;
  companies_complete: number;
  companies_incomplete: number;
  recent_syncs: {
    folder_key: string;
    label: string;
    status: string;
    last_sync_at?: string | null;
    indexed_files: number;
    last_error?: string | null;
  }[];
  recent_errors: string[];
  submodule_cards: {
    key: string;
    label: string;
    value: number | string;
    href?: string | null;
    variant?: string;
  }[];
  general_repositories?: GeneralRepositoryCard[];
  company_cards?: CompanyHubCard[];
  repository_bindings?: {
    id?: string | null;
    folder_key: string;
    label: string;
    folder_path?: string | null;
    status: string;
    indexed_files: number;
    last_sync_at?: string | null;
    last_error?: string | null;
    web_url?: string | null;
  }[];
}

export interface CompanyFieldStatus {
  field_key: string;
  label: string;
  kind: "text" | "document" | "hybrid";
  status: string;
  badge: string;
  unified_status?: string | null;
  text_value?: string | null;
  document_id?: string | null;
  document_name?: string | null;
  onedrive_url?: string | null;
  knowledge_asset_id?: string | null;
  view_url?: string | null;
  view_mode?: "local" | "external" | null;
  onedrive_folder?: string | null;
  vigency_status?: string | null;
  uploaded_at?: string | null;
  is_required: boolean;
}

export interface CompanyCompletion {
  company_id: string;
  company_key: string;
  empresa: string;
  completeness_score: number;
  fields_complete: number;
  fields_total: number;
  fields: CompanyFieldStatus[];
  validation_pending_count?: number;
  representatives_count?: number;
  progress_note?: string | null;
  progress_semaphore?: "green" | "yellow" | "red";
}

export function progressBarClass(semaphore?: string, score?: number): string {
  if (semaphore === "green" || (!semaphore && (score ?? 0) >= 100)) {
    return "bg-emerald-500";
  }
  if (semaphore === "yellow" || (!semaphore && (score ?? 0) >= 50)) {
    return "bg-amber-500";
  }
  return "bg-red-500";
}

export function progressBadgeVariant(semaphore?: string, score?: number): "default" | "secondary" | "destructive" {
  if (semaphore === "green" || (!semaphore && (score ?? 0) >= 80)) return "default";
  if (semaphore === "red" || (score ?? 0) < 50) return "destructive";
  return "secondary";
}

export interface CompanyDocumentUploadResult {
  ok: boolean;
  message: string;
  field_key: string;
  filename: string;
  document_id?: string | null;
  onedrive_url?: string | null;
  onedrive_path?: string | null;
  vigency_status?: string | null;
}

export interface CompanyDocumentProfile {
  id: string;
  company_key: string;
  razon_social?: string | null;
  nombre_comercial?: string | null;
  rnc?: string | null;
  direccion?: string | null;
  telefono?: string | null;
  correo?: string | null;
  representante_legal?: string | null;
  cedula_representante?: string | null;
  cargo_representante?: string | null;
  registro_mercantil?: string | null;
  proveedor_estado?: string | null;
  datos_bancarios?: string | null;
  responsable_legal?: string | null;
  responsable_financiero?: string | null;
  responsable_licitaciones?: string | null;
  missing_fields: string[];
  completeness_score: number;
  synced_at?: string | null;
  source_filename?: string | null;
  raw_json?: Record<string, unknown>;
}

export interface DocumentPendingItem {
  id: string;
  company_key: string;
  company_label: string;
  item_type: string;
  item_key: string;
  item_label: string;
  status: string;
  severity: string;
  detected_at: string;
  requested_at?: string | null;
  requested_to_email?: string | null;
  reminder_count: number;
  due_at?: string | null;
  onedrive_path?: string | null;
  onedrive_url?: string | null;
  suggested_filename?: string | null;
  responsible: string;
}

export interface RepresentativeMissingDocument {
  representative_id: string;
  representative_name: string;
  relation_label: string;
  document_type: string;
  document_label: string;
  status: string;
  validation_status?: string | null;
  badge: string;
}

export interface MissingItems {
  company_key: string;
  empresa: string;
  missing_fields: string[];
  missing_documents: string[];
  expired_documents: string[];
  identity_missing: string[];
  pending_items: DocumentPendingItem[];
  representative_documents?: RepresentativeMissingDocument[];
  validation_pending_count?: number;
  representatives_count?: number;
}

export interface ProfileFormResult {
  token: string;
  form_url: string;
  html: string;
  expires_at: string;
  company_key: string;
  empresa: string;
}

export interface RequestMissingResult {
  subject: string;
  body: string;
  recipient: string;
  missing_items: string[];
  task_id?: string | null;
  sent: boolean;
  can_send_outlook: boolean;
}

export interface DocumentsTrackingSummary {
  companies_complete: number;
  companies_incomplete: number;
  documents_expired: number;
  documents_missing: number;
  requests_sent: number;
  requests_pending: number;
  requests_overdue: number;
}

/** Cards principales del hub — siempre visibles aunque falle el API. */
export const HUB_MODULES = [
  {
    key: "empresas",
    href: "/apps/empresas-grupo/empresas",
    label: "Datos empresas",
    description: "Perfiles, JSON OneDrive, faltantes y solicitudes",
    icon: "building",
  },
  {
    key: "legales",
    href: "/documentos/legales",
    label: "Documentos legales",
    description: "Por empresa, subida, faltantes y solicitud a Jennipher",
    icon: "scale",
  },
  {
    key: "plantillas",
    href: "/documentos/plantillas",
    label: "Plantillas DGCP",
    description: "Sincronizar, indexar y usar en expediente",
    icon: "file",
  },
  {
    key: "repositorios",
    href: "/documentos/repositorios",
    label: "Repositorios OneDrive",
    description: "Rutas, estado, sincronización y errores",
    icon: "folder",
  },
  {
    key: "identidad",
    href: "/documentos/identidad",
    label: "Identidad corporativa",
    description: "Firma, sello, logo, membrete por empresa",
    icon: "shield",
  },
  {
    key: "precios",
    href: "/documentos/precios",
    label: "Inteligencia de precios",
    description: "Listas pendientes, procesadas e indexación",
    icon: "chart",
  },
  {
    key: "salidas",
    href: "/documentos/salidas",
    label: "Expedientes / Salidas",
    description: "Salidas documentales y expedientes generados",
    icon: "outbox",
  },
] as const;

export const DOCUMENTOS_SUBMODULES = [
  { key: "empresas", href: "/apps/empresas-grupo/empresas", label: "Empresas del grupo", icon: "building" },
  { key: "legales", href: "/documentos/legales", label: "Documentos legales", icon: "scale" },
  { key: "plantillas", href: "/documentos/plantillas", label: "Plantillas DGCP", icon: "file" },
  { key: "repositorios", href: "/documentos/repositorios", label: "Repositorios OneDrive", icon: "folder" },
  { key: "identidad", href: "/documentos/identidad", label: "Identidad corporativa", icon: "shield" },
  { key: "precios", href: "/documentos/precios", label: "Inteligencia de precios", icon: "chart" },
  { key: "pendientes", href: "/documentos/pendientes", label: "Pendientes", icon: "alert" },
  { key: "seguimiento", href: "/documentos/seguimiento", label: "Seguimiento", icon: "target" },
  { key: "salidas", href: "/documentos/salidas", label: "Expedientes / Salidas", icon: "outbox" },
] as const;

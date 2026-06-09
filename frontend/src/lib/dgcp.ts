export type OpportunityStatus =
  | "detected"
  | "to_review"
  | "interested"
  | "to_bid"
  | "discarded"
  | "won"
  | "lost";

export function isDGCPOperationalInterest(status: OpportunityStatus): boolean {
  return status === "interested" || status === "to_bid" || status === "won" || status === "lost";
}

export type OpportunityCompany =
  | "justech"
  | "just_office"
  | "mf_plug_safe"
  | "omni_solutions"
  | "unclassified";

export type OpportunityPriority = "critical" | "high" | "medium" | "low";

export type OpportunityAction =
  | "mostrar_interes"
  | "licitar"
  | "revisar"
  | "descartar"
  | "ganada"
  | "perdida";

export interface DGCPOpportunity {
  id: string;
  tenant_id: string;
  code: string;
  ocid: string | null;
  institution: string;
  title: string;
  amount: string;
  currency: string;
  probability: number;
  score: number;
  status: OpportunityStatus;
  priority: OpportunityPriority;
  company: OpportunityCompany;
  confidence_score: number;
  classification_reason: string | null;
  dgcp_status: string | null;
  modalidad: string | null;
  objeto_proceso: string | null;
  deadline: string;
  description: string | null;
  source_url: string | null;
  full_info: Record<string, unknown>;
  similar_history: Array<Record<string, unknown>>;
  risks: Array<{ nivel: string; descripcion: string }>;
  ai_recommendations: string[];
  suggested_action: string | null;
  justech_potential_amount: string;
  synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DGCPSummary {
  total_opportunities: number;
  total_potential_amount: string;
  by_status: Record<string, number>;
  by_company: Record<string, number>;
  by_priority: Record<string, number>;
  amount_by_company: Record<string, string>;
  to_bid: number;
  to_review: number;
  discarded: number;
  won: number;
  lost: number;
}

export interface DGCPOpportunityListResponse {
  items: DGCPOpportunity[];
  summary: DGCPSummary;
  total: number;
}

export interface DGCPSyncJob {
  id: string;
  tenant_id: string;
  trigger: string;
  status: string;
  pages_synced: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface DGCPSyncSchedule {
  id: string;
  tenant_id: string;
  is_enabled: boolean;
  interval_hours: number;
  max_pages: number;
  page_size: number;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface DGCPOpportunityHistory {
  id: string;
  opportunity_id: string;
  user_id: string | null;
  action: string;
  from_status: string | null;
  to_status: string | null;
  notes: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DGCPAuditLog {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  user_id: string | null;
  created_at: string;
}

export const STATUS_LABELS: Record<OpportunityStatus, string> = {
  detected: "Detectada",
  to_review: "En revisión",
  interested: "Interesada",
  to_bid: "En preparación",
  discarded: "Descartada",
  won: "Ganada",
  lost: "Perdida",
};

export const COMPANY_LABELS: Record<OpportunityCompany, string> = {
  justech: "Justech",
  just_office: "Just Office",
  mf_plug_safe: "MF Plug & Safe",
  omni_solutions: "Omni Solutions",
  unclassified: "Sin clasificar",
};

export const PRIORITY_LABELS: Record<OpportunityPriority, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Media",
  low: "Baja",
};

export const ACTION_LABELS: Record<OpportunityAction, string> = {
  mostrar_interes: "Mostrar interés",
  licitar: "Licitar / En preparación",
  revisar: "Marcar en revisión",
  descartar: "Descartar",
  ganada: "Ganada",
  perdida: "Perdida",
};

export function formatCurrency(value: string | number, currency = "DOP"): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("es-DO", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat("es-DO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(dateStr + "T12:00:00"));
}

export function formatDateTime(dateStr: string): string {
  return new Intl.DateTimeFormat("es-DO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateStr));
}

export function scoreColor(score: number): string {
  if (score >= 75) return "text-success";
  if (score >= 50) return "text-warning";
  return "text-destructive";
}

export interface DGCPRequirementEvidence {
  requirement_key: string;
  documento_origen: string;
  pagina: number | null;
  seccion: string | null;
  fragmento: string;
  confianza: string;
  process_document_id: string | null;
}

export interface DGCPRequirementItem {
  key: string;
  label: string;
  tipo: string;
  mandatory: boolean;
  subsanable: boolean;
  source: string;
  matched_text: string | null;
  evidence?: DGCPRequirementEvidence[];
}

export interface DGCPRequirements {
  opportunity_id: string;
  opportunity_code: string;
  opportunity_title: string;
  analyzed_at: string | null;
  technical: DGCPRequirementItem[];
  legal: DGCPRequirementItem[];
  financial: DGCPRequirementItem[];
  administrative: DGCPRequirementItem[];
  mandatory_documents: DGCPRequirementItem[];
  subsanable_documents: DGCPRequirementItem[];
  critical_dates: Array<Record<string, unknown>>;
  guarantees: string[];
  samples: string[];
  sncc_forms: string[];
  certifications: string[];
}

export interface DGCPChecklistItem {
  id: string;
  requirement_key: string;
  requirement: string;
  tipo: string;
  mandatory: boolean;
  status: string;
  document_id: string | null;
  document_title: string | null;
  valid_until: string | null;
  risk: string | null;
  recommended_action: string | null;
  assignee: string | null;
  task_id: string | null;
  completable: boolean;
  form_type: string | null;
  display_status?: string | null;
  notes?: string | null;
  knowledge_asset_id?: string | null;
  process_document_id?: string | null;
  relative_path?: string | null;
  match_source?: string | null;
  validity_analysis?: Record<string, unknown> | null;
  manual_validation?: Record<string, unknown> | null;
  note_history?: Array<{
    note: string;
    author: string;
    author_id?: string;
    created_at: string;
    action: string;
  }>;
}

export interface DGCPChecklist {
  opportunity_id: string;
  items: DGCPChecklistItem[];
  total: number;
  mandatory_total?: number;
  ready_count: number;
  compliant_count?: number;
  pending_count: number;
  expired_count: number;
  incomplete_count: number;
  review_count?: number;
  unanalyzed_count?: number;
}

export interface DGCPBidPackage {
  opportunity_id: string;
  opportunity_code: string;
  preparation_pct: number;
  total_requirements?: number;
  mandatory_requirements?: number;
  compliant_count?: number;
  found_documents: number;
  pending_documents: number;
  expired_documents: number;
  forms_to_complete: number;
  review_count?: number;
  recommended_tasks: string[];
  available: string[];
  missing: string[];
  expired: string[];
  to_complete: string[];
  requires_review?: string[];
  analyzed_at: string | null;
}

export interface DGCPDocumentMatch {
  requirement_key: string;
  requirement_label: string;
  document_id: string | null;
  document_title: string | null;
  knowledge_asset_id?: string | null;
  match_source?: string | null;
  relative_path?: string | null;
  match_score: number;
  status: string;
  vigency_status?: string | null;
  valid_until: string | null;
  notes: string | null;
  observation?: string | null;
  validity_analysis?: Record<string, unknown> | null;
}

export interface DGCPDocumentMatches {
  opportunity_id: string;
  matches: DGCPDocumentMatch[];
  found_count: number;
  missing_count: number;
  expired_count: number;
  review_count?: number;
  complete_count?: number;
}

export interface DGCPFormPreviewField {
  label: string;
  value: string | null;
  status: string;
  confidence: number;
  source?: string | null;
}

export interface DGCPFormPreview {
  opportunity_id: string;
  form_type: string;
  company: string;
  fields: DGCPFormPreviewField[];
  missing: string[];
  warnings: string[];
  overall_confidence: number;
  note: string;
  generate_enabled: boolean;
}

export interface DGCPProcessDocument {
  id: string;
  title: string;
  doc_role: string;
  priority: string;
  format: string;
  source_type: string;
  source_url: string | null;
  ingestion_status: string;
  display_status?: string;
  has_text: boolean;
}

export interface DGCPProcessDocuments {
  opportunity_id: string;
  items: DGCPProcessDocument[];
  total: number;
}

export interface DGCPBidAlert {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  requirement_key?: string;
  resolved?: boolean;
}

export interface DGCPBidAlerts {
  opportunity_id: string;
  alerts: DGCPBidAlert[];
  total: number;
}

export interface DGCPExpedientePrepareResult {
  opportunity_id: string;
  expediente_status: string;
  expediente_path: string;
  preparation_pct: number;
  copied_documents: number;
  generated_forms: number;
  manifest: Record<string, unknown>;
}

export interface DGCPExpedienteStatus {
  opportunity_id: string;
  opportunity_code: string;
  expediente_status: string;
  expediente_path: string | null;
  preparation_pct: number;
  found_documents: number;
  pending_documents: number;
  expired_documents: number;
  forms_to_complete: number;
  alerts_count: number;
  manifest: Record<string, unknown>;
  can_mark_ready: boolean;
  can_download: boolean;
  present_enabled: boolean;
}

export const EXPEDIENTE_STATUS_LABELS: Record<string, string> = {
  sin_preparar: "Sin preparar",
  expediente_en_preparacion: "En preparación",
  expediente_incompleto: "Incompleto",
  expediente_con_documentos_vencidos: "Con documentos vencidos",
  expediente_listo_para_revision: "Listo para revisión",
  expediente_listo_para_presentar: "Listo para presentar",
};

export const COMPLIANCE_STATUS_LABELS: Record<string, string> = {
  encontrado_vigente: "Cumplido",
  encontrado_vencido: "Vencido",
  encontrado_sin_fecha: "Vigencia no verificada",
  encontrado_sin_analizar: "Pendiente de análisis",
  validado_manual: "Validado manualmente",
  faltante: "Faltante",
  requiere_completado: "Por completar",
  requiere_revision: "Requiere revisión",
  no_aplica: "No aplica",
  pendiente: "Pendiente",
  vencido: "Vencido",
  encontrado: "Encontrado",
  validado: "Validado",
};

export const PROCESS_DOC_ROLE_LABELS: Record<string, string> = {
  pliego: "Pliego de condiciones",
  tdr: "TDR",
  ficha_tecnica: "Ficha técnica",
  invitacion: "Invitación",
  formulario: "Formulario",
  cronograma: "Cronograma",
  enmienda: "Enmienda",
  general: "General",
};

export const PROCESS_PRIORITY_LABELS: Record<string, string> = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
};

export const CHECKLIST_STATUS_LABELS: Record<string, string> = {
  pendiente: "Pendiente",
  encontrado: "Encontrado",
  vencido: "Vencido",
  incompleto: "Incompleto",
  completar: "Por completar",
  requiere_completado: "Requiere completado",
  requiere_actualizacion: "Requiere actualización",
  plantilla_disponible: "Plantilla disponible",
  validado: "Validado",
  completo: "Completo",
  requiere_revision: "Requiere revisión",
};

export const REQUIREMENT_TYPE_LABELS: Record<string, string> = {
  tecnico: "Técnico",
  legal: "Legal",
  financiero: "Financiero",
  administrativo: "Administrativo",
};

export function priorityColor(priority: OpportunityPriority): string {
  const map: Record<OpportunityPriority, string> = {
    critical: "text-red-400",
    high: "text-amber-400",
    medium: "text-blue-400",
    low: "text-muted-foreground",
  };
  return map[priority];
}

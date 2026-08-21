export type OpportunityStatus =
  | "detected"
  | "analyzing"
  | "qualified"
  | "not_qualified"
  | "preparing"
  | "pending_documents"
  | "ready_to_submit"
  | "submitted"
  | "under_evaluation"
  | "suspended"
  | "awarded"
  | "lost"
  | "cancelled"
  // Legacy — compatibilidad datos existentes
  | "to_review"
  | "interested"
  | "to_bid"
  | "discarded"
  | "won";

/** Estados visibles en filtros de pipeline (Procesos / Adjudicaciones). */
export const PIPELINE_STATUSES: OpportunityStatus[] = [
  "detected",
  "interested",
  "preparing",
  "ready_to_submit",
  "submitted",
  "suspended",
  "awarded",
  "lost",
  "discarded",
];

export function isDGCPOperationalInterest(status: OpportunityStatus): boolean {
  return (
    status === "interested" ||
    status === "to_bid" ||
    status === "preparing" ||
    status === "pending_documents" ||
    status === "ready_to_submit" ||
    status === "submitted" ||
    status === "under_evaluation" ||
    status === "awarded" ||
    status === "won" ||
    status === "lost"
  );
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
  | "marcar_interes"
  | "desmarcar_interes"
  | "iniciar_preparacion"
  | "marcar_listo_presentar"
  | "marcar_presentada"
  | "marcar_suspendida"
  | "marcar_adjudicada"
  | "marcar_no_adjudicada"
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
  deadline: string | null;
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
  jaios_intelligence?: DGCPIntelligence | null;
  needs_review?: boolean;
  responsible_name?: string | null;
  primary_action?: string | null;
  available_actions?: string[];
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
  presentation?: Record<string, number>;
}

export interface DGCPProcessUpdateDashboardItem {
  opportunity_id: string;
  process_code: string;
  title: string;
  pending_count: number;
  critical_count: number;
  requires_reanalysis?: boolean;
  last_change_at?: string | null;
}

export interface DGCPProcessUpdateDashboardResponse {
  enabled: boolean;
  total_pending: number;
  total_critical: number;
  items: DGCPProcessUpdateDashboardItem[];
}

export interface DGCPProcessUpdateItem {
  id: string;
  change_type?: string;
  severity?: string;
  summary?: string;
  status?: string;
  detected_at?: string | null;
  [key: string]: unknown;
}

export interface DGCPProcessUpdatesResponse {
  opportunity_id: string;
  enabled?: boolean;
  items?: DGCPProcessUpdateItem[];
  updates?: DGCPProcessUpdateItem[];
  total?: number;
  snapshot?: Record<string, unknown> | null;
  meta?: {
    pending_count?: number;
    critical_count?: number;
    requires_reanalysis?: boolean;
    last_checked_at?: string | null;
    last_change_at?: string | null;
    notification_hook_ready?: boolean;
  };
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
  detected: "Nueva",
  analyzing: "En análisis",
  qualified: "Calificada",
  not_qualified: "No calificada",
  preparing: "En preparación",
  pending_documents: "Pendiente documentos",
  ready_to_submit: "Lista para presentar",
  submitted: "Presentada",
  under_evaluation: "Presentada (en evaluación)",
  suspended: "Suspendida",
  awarded: "Adjudicada",
  lost: "No adjudicada",
  cancelled: "Cancelada",
  to_review: "Nueva (requiere revisión)",
  interested: "Interesada",
  to_bid: "En preparación",
  discarded: "Descartada",
  won: "Adjudicada",
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

export function formatCurrency(
  value: string | number | null | undefined,
  currency = "DOP",
): string {
  if (value == null || value === "") return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return "—";
  const code = currency && /^[A-Z]{3}$/i.test(currency) ? currency.toUpperCase() : "DOP";
  try {
    return new Intl.NumberFormat("es-DO", {
      style: "currency",
      currency: code,
      maximumFractionDigits: 0,
    }).format(num);
  } catch {
    return String(value);
  }
}

function parseDisplayDate(dateStr: string): Date | null {
  const raw = dateStr.trim();
  if (!raw) return null;
  // date-only YYYY-MM-DD → noon local to avoid TZ day-shift
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const d = new Date(`${raw}T12:00:00`);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const d = parseDisplayDate(dateStr);
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("es-DO", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(d);
  } catch {
    return "—";
  }
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const d = parseDisplayDate(dateStr);
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("es-DO", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return "—";
  }
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
  is_portal_link?: boolean;
  is_downloadable?: boolean;
  document_id?: string | null;
  storage_uri?: string | null;
  created_at?: string | null;
  file_size?: number | null;
  uploaded_by?: string | null;
  is_primary?: boolean;
  include_in_analysis?: boolean;
  metadata?: Record<string, unknown> | null;
}

export interface DGCPProcessDocuments {
  opportunity_id: string;
  items: DGCPProcessDocument[];
  total: number;
  portal?: DGCPProcessDocument | null;
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

/** Quita ruido de clasificación IA para UI. */
export function sanitizeClassificationReason(reason: string | null | undefined): string {
  if (!reason) return "";
  let out = String(reason);
  // \b(token?)\b -> token
  out = out.replace(/\\b\(([^)]*)\)\\b/g, "$1");
  out = out.replace(/\\b/g, " ");
  out = out.replace(/\(\?[:=!][^)]*\)/g, " ");
  out = out.replace(/[|()\[\]{}*+^$\\]+/g, " ");
  out = out.replace(/\?+/g, "");
  out = out.replace(/\s+/g, " ").trim();
  return out;
}

export function sanitizeKeywordList(keywords: string[] | null | undefined): string[] {
  if (!keywords?.length) return [];
  const out: string[] = [];
  for (const raw of keywords) {
    const cleaned = sanitizeClassificationReason(raw);
    if (cleaned && !out.includes(cleaned)) out.push(cleaned);
  }
  return out;
}



export interface DGCPHistoricalAwardItem {
  id: string;
  process_code: string;
  contract_code?: string | null;
  buyer_institution: string;
  supplier_name?: string | null;
  award_date?: string | null;
  item_description?: string | null;
  contract_object?: string | null;
  unit_measure?: string | null;
  unit_price?: string | number | null;
  quantity?: string | number | null;
  awarded_amount?: string | number | null;
  modality?: string | null;
  contract_url?: string | null;
  process_url?: string | null;
  source?: string;
  publication_to_award_days?: number | null;
  similarity_score?: number;
  similarity_level?: string;
  match_reasons?: string[];
  matched_keywords?: string[];
}

export interface DGCPHistoricalIndicators {
  similar_process_count: number;
  similar_item_count: number;
  min_unit_price?: string | number | null;
  avg_unit_price?: string | number | null;
  max_unit_price?: string | number | null;
  last_awarded_unit_price?: string | number | null;
  most_frequent_supplier?: string | null;
  most_frequent_supplier_wins?: number;
  competition_level?: string;
}

export interface DGCPHistoricalPriceRecommendation {
  currency?: string;
  historical_min_unit?: string | number | null;
  historical_avg_unit?: string | number | null;
  historical_max_unit?: string | number | null;
  recommended_offer_low?: string | number | null;
  recommended_offer_high?: string | number | null;
  market_supplier_avg?: string | number | null;
  margin_risk?: string | null;
  summary?: string;
}

export interface DGCPHistoricalIndexMeta {
  total_indexed: number;
  institution_indexed: number;
  last_indexed_at?: string | null;
  last_index_job_status?: string | null;
  reindex_instructions?: string;
  source?: string;
}

export interface DGCPHistoricalSimilarResponse {
  opportunity_id: string;
  process_code: string;
  process_title?: string | null;
  buyer_institution: string;
  keywords_used: string[];
  cached: boolean;
  searched_at?: string | null;
  expires_at?: string | null;
  source: string;
  pages_scanned: number;
  candidates_scanned: number;
  status: string;
  message: string;
  error_message?: string | null;
  matches: DGCPHistoricalAwardItem[];
  other_institution_matches?: DGCPHistoricalAwardItem[];
  total_matches: number;
  indicators: DGCPHistoricalIndicators;
  price_recommendation?: DGCPHistoricalPriceRecommendation | null;
  ai_insights: string[];
  index_meta: DGCPHistoricalIndexMeta;
}

export interface DGCPHistoricalIndexResponse {
  job_id: string;
  status: string;
  pages_indexed: number;
  contracts_indexed: number;
  items_indexed: number;
  error_message?: string | null;
  message?: string;
}

export interface DGCPHistoricalSourceRef {
  source: string;
  source_url?: string | null;
  process_url?: string | null;
  contract_url?: string | null;
  dgcp_process_code?: string | null;
  retrieved_at?: string | null;
}

export interface DGCPHistoricalPurchaseRow {
  award_id: string;
  process_code: string;
  contract_code?: string | null;
  award_date?: string | null;
  institution: string;
  description?: string | null;
  supplier_name?: string | null;
  supplier_rpe?: string | null;
  supplier_rnc?: string | null;
  awarded_amount?: number | string | null;
  currency?: string;
  quantity?: number | string | null;
  unit_price?: number | string | null;
  unit_measure?: string | null;
  modality?: string | null;
  award_status?: string | null;
  match_class?: "EXACTA" | "ALTA_SIMILITUD" | "RELACIONADA";
  match_class_label?: string;
  similarity_score?: number;
  similarity_pct?: number | null;
  match_reasons?: string[];
  data_quality?: "VERIFICADO" | "PARCIAL" | "INCOMPLETO";
  source?: DGCPHistoricalSourceRef;
}

export interface DGCPHistoricalIntelligence {
  current_process: {
    opportunity_id: string;
    process_code: string;
    title?: string | null;
    institution: string;
    estimated_amount?: number | string | null;
    currency?: string;
    amount_kind?: string;
  };
  window_months?: number | null;
  last_purchase: {
    available: boolean;
    title?: string;
    match_class?: string | null;
    match_class_label?: string | null;
    criterion?: string | null;
    purchase?: DGCPHistoricalPurchaseRow | null;
    caveats?: string[];
  };
  last_supplier: {
    available: boolean;
    supplier_name?: string | null;
    supplier_rpe?: string | null;
    award_date?: string | null;
    awarded_amount?: number | string | null;
    currency?: string;
    process_code?: string | null;
    source_url?: string | null;
  };
  institution_purchases: DGCPHistoricalPurchaseRow[];
  suppliers_ranking: Array<{
    supplier_name: string;
    supplier_rpe?: string | null;
    awards_count: number;
    processes_count: number;
    total_amount: number | string;
    currency?: string;
    last_award_date?: string | null;
    share_pct: number;
  }>;
  concentration: {
    level: string;
    top1_share_pct?: number | null;
    top3_share_pct?: number | null;
    suppliers_count: number;
    note?: string;
  };
  product_lines: Array<{
    line_number?: number | null;
    requested_description: string;
    last_purchase?: DGCPHistoricalPurchaseRow | null;
    match_class?: string | null;
    similarity_pct?: number | null;
  }>;
  price_history: {
    available: boolean;
    currency?: string;
    points?: Array<{
      award_date?: string | null;
      supplier_name?: string | null;
      quantity?: number | string | null;
      unit_price?: number | string | null;
      awarded_amount?: number | string | null;
      process_code?: string | null;
      source_url?: string | null;
    }>;
    last_unit_price?: number | string | null;
    avg_unit_price?: number | string | null;
    min_unit_price?: number | string | null;
    max_unit_price?: number | string | null;
    median_unit_price?: number | string | null;
    variation_vs_last_pct?: number | null;
    caveats?: string[];
  };
  frequency: {
    available: boolean;
    summary?: string;
    temporal_pattern?: string | null;
    process_count?: number;
  };
  related_processes: DGCPHistoricalPurchaseRow[];
  budget_comparison?: {
    available: boolean;
    current_estimated_amount?: number | string | null;
    current_currency?: string;
    last_comparable_amount?: number | string | null;
    variation_pct?: number | null;
    caveats?: string[];
  };
  executive_summary?: { paragraphs: string[]; based_on_metrics_only?: boolean };
  data_quality?: {
    overall: string;
    verified_count: number;
    partial_count: number;
    incomplete_count: number;
    notes?: string[];
  };
  statistics?: Record<string, unknown>;
  latency_ms?: number | null;
  indexed_lines_scanned?: number;
  message?: string;
}

export interface DGCPExpedienteDashboardKpis {
  porcentaje_completado: number;
  requisitos_pendientes: number;
  documentos_faltantes: number;
  documentos_rechazados: number;
  documentos_aprobados: number;
  proximos_vencimientos: number;
  alertas_criticas: number;
  total_requisitos: number;
  en_revision?: number;
  riesgos_criticos?: number;
}

export interface DGCPExpedienteProgreso {
  total_requisitos: number;
  completados: number;
  pendientes: number;
  en_revision: number;
  riesgos_criticos: number;
  porcentaje_real: number;
}

export interface DGCPExpedienteTimelineItem {
  event_type: string;
  label?: string;
  at: string;
  actor_id?: string | null;
  summary?: string;
  detail?: Record<string, unknown>;
}

export interface DGCPExpedienteFinalValidation {
  listo_para_presentar: boolean;
  estado: string;
  preparation_pct: number;
  faltantes: string[];
  rechazados: string[];
  en_revision: string[];
  gaps: Array<{ tipo: string; items: string[] }>;
  explicacion: string;
  validaciones_ia: Array<Record<string, unknown>>;
  validated_at: string;
  opportunity_code: string;
}

export interface DGCPExpedienteDashboardSection {
  id: string;
  nombre: string;
  total: number;
  pendientes: number;
  items: Array<Record<string, unknown>>;
}

export interface DGCPExpedienteDashboard {
  opportunity_id: string;
  opportunity_code: string;
  expediente_status: string;
  preparation_pct: number;
  progreso?: DGCPExpedienteProgreso;
  score?: DGCPExpedienteScore | null;
  kpis: DGCPExpedienteDashboardKpis;
  ia_proactiva?: {
    documentos_faltantes: Array<Record<string, unknown>>;
    proximos_a_vencer: Array<{ tipo: string; fecha: string; descripcion?: string }>;
    riesgos: Array<Record<string, unknown>>;
    requisitos_criticos: Array<Record<string, unknown>>;
    recomendaciones: string[];
  };
  timeline?: DGCPExpedienteTimelineItem[];
  validacion_preview?: DGCPExpedienteFinalValidation | null;
  informacion_general: Record<string, unknown>;
  cronograma: Record<string, unknown>;
  secciones: DGCPExpedienteDashboardSection[];
  requisitos: Array<Record<string, unknown>>;
  documentos_faltantes: Array<Record<string, unknown>>;
  documentos_rechazados: Array<Record<string, unknown>>;
  documentos_aprobados: Array<Record<string, unknown>>;
  proximos_vencimientos: Array<{ tipo: string; fecha: string; descripcion?: string }>;
  alertas_criticas: Array<Record<string, unknown>>;
  document_matches_count: number;
  analyzed_at?: string | null;
}

export interface DGCPComplianceMatrixRow {
  id: string;
  requirement_key?: string;
  requisito: string;
  estado: string;
  responsable: string;
  documento_asociado: string;
  cumple: string;
  riesgo: string;
  observaciones_ia: string;
}

export interface DGCPComplianceMatrix {
  opportunity_id: string;
  opportunity_code: string;
  generated_at: string;
  total: number;
  columns: string[];
  rows: DGCPComplianceMatrixRow[];
}

export interface DGCPRequirementEvidenceDetail {
  opportunity_id: string;
  opportunity_code: string;
  checklist_item_id: string;
  requirement_key?: string;
  requirement?: string;
  tiene_evidencia: boolean;
  evidencia: {
    pagina?: number | null;
    documento_origen?: string | null;
    parrafo?: string | null;
    texto_original?: string | null;
    confianza?: string | number | null;
    process_document_id?: string | null;
  };
}

export interface DGCPRequirementAskResponse {
  opportunity_id: string;
  checklist_item_id: string;
  requirement_key?: string;
  question: string;
  answer: string;
  context_used: string[];
  sources: string[];
  answered_at: string;
}

export interface DGCPExpedienteScore {
  score_total: number;
  desglose: Array<{ key: string; label: string; pct: number | null; detail?: string | null }>;
  explicacion: string;
  gaps?: string[];
  opportunity_id?: string;
  opportunity_code?: string;
  computed_at?: string;
}

export interface DGCPExpedientePreviewFile {
  path: string;
  name: string;
  kind: string;
  size_bytes: number;
  preview_url?: string | null;
  planned?: boolean;
}

export interface DGCPExpedientePreview {
  opportunity_id: string;
  opportunity_code: string;
  prepared: boolean;
  expediente_path?: string | null;
  zip_name: string;
  zip_available: boolean;
  files: DGCPExpedientePreviewFile[];
  counts: Record<string, number>;
  note: string;
}

export interface DGCPBidCopilotInsight {
  item: string;
  explicacion: string;
}

export interface DGCPBidCopilotCompetitividad {
  fortalezas: DGCPBidCopilotInsight[];
  debilidades: DGCPBidCopilotInsight[];
  requisitos_criticos: DGCPBidCopilotInsight[];
  riesgos_descalificacion: DGCPBidCopilotInsight[];
  opcionales_alto_valor: DGCPBidCopilotInsight[];
  ventajas_competitivas: DGCPBidCopilotInsight[];
  calidad_expediente_pct?: number | null;
  listo_para_presentar?: boolean | null;
}

export interface DGCPBidCopilotAdjudicationCategory {
  key: string;
  label: string;
  pct: number | null;
  detail?: string | null;
}

export interface DGCPBidCopilotAdjudication {
  score_general: number;
  desglose: DGCPBidCopilotAdjudicationCategory[];
  explicacion_ia: string;
  similar_matches?: number;
  calidad_expediente_pct?: number | null;
}

export interface DGCPBidCopilotTask {
  tarea: string;
  responsable: string;
  fecha_limite?: string | null;
  dependencia?: string | null;
  estado?: string | null;
  prioridad: "alta" | "media" | "baja";
  requirement_key?: string | null;
  checklist_item_id?: string | null;
}

export interface DGCPBidCopilotPlan {
  alta: DGCPBidCopilotTask[];
  media: DGCPBidCopilotTask[];
  baja: DGCPBidCopilotTask[];
  total: number;
}

export interface DGCPBidCopilotRisk {
  descripcion: string;
  impacto: string;
  probabilidad: string;
  criticidad: string;
  recomendacion_ia: string;
  accion_correctiva: string;
}

export interface DGCPBidCopilotExecutive {
  estado_expediente: string;
  porcentaje_completado: number;
  score_calidad?: number | null;
  score_adjudicacion?: number | null;
  riesgos: string[];
  fortalezas: string[];
  documentos_pendientes: string[];
  recomendacion: "listo_para_presentar" | "presentar_con_observaciones" | "no_presentar";
  recomendacion_label: string;
  explicacion_ia: string;
  proceso?: {
    code?: string;
    title?: string;
    institution?: string;
    amount?: string;
    deadline?: string | null;
  };
}

export interface DGCPBidCopilotCommittee {
  veredicto: "apto" | "apto_con_observaciones" | "no_apto";
  veredicto_label: string;
  observaciones: string[];
  posibles_rechazos: string[];
  documentos_debiles: string[];
  incumplimientos: string[];
  mejoras_recomendadas: string[];
  fundamento: string;
  simulated_at?: string;
  mode?: string;
}

export interface DGCPBidCopilotPayload {
  opportunity_id: string;
  opportunity_code: string;
  generated_at: string;
  competitividad: DGCPBidCopilotCompetitividad;
  score_adjudicacion: DGCPBidCopilotAdjudication;
  plan_accion: DGCPBidCopilotPlan;
  matriz_riesgos: DGCPBidCopilotRisk[];
  resumen_ejecutivo: DGCPBidCopilotExecutive;
  simulacion_comite: DGCPBidCopilotCommittee;
  fuentes: string[];
}

export interface DGCPBidCopilotExecutiveDashboard {
  generated_at: string;
  expedientes_activos: number;
  expedientes_listos: number;
  riesgos_criticos: number;
  licitaciones_por_vencer: number;
  valor_economico_total: string;
  probabilidad_promedio_adjudicacion: number;
  costos_estimados_restantes: string;
  estado_por_responsable: Array<{
    responsable: string;
    pendientes: number;
    completados: number;
    total: number;
  }>;
  notas?: string[];
}

export interface DGCPIntelligenceQuestion {
  answer: unknown;
  label: string;
  detail?: string;
}

export interface DGCPIntelligence {
  premium_score?: number;
  probability_band?: string;
  score_factors?: Record<string, number>;
  participation?: {
    should_participate?: boolean;
    worth_it?: boolean;
    competitiveness?: string;
    recommendation?: string;
    reason?: string;
  };
  executive?: {
    summary?: string;
    risks?: string[];
    opportunities?: string[];
    recommendation?: string;
    recommendation_reason?: string;
    next_actions?: string[];
    questions?: Record<string, DGCPIntelligenceQuestion>;
  };
  expediente?: {
    stage_code?: string;
    stage_label?: string;
    completeness_pct?: number;
    traffic_light?: string;
    checklist?: unknown[];
    missing?: string[];
    expired?: string[];
    message?: string;
  };
  recommendations?: {
    company_key?: string;
    company_label?: string;
    supplier?: string;
    manufacturer?: string;
    documents_to_attach?: string[];
    personnel?: string[];
    participation?: string;
    products_detected?: Array<{ name?: string; quantity?: string; notes?: string }>;
  };
  similar_awards_count?: number;
  analyzed_at?: string | null;
}

export function hasJaiosIntelligence(
  intel: DGCPIntelligence | null | undefined | Record<string, unknown>,
): intel is DGCPIntelligence {
  if (!intel || typeof intel !== "object") return false;
  return typeof (intel as DGCPIntelligence).premium_score === "number";
}

export function trafficLightLabel(light: string): string {
  const map: Record<string, string> = {
    green: "Listo / favorable",
    yellow: "Atención requerida",
    red: "No recomendado",
  };
  return map[light] ?? light;
}

export function trafficLightBg(light: string): string {
  const map: Record<string, string> = {
    green: "bg-success/5 border-success/20",
    yellow: "bg-warning/5 border-warning/25",
    red: "bg-destructive/5 border-destructive/25",
  };
  return map[light] ?? "";
}

export function probabilityBandLabel(band: string): string {
  const map: Record<string, string> = {
    alta: "Probabilidad alta",
    media: "Probabilidad media",
    baja: "Probabilidad baja",
  };
  return map[band] ?? band;
}

export function getOpportunityTrafficLight(
  opp: DGCPOpportunity,
): "green" | "yellow" | "red" | null {
  return (opp.jaios_intelligence?.expediente?.traffic_light as "green" | "yellow" | "red") ?? null;
}

export { resolveOpportunityGuidance } from "./dgcp-funnel";

/** Fichas técnicas — tipos alineados al schema backend. */
export interface DGCPTechSheetOfferedProduct {
  brand?: string | null;
  model?: string | null;
  manufacturer?: string | null;
  sku?: string | null;
  description?: string | null;
  source?: string | null;
  image_url?: string | null;
}

export interface DGCPTechSheetProductImage {
  id: string;
  label?: string | null;
  source?: string;
  url?: string | null;
  local_path?: string | null;
  filename?: string | null;
  mime_type?: string | null;
  sort_order?: number;
}

export interface DGCPTechSheetBrandingAssetStatus {
  asset_type: string;
  status: string;
  label?: string | null;
  source?: string | null;
  view_url?: string | null;
  filename?: string | null;
}

export interface DGCPTechSheetBrandingContext {
  company_key: string;
  company_name: string;
  rnc?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  representative_name?: string | null;
  representative_role?: string | null;
  logo: DGCPTechSheetBrandingAssetStatus;
  signature: DGCPTechSheetBrandingAssetStatus;
  stamp: DGCPTechSheetBrandingAssetStatus;
}

export interface DGCPTechSheetItem {
  id: string;
  required_product_name: string;
  required_description?: string | null;
  required_specs?: string[];
  quantity?: string | null;
  source_document_id?: string | null;
  source_fragment?: string | null;
  source_page?: number | null;
  source_section?: string | null;
  detection_source?: string;
  offered_product?: DGCPTechSheetOfferedProduct | null;
  compliance_matrix?: Array<Record<string, unknown>>;
  missing_fields?: string[];
  status: string;
  confidence?: number;
  responsible_user_id?: string | null;
  draft?: Record<string, unknown> | null;
  draft_document_id?: string | null;
  product_images?: DGCPTechSheetProductImage[];
  branding?: DGCPTechSheetBrandingContext | null;
  uploaded_file?: {
    id?: string | null;
    filename?: string | null;
    local_path?: string | null;
    mime_type?: string | null;
    replaced_at?: string | null;
    replaced_by?: string | null;
  } | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DGCPTechSheetSummary {
  total: number;
  detectadas: number;
  pendientes_producto: number;
  borradores: number;
  aprobadas: number;
  con_riesgo: number;
  requires_technical_sheets: boolean;
  message?: string | null;
}

export interface DGCPTechSheetsResponse {
  opportunity_id: string;
  enabled: boolean;
  summary: DGCPTechSheetSummary;
  items: DGCPTechSheetItem[];
}



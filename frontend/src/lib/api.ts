import type {
  DGCPAuditLog,
  DGCPOpportunity,
  DGCPOpportunityHistory,
  DGCPOpportunityListResponse,
  DGCPSummary,
  DGCPSyncJob,
  DGCPSyncSchedule,
  OpportunityAction,
  OpportunityCompany,
  OpportunityPriority,
  OpportunityStatus,
} from "./dgcp";
import type { BusinessCompany, BusinessCompanyListResponse } from "./companies";
import type { GlobalCompanyContext, GlobalCompanyContextUpdate } from "./company-context-types";
import type { ExecutiveDashboard } from "./dashboard";
import type { AssistantQueryRequest, AssistantQueryResponse } from "./assistant";
import type { EnterpriseSearchResponse } from "./search";
import type {
  M365Health,
  M365ListResponse,
  M365SearchResponse,
  M365Status,
} from "./m365";
import type {
  DocumentAlert,
  DocumentHealth,
  DocumentItem,
  DocumentListResponse,
  DocumentScanResult,
  DocumentSearchResponse,
} from "./documents";
import type {
  PriceCompareResponse,
  PriceSearchParams,
  PriceSearchResponse,
} from "./prices";
import type {
  NotificationListResponse,
  RoutingPreview,
  Task,
  TaskListResponse,
  WorkHub,
} from "./tasks";
import type {
  OdooCompaniesResponse,
  OdooCompanyContext,
  OdooMe,
  OdooUserMapping,
  OdooCustomer,
  OdooCustomerDetail,
  OdooInvoiceDetail,
  OdooProductDetail,
  OdooVendor,
  OdooVendorDetail,
  OdooHealth,
  OdooInvoice,
  OdooListResponse,
  OdooOpportunity,
  OdooProduct,
  OdooProject,
  OdooQueryResponse,
  OdooQuotation,
  OdooSaleHistoryItem,
  OdooSummary,
} from "./odoo";
import type {
  CalendarWindowResponse,
  ComparisonResponse,
  DateQueryResponse,
  DrawsWindowResponse,
  FrequencyResponse,
  LotteryAdminBulkResponse,
  LotteryAdminLottery,
  LotteryCatalogResponse,
  LotteryChatMessage,
  LotteryChatSendResponse,
  LotteryChatSession,
  LotteryDashboard,
  LotteryDashboardV2,
  LotteryDashboardV3,
  LotteryDetail,
  LotteryExportResponse,
  LotteryFavorite,
  LotteryHealth,
  LotteryListResponse,
  LotteryPreferences,
  LotteryRecentQuery,
  LotterySavedQuery,
} from "./lottery";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  getTenantId,
  setAuthTokens,
  type AuthTokens,
} from "./auth";

const REQUEST_TIMEOUT_MS = 30_000;
/** Búsqueda empresarial y asistente pueden tardar (Odoo + índice). */
const LONG_REQUEST_TIMEOUT_MS = 90_000;

/** API siempre mismo origen: gateway (:8000) o proxy Next (:3000 → /api rewrite). */
function getApiUrl(): string {
  const fallback = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  if (typeof window === "undefined") return fallback;
  return `${window.location.origin}/api/v1`;
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return false;
    try {
      const response = await fetch(`${getApiUrl()}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) return false;
      const tokens = (await response.json()) as AuthTokens;
      setAuthTokens(tokens);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export function redirectToLogin(sessionExpired = false): void {
  if (typeof window === "undefined") return;
  clearAuthTokens();
  const suffix = sessionExpired ? "?session=expired" : "";
  window.location.href = `/login${suffix}`;
}

export class ApiError extends Error {
  status: number;
  code: string;
  data?: unknown;

  constructor(status: number, code: string, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

interface LoginPayload {
  email: string;
  password: string;
  tenant_slug?: string;
}

interface TenantResponse {
  id: string;
  slug: string;
  name: string;
}

type RequestOptions = RequestInit & { timeoutMs?: number };

async function request<T>(
  path: string,
  options: RequestOptions = {},
  authenticated = false,
  retried = false,
): Promise<T> {
  const { timeoutMs = REQUEST_TIMEOUT_MS, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (authenticated) {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) {
      redirectToLogin(true);
      throw new Error("UNAUTHORIZED");
    }
    headers.Authorization = `Bearer ${token}`;
    if (tenantId) headers["X-Tenant-ID"] = tenantId;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${getApiUrl()}${path}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
    if (response.status === 401 && authenticated && !retried && !path.startsWith("/auth/")) {
      const refreshed = await tryRefreshAccessToken();
      if (refreshed) {
        return request<T>(path, options, authenticated, true);
      }
      redirectToLogin(true);
      throw new Error("UNAUTHORIZED");
    }
    if (response.status === 401) {
      throw new Error("UNAUTHORIZED");
    }
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as {
        error?: string;
        message?: string;
        detail?: string | Array<{ msg?: string }>;
      };
      const detailRaw = body.detail;
      const detail =
        typeof detailRaw === "string"
          ? detailRaw
          : Array.isArray(detailRaw)
            ? detailRaw.map((d) => d.msg).filter(Boolean).join("; ")
            : typeof detailRaw === "object" && detailRaw !== null
              ? (detailRaw as { message?: string }).message ?? "Error de validación"
              : undefined;
      const pathHint = path || "";
      const lotteryFriendly =
        pathHint.includes("/lottery/")
          ? response.status === 404
            ? "No se encontró información para esta consulta."
            : response.status === 408 || response.status === 504
              ? "La consulta está tardando más de lo esperado. Intente nuevamente."
              : "No fue posible consultar los resultados. Intente nuevamente."
          : null;
      const fallbackMessage =
        lotteryFriendly ||
        (response.status === 500
          ? "El servidor no pudo completar la operación. Intente de nuevo en unos momentos."
          : response.status === 503
            ? "El servicio no está disponible temporalmente. Intente más tarde."
            : response.status === 404
              ? "No se encontró el recurso solicitado."
              : response.status === 403
                ? "No tiene permisos para esta acción."
                : `No se pudo completar la solicitud (${response.status}).`);
      throw new ApiError(
        response.status,
        body.error ?? "API_ERROR",
        detail ?? body.message ?? fallbackMessage,
        typeof detailRaw === "object" && detailRaw !== null && !Array.isArray(detailRaw)
          ? detailRaw
          : undefined,
      );
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(
        408,
        "TIMEOUT",
        "La solicitud tardó demasiado. Intenta de nuevo en unos segundos.",
      );
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") qs.set(key, String(value));
  }
  const str = qs.toString();
  return str ? `?${str}` : "";
}

export const apiClient = {
  login: (payload: LoginPayload) =>
    request<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCurrentTenant: () => request<TenantResponse>("/tenants/current", {}, true),

  getCompanyContext: () => request<GlobalCompanyContext>("/company-context", {}, true),

  setCompanyContext: (payload: GlobalCompanyContextUpdate) =>
    request<GlobalCompanyContext>(
      "/company-context",
      { method: "PUT", body: JSON.stringify(payload) },
      true,
    ),

  getAllowedCompanies: () =>
    request<{ items: GlobalCompanyContext["allowed_companies"]; can_select_all: boolean }>(
      "/company-context/allowed",
      {},
      true,
    ),

  bulkDocuments: (payload: { ids: string[]; action: string }) =>
    request<{ action: string; affected: number; message: string; export_csv?: string }>(
      "/documents/bulk",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  bulkTasks: (payload: {
    ids: string[];
    action: string;
    status?: string;
    priority?: string;
    assigned_to_id?: string;
  }) =>
    request<{ action: string; affected: number; message: string }>(
      "/tasks/bulk",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  bulkQuoteDrafts: (payload: {
    ids: string[];
    action: string;
    status?: string;
    assigned_user_id?: string;
  }) =>
    request<{ action: string; affected: number; message: string; export_csv?: string }>(
      "/prices/quote-drafts/bulk",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  getAdminUserCompanies: (userId: string) =>
    request<{
      user_id: string;
      visible_company_ids: number[];
      visible_company_names: string[];
      available_companies: { id: number; name: string; selected: boolean }[];
      default_company_id: number | null;
      can_select_all: boolean;
      user_role: string | null;
      odoo_allowed_company_ids: number[];
    }>(`/admin/users/${userId}/companies`, {}, true),

  setAdminUserCompanies: (
    userId: string,
    payload: { visible_company_ids: number[]; default_company_id?: number; can_select_all?: boolean },
  ) =>
    request(`/admin/users/${userId}/companies`, { method: "PUT", body: JSON.stringify(payload) }, true),

  getDGCPDashboard: (filters?: { company?: OpportunityCompany; include_expired?: boolean }) =>
    request<DGCPSummary>(
      `/dgcp/dashboard${buildQuery({
        company: filters?.company,
        include_expired: filters?.include_expired,
      })}`,
      {},
      true,
    ),
  getExecutiveDashboard: () => request<ExecutiveDashboard>("/dashboard/executive", {}, true),

  getCompanies: (params?: {
    company_type?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) =>
    request<BusinessCompanyListResponse>(
      `/companies${buildQuery(params ?? {})}`,
      {},
      true,
    ),

  getCompany: (id: string) => request<BusinessCompany>(`/companies/${id}`, {}, true),

  createCompany: (data: Partial<BusinessCompany> & { name: string; company_type: string }) =>
    request<BusinessCompany>("/companies", { method: "POST", body: JSON.stringify(data) }, true),

  updateCompany: (id: string, data: Partial<BusinessCompany>) =>
    request<BusinessCompany>(`/companies/${id}`, { method: "PUT", body: JSON.stringify(data) }, true),

  deactivateCompany: (id: string) =>
    request<BusinessCompany>(`/companies/${id}/deactivate`, { method: "POST", body: "{}" }, true),

  getSupplierDashboard: () =>
    request<import("@/lib/suppliers").SupplierDashboardStats>("/suppliers/dashboard", {}, true),

  getSuppliers: (params?: {
    company_type?: string;
    status?: string;
    category_id?: string;
    brand?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) =>
    request<import("@/lib/suppliers").SupplierListResponse>(
      `/suppliers${buildQuery(params ?? {})}`,
      {},
      true,
    ),

  getSupplier: (id: string) =>
    request<import("@/lib/suppliers").Supplier>(`/suppliers/${id}`, {}, true),

  createSupplier: (data: Record<string, unknown>) =>
    request<import("@/lib/suppliers").Supplier>(
      "/suppliers",
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  updateSupplier: (id: string, data: Record<string, unknown>) =>
    request<import("@/lib/suppliers").Supplier>(
      `/suppliers/${id}`,
      { method: "PUT", body: JSON.stringify(data) },
      true,
    ),

  deleteSupplier: (id: string) =>
    request<void>(`/suppliers/${id}`, { method: "DELETE" }, true),

  markSupplierPreferred: (id: string, preferred = true) =>
    request<import("@/lib/suppliers").Supplier>(
      `/suppliers/${id}/prefer?preferred=${preferred}`,
      { method: "POST", body: "{}" },
      true,
    ),

  getSupplierCategories: () =>
    request<{ items: import("@/lib/suppliers").SupplierCategory[]; total: number }>(
      "/suppliers/categories/list",
      {},
      true,
    ),

  searchSuppliers: (payload: {
    query: string;
    company_type?: string;
    category_id?: string;
    brand?: string;
    status?: string;
    limit?: number;
  }) =>
    request<import("@/lib/suppliers").SupplierSearchResponse>(
      "/suppliers/search",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  importSuppliers: (payload: { source: string; dry_run?: boolean; rows: Record<string, unknown>[] }) =>
    request<{ created: number; updated: number; skipped: number; errors: string[] }>(
      "/suppliers/import",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  requestSupplierQuote: (
    id: string,
    payload: { subject?: string; message?: string; products?: string[]; channel?: string },
  ) =>
    request<import("@/lib/suppliers").SupplierQuoteResponse>(
      `/suppliers/${id}/request-quote`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  getSupplierPriceLists: (id: string) =>
    request<import("@/lib/suppliers").SupplierPriceListSummary[]>(
      `/suppliers/${id}/price-lists`,
      {},
      true,
    ),

  getSupplierInteractions: (id: string) =>
    request<import("@/lib/suppliers").SupplierInteraction[]>(
      `/suppliers/${id}/interactions`,
      {},
      true,
    ),

  suggestTenderSuppliers: (payload: { requirements?: string[]; description?: string; limit?: number }) =>
    request<{
      requirements: string[];
      suggestions: Array<{
        supplier: import("@/lib/suppliers").Supplier;
        score: number;
        matched_requirements: string[];
        has_price_list: boolean;
        last_quote_at?: string | null;
      }>;
    }>("/suppliers/tender-suggestions", { method: "POST", body: JSON.stringify(payload) }, true),

  getDGCPOpportunities: (filters?: {
    status?: OpportunityStatus;
    company?: OpportunityCompany;
    priority?: OpportunityPriority;
    funnel_stage?: string;
    search?: string;
    include_expired?: boolean;
    skip?: number;
    limit?: number;
  }) =>
    request<DGCPOpportunityListResponse>(
      `/dgcp/opportunities${buildQuery(filters ?? {})}`,
      { timeoutMs: LONG_REQUEST_TIMEOUT_MS },
      true,
    ),

  getDGCPOpportunity: (id: string) =>
    request<DGCPOpportunity>(`/dgcp/opportunities/${id}`, {}, true),

  updateDGCPOpportunity: (id: string, data: { status?: OpportunityStatus; notes?: string }) =>
    request<DGCPOpportunity>(
      `/dgcp/opportunities/${id}`,
      { method: "PATCH", body: JSON.stringify(data) },
      true,
    ),

  applyDGCPAction: (id: string, action: OpportunityAction, notes?: string) =>
    request<DGCPOpportunity>(
      `/dgcp/opportunities/${id}/actions`,
      { method: "POST", body: JSON.stringify({ action, notes }) },
      true,
    ),

  retryDGCPOdooSync: (id: string) =>
    request<{
      opportunity_id: string;
      code: string;
      odoo_sync?: Record<string, unknown>;
      result?: { ok?: boolean; error?: string; status?: string };
    }>(`/dgcp/opportunities/${id}/odoo-sync/retry`, { method: "POST", body: "{}" }, true),

  getDGCPOdooProductMatches: (id: string) =>
    request<{
      opportunity_id: string;
      code: string;
      lines?: Array<Record<string, unknown>>;
      summary?: Record<string, number>;
    }>(`/dgcp/opportunities/${id}/odoo-product-matches`, {}, true),

  runDGCPOdooProductMatches: (id: string) =>
    request<{
      opportunity_id: string;
      ok?: boolean;
      lines?: Array<Record<string, unknown>>;
      summary?: Record<string, number>;
      error?: string;
    }>(`/dgcp/opportunities/${id}/odoo-product-matches/run`, { method: "POST", body: "{}" }, true),

  decideDGCPOdooProductMatch: (
    id: string,
    lineNumber: number,
    opts: { approve?: boolean; productId?: number } = {},
  ) =>
    request<{
      opportunity_id: string;
      ok?: boolean;
      line?: Record<string, unknown>;
      summary?: Record<string, number>;
      error?: string;
    }>(
      `/dgcp/opportunities/${id}/odoo-product-matches/${lineNumber}/decision${buildQuery({
        approve: opts.approve ?? true,
        product_id: opts.productId,
      })}`,
      { method: "POST", body: "{}" },
      true,
    ),

  getDGCPOpportunityHistory: (id: string) =>
    request<DGCPOpportunityHistory[]>(`/dgcp/opportunities/${id}/history`, {}, true),

  getDGCPRequirements: (id: string) =>
    request<import("@/lib/dgcp").DGCPRequirements>(`/dgcp/opportunities/${id}/requirements`, {}, true),

  analyzeDGCPRequirements: (id: string) =>
    request<{
      opportunity_id: string;
      requirements: import("@/lib/dgcp").DGCPRequirements;
      checklist: import("@/lib/dgcp").DGCPChecklist;
      bid_package: import("@/lib/dgcp").DGCPBidPackage;
      document_matches: import("@/lib/dgcp").DGCPDocumentMatches;
      process_documents?: import("@/lib/dgcp").DGCPProcessDocument[];
      alerts?: import("@/lib/dgcp").DGCPBidAlert[];
      analysis_warnings?: string[];
      expediente_status?: string;
      pliego_analysis?: Record<string, unknown> | null;
    }>(`/dgcp/opportunities/${id}/requirements/analyze`, { method: "POST", body: "{}" }, true),

  getDGCPPliegoAnalysis: (id: string) =>
    request<{
      opportunity_id: string;
      current: Record<string, unknown> | null;
      versions: Array<Record<string, unknown>>;
    }>(`/dgcp/opportunities/${id}/pliego-analysis`, {}, true),

  runDGCPPliegoAnalysis: (id: string, force = true) =>
    request<{
      opportunity_id: string;
      current: Record<string, unknown> | null;
      versions: Array<Record<string, unknown>>;
    }>(
      `/dgcp/opportunities/${id}/pliego-analysis/run${force ? "?force=true" : "?force=false"}`,
      { method: "POST", body: "{}" },
      true,
    ),

  reviewDGCPPliegoField: (
    id: string,
    fieldKey: string,
    data: {
      reviewed?: boolean;
      comment?: string | null;
      corrected_value?: unknown;
      corrected_items?: unknown[];
    },
  ) =>
    request<Record<string, unknown>>(
      `/dgcp/opportunities/${id}/pliego-analysis/fields/${encodeURIComponent(fieldKey)}/review`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  getDGCPChecklist: (id: string) =>
    request<import("@/lib/dgcp").DGCPChecklist>(`/dgcp/opportunities/${id}/checklist`, {}, true),

  getDGCPBidPackage: (id: string) =>
    request<import("@/lib/dgcp").DGCPBidPackage>(`/dgcp/opportunities/${id}/bid-package`, {}, true),

  getDGCPDocumentMatches: (id: string) =>
    request<import("@/lib/dgcp").DGCPDocumentMatches>(`/dgcp/opportunities/${id}/document-matches`, {}, true),

  createDGCPChecklistTask: (opportunityId: string, itemId: string, assignee?: string, forceNew?: boolean) =>
    request<{ task_id: string; title: string; created?: boolean; existing?: boolean }>(
      `/dgcp/opportunities/${opportunityId}/checklist/${itemId}/task${buildQuery({ assignee, force_new: forceNew ? "true" : undefined })}`,
      { method: "POST" },
      true,
    ),

  manualValidateDGCPRequirement: (
    opportunityId: string,
    itemId: string,
    data: {
      status: string;
      note?: string;
      expiration_date?: string;
      evidence?: string;
    },
  ) =>
    request<{
      checklist: import("@/lib/dgcp").DGCPChecklist;
      bid_package: import("@/lib/dgcp").DGCPBidPackage;
      expediente_status: string;
    }>(
      `/dgcp/opportunities/${opportunityId}/checklist/${itemId}/manual-validation`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  addDGCPChecklistNote: (opportunityId: string, itemId: string, note: string) =>
    request<{
      checklist: import("@/lib/dgcp").DGCPChecklist;
      notes: string | null;
      note_history: Array<{ note: string; author: string; created_at: string; action: string }>;
    }>(
      `/dgcp/opportunities/${opportunityId}/checklist/${itemId}/notes`,
      { method: "POST", body: JSON.stringify({ note }) },
      true,
    ),

  associateDGCPChecklistDocument: (
    opportunityId: string,
    itemId: string,
    data: { document_id?: string; knowledge_asset_id?: string; process_document_id?: string },
  ) =>
    request<{
      checklist: import("@/lib/dgcp").DGCPChecklist;
      bid_package: import("@/lib/dgcp").DGCPBidPackage;
      expediente_status: string;
    }>(
      `/dgcp/opportunities/${opportunityId}/checklist/${itemId}/associate-document`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  unlinkDGCPChecklistDocument: (opportunityId: string, itemId: string) =>
    request<{
      checklist: import("@/lib/dgcp").DGCPChecklist;
      bid_package: import("@/lib/dgcp").DGCPBidPackage;
      expediente_status: string;
    }>(
      `/dgcp/opportunities/${opportunityId}/checklist/${itemId}/unlink-document`,
      { method: "POST", body: "{}" },
      true,
    ),

  uploadDGCPChecklistDocument: async (opportunityId: string, itemId: string, file: File) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${getApiUrl()}/dgcp/opportunities/${opportunityId}/checklist/${itemId}/upload-document`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
        },
        body: form,
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al subir documento");
    }
    return response.json() as Promise<{
      checklist: import("@/lib/dgcp").DGCPChecklist;
      bid_package: import("@/lib/dgcp").DGCPBidPackage;
      expediente_status: string;
    }>;
  },

  listKnowledgeAssets: (params: Record<string, string | number | undefined> = {}) =>
    request<{ items: import("@/lib/documents").KnowledgeAssetItem[]; total: number }>(
      `/knowledge/assets${buildQuery(params)}`,
      {},
      true,
    ),

  getDGCPDocumentPreview: (opportunityId: string, itemId: string) =>
    request<{
      requirement_label: string;
      document_title: string | null;
      relative_path: string | null;
      extracted_text: string | null;
      download_url: string | null;
      preview_url: string | null;
      validity_analysis: Record<string, unknown> | null;
      metadata: Record<string, unknown>;
    }>(`/dgcp/opportunities/${opportunityId}/checklist/${itemId}/document-preview`, {}, true),

  previewDGCPForm: (opportunityId: string, formType = "SNCC.F042", company = "justech") =>
    request<import("@/lib/dgcp").DGCPFormPreview>(
      `/dgcp/opportunities/${opportunityId}/forms/preview`,
      { method: "POST", body: JSON.stringify({ form_type: formType, company }) },
      true,
    ),

  getDGCPProcessDocuments: (id: string) =>
    request<import("@/lib/dgcp").DGCPProcessDocuments>(
      `/dgcp/opportunities/${id}/process-documents`,
      {},
      true,
    ),

  getDGCPAlerts: (id: string) =>
    request<import("@/lib/dgcp").DGCPBidAlerts>(`/dgcp/opportunities/${id}/alerts`, {}, true),

  autofillDGCPForm: (opportunityId: string, formType = "SNCC.F042", company = "justech") =>
    request<import("@/lib/dgcp").DGCPFormPreview>(
      `/dgcp/opportunities/${opportunityId}/forms/autofill-preview`,
      { method: "POST", body: JSON.stringify({ form_type: formType, company }) },
      true,
    ),

  generateDGCPForm: (opportunityId: string, formType = "SNCC.F042", company = "justech") =>
    request<{
      opportunity_id: string;
      form_type: string;
      output_path: string;
      filename: string;
      fields_completed: number;
      fields_pending: number;
      overall_confidence: number;
    }>(
      `/dgcp/opportunities/${opportunityId}/forms/generate`,
      { method: "POST", body: JSON.stringify({ form_type: formType, company }) },
      true,
    ),

  getDGCPDocumentValidation: (id: string, companyKey = "justech") =>
    request<import("@/lib/dgcp").DGCPDocumentValidation>(
      `/dgcp/opportunities/${id}/bid-package/document-validation${buildQuery({ company_key: companyKey })}`,
      {},
      true,
    ),

  prepareDGCPExpediente: (id: string, companyKey = "justech") =>
    request<import("@/lib/dgcp").DGCPExpedientePrepareResult>(
      `/dgcp/opportunities/${id}/bid-package/prepare${buildQuery({ company_key: companyKey })}`,
      { method: "POST", body: "{}" },
      true,
    ),

  getDGCPExpedienteStatus: (id: string) =>
    request<import("@/lib/dgcp").DGCPExpedienteStatus>(
      `/dgcp/opportunities/${id}/bid-package/status`,
      {},
      true,
    ),

  setDGCPUserInput: (
    id: string,
    data: {
      fabricante?: string;
      plazo_entrega?: string;
      garantia?: string;
      monto?: string;
      notes?: string;
    },
  ) =>
    request<Record<string, unknown>>(
      `/dgcp/opportunities/${id}/bid-package/user-input`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  markDGCPExpedienteReady: (id: string) =>
    request<import("@/lib/dgcp").DGCPExpedienteStatus>(
      `/dgcp/opportunities/${id}/bid-package/mark-ready-review`,
      { method: "POST", body: "{}" },
      true,
    ),

  downloadDGCPExpediente: async (id: string, filename?: string): Promise<void> => {
    const { blob, filename: resolvedName } = await (async () => {
      const { fetchAuthenticatedFile } = await import("@/lib/authenticated-file");
      // Canónico operativo: real-expediente ZIP (bid-package/download puede no existir aún generado).
      try {
        const payload = await fetchAuthenticatedFile(`/dgcp/opportunities/${id}/real-expediente/download`);
        return { blob: payload.blob, filename: filename ?? payload.filename ?? `expediente_${id}.zip` };
      } catch {
        const payload = await fetchAuthenticatedFile(`/dgcp/opportunities/${id}/bid-package/download`);
        return { blob: payload.blob, filename: filename ?? `expediente_${id}.zip` };
      }
    })();
    const { downloadAuthenticatedBlob } = await import("@/lib/authenticated-file");
    downloadAuthenticatedBlob(blob, resolvedName);
  },

  getRealExpedienteStatus: (id: string) =>
    request<import("@/lib/dgcp").RealExpedienteStatus>(
      `/dgcp/opportunities/${id}/real-expediente/status`,
      {},
      true,
    ),

  validateRealExpediente: (id: string) =>
    request<import("@/lib/dgcp").RealExpedienteValidation>(
      `/dgcp/opportunities/${id}/real-expediente/validate`,
      {},
      true,
    ),

  generateRealExpediente: (id: string) =>
    request<import("@/lib/dgcp").RealExpedienteGenerateResult>(
      `/dgcp/opportunities/${id}/real-expediente/generate`,
      { method: "POST", body: "{}" },
      true,
    ),

  prepareDGCPSubmissionPackage: (id: string) =>
    request<import("@/lib/dgcp").RealExpedienteGenerateResult>(
      `/dgcp/opportunities/${id}/real-expediente/prepare-package`,
      { method: "POST", body: "{}" },
      true,
    ),

  markRealExpedienteReadyReview: (id: string) =>
    request<import("@/lib/dgcp").RealExpedienteStatus>(
      `/dgcp/opportunities/${id}/real-expediente/mark-ready-review`,
      { method: "POST", body: "{}" },
      true,
    ),

  markRealExpedienteReadyUpload: (id: string) =>
    request<import("@/lib/dgcp").RealExpedienteStatus>(
      `/dgcp/opportunities/${id}/real-expediente/mark-ready-upload`,
      { method: "POST", body: "{}" },
      true,
    ),

  getRealExpedienteManifest: (id: string) =>
    request<Record<string, unknown>>(
      `/dgcp/opportunities/${id}/real-expediente/manifest`,
      {},
      true,
    ),

  downloadRealExpedienteReport: async (id: string): Promise<void> => {
    const { fetchAuthenticatedFile, downloadAuthenticatedBlob } = await import(
      "@/lib/authenticated-file"
    );
    const { blob } = await fetchAuthenticatedFile(
      `/dgcp/opportunities/${id}/real-expediente/report`,
    );
    downloadAuthenticatedBlob(blob, "reporte_preparacion.pdf");
  },

  downloadRealExpedienteZip: async (id: string, filename?: string): Promise<void> => {
    const { fetchAuthenticatedFile, downloadAuthenticatedBlob } = await import(
      "@/lib/authenticated-file"
    );
    const { blob } = await fetchAuthenticatedFile(
      `/dgcp/opportunities/${id}/real-expediente/download`,
    );
    downloadAuthenticatedBlob(blob, filename ?? `expediente_dgcp_${id}.zip`);
  },

  reclassifyDGCPOpportunities: () =>
    request<{
      total: number;
      reclassified: number;
      unclassified: number;
      by_company: Record<string, number>;
    }>("/dgcp/reclassify", { method: "POST" }, true),

  triggerDGCPSync: (maxPages = 5, pageSize = 50) =>
    request<DGCPSyncJob>(
      "/dgcp/sync",
      {
        method: "POST",
        body: JSON.stringify({ max_pages: maxPages, page_size: pageSize }),
      },
      true,
    ),

  getDGCPProcessUpdatesDashboard: () =>
    request<import("@/lib/dgcp").DGCPProcessUpdateDashboardResponse>(
      "/dgcp/process-updates/dashboard",
      {},
      true,
    ),

  getDGCPProcessUpdates: (opportunityId: string) =>
    request<import("@/lib/dgcp").DGCPProcessUpdatesResponse>(
      `/dgcp/opportunities/${opportunityId}/process-updates`,
      {},
      true,
    ),

  getDGCPHistoricalSimilar: (opportunityId: string) =>
    request<import("./dgcp").DGCPHistoricalSimilarResponse>(
      `/dgcp/processes/${opportunityId}/historical-similar`,
      {},
      true,
    ),

  getDGCPHistoricalIntelligence: (
    opportunityId: string,
    opts?: { window_months?: number; limit?: number },
  ) => {
    const params = new URLSearchParams();
    if (opts?.window_months !== undefined) params.set("window_months", String(opts.window_months));
    if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return request<import("./dgcp").DGCPHistoricalIntelligence>(
      `/dgcp/processes/${opportunityId}/historical-intelligence${qs ? `?${qs}` : ""}`,
      {},
      true,
    );
  },

  reindexDGCPHistoricalAwards: (opts?: {
    institution_code?: string | number;
    institution_name?: string;
    max_pages?: number;
    page_size?: number;
  }) => {
    const params = new URLSearchParams();
    if (opts?.institution_code !== undefined && opts.institution_code !== null) {
      params.set("institution_code", String(opts.institution_code));
    }
    if (opts?.institution_name) params.set("institution_name", opts.institution_name);
    const qs = params.toString();
    return request<import("./dgcp").DGCPHistoricalIndexResponse>(
      `/dgcp/historical-awards/index${qs ? `?${qs}` : ""}`,
      {
        method: "POST",
        body: JSON.stringify({
          max_pages: opts?.max_pages ?? 60,
          page_size: opts?.page_size ?? 100,
        }),
      },
      true,
    );
  },

  linkDGCPProcessDocument: (
    opportunityId: string,
    data: { url: string; title?: string; doc_role?: string },
  ) =>
    request<import("@/lib/dgcp").DGCPProcessDocument>(
      `/dgcp/opportunities/${opportunityId}/process-documents/link`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  updateDGCPProcessDocumentRole: (opportunityId: string, docId: string, docRole: string) =>
    request<import("@/lib/dgcp").DGCPProcessDocument>(
      `/dgcp/opportunities/${opportunityId}/process-documents/${docId}/role`,
      { method: "PATCH", body: JSON.stringify({ doc_role: docRole }) },
      true,
    ),

  reingestDGCPProcessDocument: (opportunityId: string, docId: string) =>
    request<import("@/lib/dgcp").DGCPProcessDocument>(
      `/dgcp/opportunities/${opportunityId}/process-documents/${docId}/reingest`,
      { method: "POST", body: "{}" },
      true,
    ),

  getDGCPAnalysisStatus: (id: string) =>
    request<{
      opportunity_id: string;
      has_active_job: boolean;
      job: { id?: string; status: string; stage?: string | null; progress?: number | null; error?: string | null } | null;
    }>(`/dgcp/opportunities/${id}/analysis-status`, {}, true),

  refreshDGCPProcessDocuments: (id: string) =>
    request<{
      opportunity_id: string;
      discovered: number;
      downloaded: number;
      items: import("@/lib/dgcp").DGCPProcessDocument[];
      total: number;
      portal?: import("@/lib/dgcp").DGCPProcessDocument | null;
      message?: string;
    }>(`/dgcp/opportunities/${id}/process-documents/refresh`, { method: "POST", body: "{}" }, true),

  uploadDGCPProcessDocument: async (id: string, file: File, docRole = "pliego") => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${getApiUrl()}/dgcp/opportunities/${id}/process-documents/upload${buildQuery({ doc_role: docRole })}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
        },
        body: form,
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al subir documento");
    }
    return response.json() as Promise<{
      opportunity_id: string;
      process_document: import("@/lib/dgcp").DGCPProcessDocument;
      text_extracted: boolean;
      text_length: number;
      message?: string;
    }>;
  },

  getDGCPProcessDocumentFileUrl: (opportunityId: string, docId: string, disposition: "inline" | "attachment" = "inline") =>
    `${getApiUrl()}/dgcp/opportunities/${opportunityId}/process-documents/${docId}/file${buildQuery({ disposition })}`,

  analyzeDGCPIntelligence: (id: string) =>
    request<import("@/lib/dgcp").DGCPIntelligence>(
      `/dgcp/opportunities/${id}/intelligence/analyze`,
      { method: "POST", body: "{}" },
      true,
    ),

  getDGCPTechnicalSheets: (opportunityId: string) =>
    request<import("@/lib/dgcp").DGCPTechSheetsResponse>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets`,
      {},
      true,
    ),

  detectDGCPTechnicalSheets: (opportunityId: string, force = false) =>
    request<import("@/lib/dgcp").DGCPTechSheetsResponse & { detected_count?: number }>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/detect${buildQuery({ force: force ? "true" : undefined })}`,
      { method: "POST", body: "{}" },
      true,
    ),

  createDGCPTechnicalSheetManual: (
    opportunityId: string,
    data: { name: string; description?: string; quantity?: string; unit?: string },
  ) =>
    request<import("@/lib/dgcp").DGCPTechSheetsResponse>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/manual`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  uploadDGCPTechnicalSheetExisting: async (
    opportunityId: string,
    file: File,
    data: {
      name: string;
      description?: string;
      brand?: string;
      model?: string;
      manufacturer?: string;
      country?: string;
      warranty?: string;
      observation?: string;
      initial_status?: string;
    },
  ) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    const q = buildQuery({
      name: data.name,
      description: data.description,
      brand: data.brand,
      model: data.model,
      manufacturer: data.manufacturer,
      country: data.country,
      warranty: data.warranty,
      observation: data.observation,
      initial_status: data.initial_status || "en_elaboracion",
    });
    const response = await fetch(
      `${getApiUrl()}/dgcp/opportunities/${opportunityId}/technical-sheets/upload-existing${q}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
        },
        body: form,
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al subir ficha");
    }
    return response.json() as Promise<import("@/lib/dgcp").DGCPTechSheetsResponse>;
  },

  replaceDGCPTechnicalSheetFile: async (opportunityId: string, sheetId: string, file: File) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${getApiUrl()}/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/replace-file`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
        },
        body: form,
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al sustituir archivo");
    }
    return response.json() as Promise<import("@/lib/dgcp").DGCPTechSheetItem>;
  },

  getDGCPTechnicalSheetUploadedFileUrl: (
    opportunityId: string,
    sheetId: string,
    disposition: "inline" | "attachment" = "attachment",
  ) =>
    `${getApiUrl()}/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/uploaded-file${buildQuery({ disposition })}`,

  selectDGCPTechSheetProduct: (
    opportunityId: string,
    sheetId: string,
    data: {
      brand?: string;
      model?: string;
      manufacturer?: string;
      sku?: string;
      description?: string;
      source?: string;
    },
  ) =>
    request<import("@/lib/dgcp").DGCPTechSheetItem>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/select-product`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  generateDGCPTechSheetDraft: (opportunityId: string, sheetId: string) =>
    request<{ sheet_id: string; status: string; confidence: number }>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/generate-draft`,
      { method: "POST", body: "{}" },
      true,
    ),

  approveDGCPTechSheet: (opportunityId: string, sheetId: string) =>
    request<{ sheet_id: string; status: string }>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/approve`,
      { method: "POST", body: "{}" },
      true,
    ),

  rejectDGCPTechSheet: (opportunityId: string, sheetId: string) =>
    request<{ sheet_id: string; status: string }>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/reject`,
      { method: "POST", body: "{}" },
      true,
    ),

  exportDGCPTechSheet: (opportunityId: string, sheetId: string, fmt: "markdown" | "pdf" = "markdown") =>
    request<{ content: string; filename: string }>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/export${buildQuery({ fmt })}`,
      {},
      true,
    ),

  exportDGCPTechSheetPdf: async (opportunityId: string, sheetId: string) => {
    const { fetchAuthenticatedFile, downloadAuthenticatedBlob } = await import(
      "@/lib/authenticated-file"
    );
    const blob = await fetchAuthenticatedFile(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/export?fmt=pdf`,
    );
    downloadAuthenticatedBlob(blob, `ficha-tecnica-${sheetId}.pdf`);
  },

  addDGCPTechSheetImage: async (opportunityId: string, sheetId: string, file: File) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${getApiUrl()}/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
        },
        body: form,
      },
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al subir imagen");
    }
    return response.json() as Promise<import("@/lib/dgcp").DGCPTechSheetItem>;
  },

  removeDGCPTechSheetImage: (opportunityId: string, sheetId: string, imageId: string) =>
    request<import("@/lib/dgcp").DGCPTechSheetItem>(
      `/dgcp/opportunities/${opportunityId}/technical-sheets/${sheetId}/images/${imageId}`,
      { method: "DELETE" },
      true,
    ),

  addDGCPChecklistItem: (
    opportunityId: string,
    data: {
      name: string;
      tipo?: string;
      mandatory?: boolean;
      description?: string;
      source?: string;
      page?: string;
      due_date?: string;
      assignee?: string;
      notes?: string;
      document_type?: string;
    },
  ) =>
    request<{
      item: import("@/lib/dgcp").DGCPChecklistItem;
      checklist: import("@/lib/dgcp").DGCPChecklist;
      bid_package: import("@/lib/dgcp").DGCPBidPackage;
      expediente_status: string;
    }>(`/dgcp/opportunities/${opportunityId}/checklist/items`, { method: "POST", body: JSON.stringify(data) }, true),

  updateDGCPProcessDocumentFlags: (
    opportunityId: string,
    docId: string,
    data: { is_primary?: boolean; include_in_analysis?: boolean; doc_role?: string },
  ) =>
    request<import("@/lib/dgcp").DGCPProcessDocument>(
      `/dgcp/opportunities/${opportunityId}/process-documents/${docId}/flags`,
      { method: "PATCH", body: JSON.stringify(data) },
      true,
    ),

  getDGCPIntelligence: (id: string) =>
    request<import("@/lib/dgcp").DGCPIntelligence>(`/dgcp/opportunities/${id}/intelligence`, {}, true),

  bootstrapDGCPExpedienteContext: (opportunityId: string, opts?: { refresh?: boolean }) =>
    request<import("@/lib/dgcp-expediente-context").DGCPExpedienteContextResponse>(
      `/dgcp/opportunities/${opportunityId}/expediente-context/bootstrap`,
      { method: "POST", body: JSON.stringify({ refresh: Boolean(opts?.refresh) }) },
      true,
    ),

  searchDGCPHistoricalSimilar: (
    opportunityId: string,
    body?: { refresh?: boolean; limit?: number; extra_query?: string },
  ) =>
    request<import("./dgcp").DGCPHistoricalSimilarResponse>(
      `/dgcp/processes/${opportunityId}/historical-similar/search`,
      {
        method: "POST",
        body: JSON.stringify({
          refresh: body?.refresh ?? false,
          limit: body?.limit ?? 3,
          extra_query: body?.extra_query,
        }),
      },
      true,
    ),

  getDGCPSyncJobs: (limit = 10) =>
    request<DGCPSyncJob[]>(`/dgcp/sync/jobs${buildQuery({ limit })}`, {}, true),

  getDGCPSyncSchedule: () => request<DGCPSyncSchedule>("/dgcp/sync/schedule", {}, true),

  updateDGCPSyncSchedule: (data: Partial<DGCPSyncSchedule>) =>
    request<DGCPSyncSchedule>(
      "/dgcp/sync/schedule",
      { method: "PUT", body: JSON.stringify(data) },
      true,
    ),

  getDGCPAudit: (limit = 30) =>
    request<DGCPAuditLog[]>(`/dgcp/audit${buildQuery({ limit })}`, {}, true),

  getOdooConfig: () => request<import("@/lib/odoo").OdooConfigStatus>("/odoo/config", {}, true),

  getOdooHealth: () => request<OdooHealth>("/odoo/health", {}, true),

  getOdooDashboard: () => request<import("@/lib/odoo").OdooDashboard>("/odoo/dashboard", {}, true),

  getOdooPermissions: () =>
    request<{ permissions: import("@/lib/odoo").OdooPermissionsSummary; message?: string }>(
      "/odoo/permissions",
      {},
      true,
    ),

  syncOdooPermissions: () =>
    request<{ permissions: import("@/lib/odoo").OdooPermissionsSummary; message?: string }>(
      "/odoo/permissions/sync",
      { method: "POST" },
      true,
    ),

  getOdooFinanceSummary: () =>
    request<import("@/lib/odoo").OdooFinanceSummary>("/odoo/finance/summary", {}, true),

  getOdooPayments: (limit = 50) =>
    request<OdooListResponse<Record<string, unknown>>>(`/odoo/payments${buildQuery({ limit })}`, {}, true),

  getOdooUsers: (search = "", limit = 50) =>
    request<OdooListResponse<{ id: number; name: string; login: string; active: boolean }>>(
      `/odoo/users${buildQuery({ search, limit })}`,
      {},
      true,
    ),

  createOdooQuotation: (payload: import("@/lib/odoo").OdooCreateQuotationPayload) =>
    request<import("@/lib/odoo").OdooCreateQuotationResult>(
      "/odoo/quotations",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  createOdooTask: (payload: import("@/lib/odoo").OdooCreateTaskPayload) =>
    request<import("@/lib/odoo").OdooCreateTaskResult>(
      "/odoo/tasks",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  createOdooCustomer: (payload: { name: string; email?: string; phone?: string; vat?: string; city?: string; source?: string; source_ref?: string }) =>
    request<{ id: number; name: string; odoo_url?: string }>(
      "/odoo/customers",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  odooIntegrationAction: (payload: { action: string; source?: string; source_ref?: string; payload?: Record<string, unknown> }) =>
    request<{ ok: boolean; action: string; result: Record<string, unknown>; message?: string }>(
      "/odoo/actions",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  getOdooSummary: () => request<OdooSummary>("/odoo/summary", {}, true),

  getOdooCompanies: () => request<OdooCompaniesResponse>("/odoo/companies", {}, true),

  getOdooCompanyContext: () => request<OdooCompanyContext>("/odoo/company-context", {}, true),

  setOdooCompanyContext: (odoo_company_id: number) =>
    request<OdooCompanyContext>(
      "/odoo/company-context",
      { method: "PUT", body: JSON.stringify({ odoo_company_id }) },
      true,
    ),

  getOdooMe: () => request<OdooMe>("/odoo/me", {}, true),

  linkOdooUser: (odoo_login: string) =>
    request<OdooUserMapping>(
      "/odoo/link-user",
      { method: "POST", body: JSON.stringify({ odoo_login }) },
      true,
    ),

  unlinkOdooUser: () =>
    request<void>("/odoo/link-user", { method: "DELETE" }, true),

  getOdooCustomers: (search = "", limit = 50) =>
    request<OdooListResponse<OdooCustomer>>(
      `/odoo/customers${buildQuery({ search, limit })}`,
      {},
      true,
    ),

  getOdooProducts: (search = "", limit = 50) =>
    request<OdooListResponse<OdooProduct>>(
      `/odoo/products${buildQuery({ search, limit })}`,
      {},
      true,
    ),

  getOdooSalesHistory: (filters?: { partner_id?: number; product_id?: number; limit?: number }) =>
    request<OdooListResponse<OdooSaleHistoryItem>>(
      `/odoo/sales/history${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  getOdooOpenInvoices: (filters?: { partner_id?: number; limit?: number }) =>
    request<OdooListResponse<OdooInvoice>>(
      `/odoo/invoices/open${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  getOdooOverdueInvoices: (filters?: { partner_id?: number; limit?: number }) =>
    request<OdooListResponse<OdooInvoice>>(
      `/odoo/invoices/overdue${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  getOdooQuotations: (filters?: { partner_id?: number; limit?: number }) =>
    request<OdooListResponse<OdooQuotation>>(
      `/odoo/quotations${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  searchOdooQuotations: (filters?: Record<string, string | number | undefined>) =>
    request<OdooListResponse<OdooQuotation>>(
      `/odoo/quotations/search${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  getOdooQuotationDetail: (id: number) =>
    request<import("@/lib/odoo").OdooQuotationDetail>(`/odoo/quotations/${id}`, {}, true),

  downloadOdooQuotationPdf: async (id: number, filename: string) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const response = await fetch(`${getApiUrl()}/odoo/quotations/${id}/pdf`, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
      },
    });
    if (!response.ok) throw new ApiError(response.status, "DOWNLOAD_ERROR", "Error al descargar PDF");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },

  getDGCPEconomicOfferStatus: (opportunityId: string) =>
    request<import("@/lib/dgcp").DGCPEconomicOfferStatus>(
      `/dgcp/opportunities/${opportunityId}/economic-offer/status`,
      {},
      true,
    ),

  createDGCPEconomicOfferTask: (
    opportunityId: string,
    data: {
      customer_name?: string;
      suggested_products?: unknown[];
      notes?: string;
      assigned_to?: string;
      requirement_id?: string;
    },
  ) =>
    request<{ task_id: string; title: string; created: boolean; existing: boolean }>(
      `/dgcp/opportunities/${opportunityId}/economic-offer/create-draft-task`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  getCorporateIdentity: (companyKey?: string) =>
    request<import("@/lib/corporate-identity").CorporateIdentityOverview>(
      `/corporate-identity${companyKey ? `?company_key=${encodeURIComponent(companyKey)}` : ""}`,
      {},
      true,
    ),

  uploadCorporateSignature: async (file: File) => {
    const token = getAccessToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${getApiUrl()}/corporate-identity/upload-signature`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al subir firma");
    }
    return response.json() as Promise<{ asset: import("@/lib/corporate-identity").CorporateIdentityAsset; message: string }>;
  },

  uploadCorporateStamp: async (companyKey: string, file: File) => {
    const token = getAccessToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${getApiUrl()}/corporate-identity/upload-stamp?company_key=${encodeURIComponent(companyKey)}`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(response.status, "UPLOAD_ERROR", body.detail ?? "Error al subir sello");
    }
    return response.json() as Promise<{ asset: import("@/lib/corporate-identity").CorporateIdentityAsset; message: string }>;
  },

  previewDGCPFinalization: (
    opportunityId: string,
    data: { requirement_key: string; checklist_item_id?: string; company_key?: string },
  ) =>
    request<import("@/lib/corporate-identity").DocumentFinalizationPreview>(
      `/dgcp/opportunities/${opportunityId}/finalization/preview`,
      { method: "POST", body: JSON.stringify(data) },
      true,
    ),

  generateDGCPFinalPdf: (
    opportunityId: string,
    data: { requirement_key: string; checklist_item_id?: string; company_key?: string; regenerate?: boolean },
  ) =>
    request<{
      record: import("@/lib/corporate-identity").DocumentFinalizationRecord;
      preparation_pct?: number;
      expediente_status?: string;
      message: string;
    }>(`/dgcp/opportunities/${opportunityId}/finalization/generate`, {
      method: "POST",
      body: JSON.stringify(data),
    }, true),

  generateAllDGCPFinalPdfs: (opportunityId: string, companyKey?: string) =>
    request<{
      processed: import("@/lib/corporate-identity").DocumentFinalizationRecord[];
      skipped: { requirement_key: string; reason: string }[];
      warnings: string[];
    }>(
      `/dgcp/opportunities/${opportunityId}/finalization/generate-all${companyKey ? `?company_key=${encodeURIComponent(companyKey)}` : ""}`,
      { method: "POST", body: JSON.stringify({}) },
      true,
    ),

  listDGCPFinalizationRecords: (opportunityId: string) =>
    request<import("@/lib/corporate-identity").DocumentFinalizationRecord[]>(
      `/dgcp/opportunities/${opportunityId}/finalization/records`,
      {},
      true,
    ),

  downloadDGCPFinalPdf: async (opportunityId: string, recordId: string, filename: string) => {
    const token = getAccessToken();
    const response = await fetch(
      `${getApiUrl()}/dgcp/opportunities/${opportunityId}/finalization/${recordId}/file`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    );
    if (!response.ok) throw new ApiError(response.status, "DOWNLOAD_ERROR", "No se pudo descargar PDF final");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  getOdooOpportunities: (filters?: { partner_id?: number; limit?: number }) =>
    request<OdooListResponse<OdooOpportunity>>(
      `/odoo/opportunities${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  getOdooProjects: (filters?: { partner_id?: number; limit?: number }) =>
    request<OdooListResponse<OdooProject>>(
      `/odoo/projects${buildQuery(filters ?? {})}`,
      {},
      true,
    ),

  queryOdoo: (q: string) =>
    request<OdooQueryResponse>(`/odoo/query${buildQuery({ q })}`, {}, true),

  getOdooCustomerDetail: (id: number) =>
    request<OdooCustomerDetail>(`/odoo/customers/${id}`, {}, true),

  getOdooProductDetail: (id: number) =>
    request<OdooProductDetail>(`/odoo/products/${id}`, {}, true),

  getOdooInvoiceDetail: (id: number) =>
    request<OdooInvoiceDetail>(`/odoo/invoices/${id}`, {}, true),

  getOdooVendors: (search = "", limit = 50) =>
    request<OdooListResponse<OdooVendor>>(
      `/odoo/vendors${buildQuery({ search, limit })}`,
      {},
      true,
    ),

  getOdooVendorDetail: (id: number) =>
    request<OdooVendorDetail>(`/odoo/vendors/${id}`, {}, true),

  getM365Health: () => request<M365Health>("/m365/health", {}, true),

  getM365OAuthAuthorizeUrl: () =>
    request<{ authorize_url: string }>("/m365/oauth/authorize-url", {}, true),

  startM365OAuth: async () => {
    const { authorize_url } = await request<{ authorize_url: string }>(
      "/m365/oauth/authorize-url",
      {},
      true,
    );
    window.location.href = authorize_url;
  },

  getM365Status: () => request<M365Status>("/m365/status", {}, true),

  getM365Connection: () =>
    request<import("@/lib/m365-mail").M365ConnectionState>("/m365/connection", {}, true),

  getM365MailMessages: (params: {
    folder?: string;
    search?: string;
    account_id?: string;
    limit?: number;
  } = {}) =>
    request<import("@/lib/m365-mail").M365MailListResponse>(
      `/m365/mail/messages${buildQuery(params)}`,
      {},
      true,
    ),

  getM365MailMessage: (messageId: string, accountId?: string) =>
    request<import("@/lib/m365-mail").M365MailDetail>(
      `/m365/mail/messages/${encodeURIComponent(messageId)}${buildQuery({ account_id: accountId })}`,
      {},
      true,
    ),

  patchM365MailMessage: (
    messageId: string,
    payload: { is_read?: boolean; move_to_folder?: string },
    accountId?: string,
  ) =>
    request<{ ok: boolean; message: string }>(
      `/m365/mail/messages/${encodeURIComponent(messageId)}${buildQuery({ account_id: accountId })}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    ),

  sendM365Mail: (
    payload: {
      subject: string;
      body: string;
      to: string[];
      cc?: string[];
      attachments?: Array<{
        name: string;
        content_type?: string;
        content_base64?: string;
        source_url?: string;
        onedrive_item_id?: string;
      }>;
      save_draft?: boolean;
    },
    accountId?: string,
  ) =>
    request<{ ok: boolean; message: string }>(
      `/m365/mail/send${buildQuery({ account_id: accountId })}`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  replyM365Mail: (
    messageId: string,
    body: string,
    accountId?: string,
    replyAll = false,
  ) =>
    request<{ ok: boolean; message: string }>(
      `/m365/mail/messages/${encodeURIComponent(messageId)}/reply${buildQuery({ account_id: accountId })}`,
      { method: "POST", body: JSON.stringify({ body, reply_all: replyAll }) },
      true,
    ),

  forwardM365Mail: (messageId: string, body: string, to: string[], accountId?: string) =>
    request<{ ok: boolean; message: string }>(
      `/m365/mail/messages/${encodeURIComponent(messageId)}/forward${buildQuery({ account_id: accountId })}`,
      { method: "POST", body: JSON.stringify({ body, to }) },
      true,
    ),

  getM365MailIntelligence: (messageId: string, accountId?: string) =>
    request<import("@/lib/m365-intelligence").M365MailIntelligence>(
      `/m365/mail/messages/${encodeURIComponent(messageId)}/intelligence${buildQuery({ account_id: accountId })}`,
      {},
      true,
    ),

  createM365CalendarEvent: (
    payload: {
      subject: string;
      start: string;
      end: string;
      location?: string;
      body?: string;
      attendees?: string[];
      is_online?: boolean;
    },
    accountId?: string,
  ) =>
    request<{ ok: boolean; message: string; event_id?: string }>(
      `/m365/calendar/events${buildQuery({ account_id: accountId })}`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  updateM365CalendarEvent: (
    eventId: string,
    payload: {
      subject?: string;
      start?: string;
      end?: string;
      location?: string;
      body?: string;
    },
    accountId?: string,
  ) =>
    request<{ ok: boolean; message: string }>(
      `/m365/calendar/events/${encodeURIComponent(eventId)}${buildQuery({ account_id: accountId })}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    ),

  deleteM365CalendarEvent: (eventId: string, accountId?: string) =>
    request<{ ok: boolean; message: string }>(
      `/m365/calendar/events/${encodeURIComponent(eventId)}${buildQuery({ account_id: accountId })}`,
      { method: "DELETE" },
      true,
    ),

  syncM365Repository: (accountId?: string, source: "all" | "onedrive" | "sharepoint" = "all") =>
    request<{ ok: boolean; synced: number; classified: number; message: string }>(
      `/m365/repository/sync${buildQuery({ account_id: accountId, source })}`,
      { method: "POST" },
      true,
    ),

  getM365RepositoryFiles: (params: { category?: string; search?: string; account_id?: string; limit?: number } = {}) =>
    request<{
      items: import("@/lib/m365-intelligence").M365RepositoryFile[];
      total: number;
      categories: Record<string, number>;
      message: string;
    }>(`/m365/repository/files${buildQuery(params)}`, {}, true),

  getM365SemanticSearch: (q: string, limit = 20) =>
    request<{ query: string; hits: Record<string, unknown>[]; total: number; qdrant_ready: boolean; message: string }>(
      `/m365/search/semantic${buildQuery({ q, limit })}`,
      {},
      true,
    ),

  getM365Templates: () =>
    request<{ items: Array<{ id: string; name: string; source: string }>; total: number }>(
      "/m365/templates",
      {},
      true,
    ),

  previewM365Template: (templateType: string, companyKey = "justech") =>
    request<import("@/lib/m365-intelligence").M365TemplatePreview>(
      `/m365/templates/preview${buildQuery({ template_type: templateType, company_key: companyKey })}`,
      { method: "POST" },
      true,
    ),

  generateM365Template: (templateType: string, companyKey = "justech") =>
    request<{ ok: boolean; filename: string; content_base64: string; message: string }>(
      `/m365/templates/generate${buildQuery({ template_type: templateType, company_key: companyKey })}`,
      { method: "POST" },
      true,
    ),

  uploadM365OneDrive: async (file: File, folderId?: string, accountId?: string) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    if (folderId) form.append("folder_id", folderId);
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (tenantId) headers["X-Tenant-ID"] = tenantId;
    const url = `${getApiUrl()}/m365/onedrive/upload${buildQuery({ account_id: accountId })}`;
    const res = await fetch(url, { method: "POST", headers, body: form });
    if (!res.ok) throw new ApiError(res.status, "UPLOAD_FAILED", "Error al subir archivo");
    return res.json() as Promise<{ ok: boolean; message: string; item_id?: string; web_url?: string }>;
  },

  uploadM365SharePoint: async (driveId: string, file: File, folderId?: string, accountId?: string) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    if (folderId) form.append("folder_id", folderId);
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (tenantId) headers["X-Tenant-ID"] = tenantId;
    const url = `${getApiUrl()}/m365/sharepoint/drives/${encodeURIComponent(driveId)}/upload${buildQuery({ account_id: accountId })}`;
    const res = await fetch(url, { method: "POST", headers, body: form });
    if (!res.ok) throw new ApiError(res.status, "UPLOAD_FAILED", "Error al subir archivo");
    return res.json() as Promise<{ ok: boolean; message: string; item_id?: string; web_url?: string }>;
  },

  downloadM365MailAttachment: async (messageId: string, attachmentId: string, accountId?: string) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (tenantId) headers["X-Tenant-ID"] = tenantId;
    const url = `${getApiUrl()}/m365/mail/messages/${encodeURIComponent(messageId)}/attachments/${encodeURIComponent(attachmentId)}/download${buildQuery({ account_id: accountId })}`;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new ApiError(res.status, "DOWNLOAD_FAILED", "No se pudo descargar el adjunto");
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="([^"]+)"/);
    return { blob, filename: match?.[1] ?? "adjunto" };
  },

  getM365OutlookMessages: (search = "", limit = 50, accountId?: string) =>
    request<M365ListResponse>(
      `/m365/outlook/messages${buildQuery({ search, limit, account_id: accountId })}`,
      {},
      true,
    ),

  getM365SharePointSites: (search = "", limit = 50, accountId?: string) =>
    request<M365ListResponse>(
      `/m365/sharepoint/sites${buildQuery({ search, limit, account_id: accountId })}`,
      {},
      true,
    ),

  getM365OneDriveFiles: (params: { search?: string; folder_id?: string; limit?: number; account_id?: string } = {}) =>
    request<M365ListResponse>(`/m365/onedrive/files${buildQuery(params)}`, {}, true),

  getM365SharePointDrives: (siteId: string, accountId?: string) =>
    request<M365ListResponse>(
      `/m365/sharepoint/sites/${encodeURIComponent(siteId)}/drives${buildQuery({ account_id: accountId })}`,
      {},
      true,
    ),

  getM365SharePointItems: (
    driveId: string,
    params: { folder_id?: string; search?: string; account_id?: string } = {},
  ) =>
    request<M365ListResponse>(
      `/m365/sharepoint/drives/${encodeURIComponent(driveId)}/items${buildQuery(params)}`,
      {},
      true,
    ),

  getM365CalendarEvents: (params: { limit?: number; start?: string; end?: string; account_id?: string } = {}) =>
    request<M365ListResponse>(`/m365/calendar/events${buildQuery(params)}`, {}, true),

  getM365Teams: (limit = 50, accountId?: string) =>
    request<M365ListResponse>(`/m365/teams${buildQuery({ limit, account_id: accountId })}`, {}, true),

  getM365TeamChannels: (teamId: string, accountId?: string) =>
    request<M365ListResponse>(
      `/m365/teams/${encodeURIComponent(teamId)}/channels${buildQuery({ account_id: accountId })}`,
      {},
      true,
    ),

  getM365TeamMessages: (teamId: string, channelId: string, accountId?: string) =>
    request<M365ListResponse>(
      `/m365/teams/${encodeURIComponent(teamId)}/channels/${encodeURIComponent(channelId)}/messages${buildQuery({ account_id: accountId })}`,
      {},
      true,
    ),

  getM365Contacts: (limit = 50, accountId?: string, search = "") =>
    request<M365ListResponse>(
      `/m365/contacts${buildQuery({ limit, account_id: accountId, search })}`,
      {},
      true,
    ),

  getM365Documents: (search = "", limit = 50, accountId?: string) =>
    request<M365ListResponse>(
      `/m365/documents${buildQuery({ search, limit, account_id: accountId })}`,
      {},
      true,
    ),

  getM365Search: (q: string, limit = 25, accountId?: string) =>
    request<M365SearchResponse>(
      `/m365/search${buildQuery({ q, limit, account_id: accountId })}`,
      {},
      true,
    ),

  getM365OperativeDashboard: () =>
    request<import("@/lib/m365-operative").M365OperativeDashboard>("/m365/operative/dashboard", {}, true),

  getM365OperativeEmails: (classification?: string, limit = 50) =>
    request<import("@/lib/m365-operative").M365ProcessedEmailListResponse>(
      `/m365/operative/emails${buildQuery({ classification, limit })}`,
      {},
      true,
    ),

  syncM365OperativeInbox: () =>
    request<import("@/lib/m365-operative").M365SyncResponse>(
      "/m365/operative/sync",
      { method: "POST" },
      true,
    ),

  executeM365OperativeAction: (emailId: string, actionKey: string, params: Record<string, unknown> = {}) =>
    request<import("@/lib/m365-operative").M365ExecuteActionResponse>(
      `/m365/operative/emails/${emailId}/actions`,
      { method: "POST", body: JSON.stringify({ action_key: actionKey, params }) },
      true,
    ),

  getTasks: (params: Record<string, string | number | undefined> = {}) =>
    request<TaskListResponse>(`/tasks${buildQuery(params)}`, {}, true),

  getTask: (id: string) => request<Task>(`/tasks/${id}`, {}, true),

  createTask: (payload: Record<string, unknown>) =>
    request<Task>("/tasks", { method: "POST", body: JSON.stringify(payload) }, true),

  createTaskFromEvent: (payload: Record<string, unknown>) =>
    request<Task>("/tasks/from-event", { method: "POST", body: JSON.stringify(payload) }, true),

  updateTask: (id: string, payload: Record<string, unknown>) =>
    request<Task>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) }, true),

  deleteTask: (id: string) =>
    request<void>(`/tasks/${id}`, { method: "DELETE" }, true),

  addTaskComment: (id: string, comment: string) =>
    request<Task>(`/tasks/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }, true),

  addTaskChecklistItem: (id: string, text: string) =>
    request<Task>(`/tasks/${id}/checklist`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }, true),

  updateTaskChecklistItem: (taskId: string, itemId: string, completed: boolean) =>
    request<Task>(`/tasks/${taskId}/checklist/${itemId}`, {
      method: "PUT",
      body: JSON.stringify({ completed }),
    }, true),

  getWorkHub: () => request<WorkHub>("/work", {}, true),

  getTenantUsers: (params: Record<string, string | number | undefined> = {}) =>
    request<{ items: { id: string; email: string; full_name: string; role: string; is_active: boolean }[]; total: number }>(
      `/users${buildQuery(params)}`,
      {},
      true,
    ),

  getPlatformAccess: () =>
    request<import("@/lib/admin").PlatformAccess>("/users/me/platform-access", {}, true),

  getSupplierIntegrationSettings: (provider: string) =>
    request<import("@/lib/settings").IntegrationDetail>(
      `/prices/connectors/suppliers/${provider}/settings`,
      {},
      true,
    ),

  updateSupplierIntegrationSettings: (
    provider: string,
    payload: { config?: Record<string, string | boolean>; secrets?: Record<string, string> },
  ) =>
    request<import("@/lib/settings").IntegrationDetail>(
      `/prices/connectors/suppliers/${provider}/settings`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  getAdminAssignableModules: () =>
    request<{ items: import("@/lib/admin").AssignableModule[] }>("/admin/assignable-modules", {}, true),

  getAdminIntegrations: () =>
    request<{
      environment: string;
      items: import("@/lib/connectors").ConnectorSummary[];
      builtin_items: import("@/lib/connectors").ConnectorSummary[];
      dynamic_items: import("@/lib/connectors").ConnectorSummary[];
    }>("/admin/integrations", {}, true),

  getAdminIntegration: (provider: string) =>
    request<import("@/lib/settings").IntegrationDetail | import("@/lib/connectors").ConnectorDetail>(
      `/admin/integrations/${provider}`,
      {},
      true,
    ),

  createConnector: (payload: import("@/lib/connectors").ConnectorCreatePayload) =>
    request<import("@/lib/connectors").ConnectorDetail>("/admin/integrations", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  updateConnector: (id: string, payload: Record<string, unknown>) =>
    request<import("@/lib/connectors").ConnectorDetail>(`/admin/integrations/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }, true),

  deleteConnector: (id: string) =>
    request<{ ok: boolean }>(`/admin/integrations/${id}`, { method: "DELETE" }, true),

  testConnector: (id: string) =>
    request<{ ok: boolean; message: string; http_status?: number; response_preview?: string; details?: Record<string, unknown> }>(
      `/admin/integrations/${id}/test`,
      { method: "POST" },
      true,
    ),

  getConnectorUserLinks: (id: string) =>
    request<import("@/lib/connectors").ConnectorSummary[]>(`/admin/integrations/${id}/user-links`, {}, true),

  createConnectorEndpoint: (id: string, payload: import("@/lib/connectors").ConnectorEndpoint) =>
    request<import("@/lib/connectors").ConnectorEndpoint>(`/admin/integrations/${id}/endpoints`, {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  testConnectorEndpoint: (id: string, endpointId: string) =>
    request<{ ok: boolean; message: string; response_preview?: string }>(
      `/admin/integrations/${id}/endpoints/${endpointId}/test`,
      { method: "POST" },
      true,
    ),

  updateAdminIntegration: (
    provider: string,
    payload: { config?: Record<string, unknown>; secrets?: Record<string, string>; delete_secrets?: string[] },
  ) =>
    request<import("@/lib/settings").IntegrationDetail>(
      `/admin/integrations/${provider}`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  testAdminIntegration: (provider: string) =>
    request<{ ok: boolean; message: string; details?: Record<string, unknown> }>(
      `/admin/integrations/${provider}/test`,
      { method: "POST" },
      true,
    ),

  disconnectAdminIntegration: (provider: string) =>
    request<import("@/lib/settings").IntegrationDetail>(
      `/admin/integrations/${provider}/disconnect`,
      { method: "POST" },
      true,
    ),

  getAdminIntegrationLogs: (provider: string, limit = 30) =>
    request<{ items: import("@/lib/settings").SettingsAuditEntry[]; total: number }>(
      `/admin/integrations/${provider}/logs${buildQuery({ limit })}`,
      {},
      true,
    ),

  /** @deprecated use getAdminIntegrations */
  getSettingsIntegrations: () =>
    request<{ environment: string; items: import("@/lib/settings").IntegrationCard[] }>(
      "/admin/integrations",
      {},
      true,
    ),

  getSettingsIntegration: (provider: string) =>
    request<import("@/lib/settings").IntegrationDetail>(`/admin/integrations/${provider}`, {}, true),

  updateSettingsIntegration: (
    provider: string,
    payload: { config?: Record<string, unknown>; secrets?: Record<string, string>; delete_secrets?: string[] },
  ) =>
    request<import("@/lib/settings").IntegrationDetail>(
      `/admin/integrations/${provider}`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  testSettingsIntegration: (provider: string) =>
    request<{ ok: boolean; message: string; details?: Record<string, unknown> }>(
      `/admin/integrations/${provider}/test`,
      { method: "POST" },
      true,
    ),

  disconnectSettingsIntegration: (provider: string) =>
    request<import("@/lib/settings").IntegrationDetail>(
      `/admin/integrations/${provider}/disconnect`,
      { method: "POST" },
      true,
    ),

  getSettingsSystemStatus: () =>
    request<{ environment: string; items: import("@/lib/settings").SystemStatusItem[] }>(
      "/settings/system-status",
      {},
      true,
    ),

  getSettingsAuditLog: (limit = 50) =>
    request<{ items: import("@/lib/settings").SettingsAuditEntry[]; total: number }>(
      `/settings/audit-log${buildQuery({ limit })}`,
      {},
      true,
    ),

  getSettingsRepositories: () =>
    request<import("@/lib/settings").RepositoryBinding[]>("/settings/repositories", {}, true),

  upsertSettingsRepository: (payload: Record<string, unknown>) =>
    request<import("@/lib/settings").RepositoryBinding>(
      "/settings/repositories",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  syncSettingsRepository: (id: string) =>
    request<{ ok: boolean; indexed: number; records_indexed?: number; job_id?: string; message: string }>(
      `/settings/repositories/${id}/sync`,
      { method: "POST" },
      true,
    ),

  syncAllSettingsRepositories: () =>
    request<{ ok: boolean; indexed: number; message: string }[]>(
      "/settings/repositories/sync-all",
      { method: "POST" },
      true,
    ),

  getRepositorySyncJobs: (limit = 50) =>
    request<import("@/lib/settings").RepositorySyncJob[]>(
      `/settings/repositories/sync-jobs${buildQuery({ limit })}`,
      {},
      true,
    ),

  getCompanyProfiles: () =>
    request<import("@/lib/settings").CompanyProfile[]>("/settings/company-profiles", {}, true),

  draftCompanyMissingEmail: (companyKey: string) =>
    request<{ subject: string; body: string; missing_fields: string[] }>(
      `/settings/company-profiles/${companyKey}/missing-email`,
      { method: "POST" },
      true,
    ),

  getPendingPriceFiles: () =>
    request<{ id: string; name: string; parent_path: string }[]>("/settings/price-inbox/pending", {}, true),

  getDocumentsHubDashboard: () =>
    request<import("@/lib/documents-hub").DocumentsHubDashboard>("/documents/dashboard", {}, true),

  getDocumentsHubGeneralRepositories: () =>
    request<import("@/lib/documents-hub").GeneralRepositoryCard[]>(
      "/documents/repositories/general",
      {},
      true,
    ),

  syncDocumentsHubOneDrive: () =>
    request<{ synced: unknown[]; errors: string[] }>("/documents/sync/onedrive", { method: "POST" }, true),

  getDocumentsHubTracking: () =>
    request<import("@/lib/documents-hub").DocumentsTrackingSummary>("/documents/tracking", {}, true),

  getDocumentsHubCompanies: () =>
    request<import("@/lib/documents-hub").CompanyDocumentProfile[]>("/documents/companies", {}, true),

  getDocumentsHubCompany: (id: string) =>
    request<import("@/lib/documents-hub").CompanyDocumentProfile>(`/documents/companies/${id}`, {}, true),

  updateDocumentsHubCompany: (id: string, payload: Record<string, unknown>) =>
    request<import("@/lib/documents-hub").CompanyDocumentProfile>(`/documents/companies/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }, true),

  getDocumentsHubMissing: (id: string) =>
    request<import("@/lib/documents-hub").MissingItems>(`/documents/companies/${id}/missing`, {}, true),

  requestDocumentsHubMissing: (id: string, payload: Record<string, unknown>) =>
    request<import("@/lib/documents-hub").RequestMissingResult>(
      `/documents/companies/${id}/request-missing`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  generateDocumentsProfileForm: (id: string) =>
    request<import("@/lib/documents-hub").ProfileFormResult>(
      `/documents/companies/${id}/profile-form`,
      { method: "POST" },
      true,
    ),

  getDocumentsHubCompletion: (id: string) =>
    request<import("@/lib/documents-hub").CompanyCompletion>(
      `/documents/companies/${id}/completion`,
      {},
      true,
    ),

  getCompanyRepresentatives: (companyId: string) =>
    request<import("@/lib/company-representatives").RepresentativesSummary>(
      `/documents/companies/${companyId}/representatives`,
      {},
      true,
    ),

  createCompanyRepresentative: (
    companyId: string,
    payload: import("@/lib/company-representatives").RepresentativeCreatePayload,
    forceNew = false,
  ) =>
    request<import("@/lib/company-representatives").CompanyRepresentative>(
      `/documents/companies/${companyId}/representatives${buildQuery({ force_new: forceNew || undefined })}`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  updateCompanyRepresentative: (
    companyId: string,
    representativeId: string,
    payload: Partial<import("@/lib/company-representatives").RepresentativeCreatePayload>,
  ) =>
    request<import("@/lib/company-representatives").CompanyRepresentative>(
      `/documents/companies/${companyId}/representatives/${representativeId}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      true,
    ),

  deactivateCompanyRepresentative: (companyId: string, representativeId: string) =>
    request<import("@/lib/company-representatives").CompanyRepresentative>(
      `/documents/companies/${companyId}/representatives/${representativeId}`,
      { method: "DELETE" },
      true,
    ),

  deleteCompanyRepresentativePermanent: (companyId: string, representativeId: string) =>
    request<{ ok?: boolean }>(
      `/documents/companies/${companyId}/representatives/${representativeId}/permanent`,
      { method: "DELETE" },
      true,
    ),

  assignCompanyPersonRole: (
    companyId: string,
    representativeId: string,
    roleType: string,
    canSign?: boolean,
  ) =>
    request<import("@/lib/company-representatives").CompanyRepresentative>(
      `/documents/companies/${companyId}/representatives/${representativeId}/assign-role${buildQuery({
        role_type: roleType,
        can_sign: canSign ?? false,
      })}`,
      { method: "POST" },
      true,
    ),

  linkCompanyProfilePerson: (companyId: string, fieldKey: string, personId: string) =>
    request<{ ok?: boolean; message: string }>(
      `/documents/companies/${companyId}/profile-fields/${encodeURIComponent(fieldKey)}/link-person${buildQuery({
        person_id: personId,
      })}`,
      { method: "POST" },
      true,
    ),

  validateRepresentativeDocument: (
    companyId: string,
    representativeId: string,
    documentType: string,
    payload: { validation_status?: string; validation_notes?: string; validation_method?: string },
  ) =>
    request<{
      ok: boolean;
      message: string;
      document: import("@/lib/company-representatives").RepresentativeDocument;
    }>(
      `/documents/companies/${companyId}/representatives/${representativeId}/documents/${encodeURIComponent(documentType)}/validate`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  updateDocumentsHubField: (id: string, fieldKey: string, value: string) =>
    request<import("@/lib/documents-hub").CompanyDocumentProfile>(
      `/documents/companies/${id}/fields/${encodeURIComponent(fieldKey)}`,
      { method: "POST", body: JSON.stringify({ value }) },
      true,
    ),

  requestDocumentsHubMissingFields: (id: string, payload: Record<string, unknown>) =>
    request<import("@/lib/documents-hub").RequestMissingResult>(
      `/documents/companies/${id}/missing/request`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  syncDocumentsHubCompanyOneDrive: (id: string) =>
    request<{ synced: unknown[]; errors: string[]; company_key: string }>(
      `/documents/companies/${id}/onedrive/sync`,
      { method: "POST" },
      true,
    ),

  uploadDocumentsHubCompanyDocument: async (id: string, fieldKey: string, file: File, validUntil?: string) => {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) throw new Error("UNAUTHORIZED");
    const form = new FormData();
    form.append("file", file);
    form.append("field_key", fieldKey);
    if (validUntil) form.append("valid_until", validUntil);
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (tenantId) headers["X-Tenant-ID"] = tenantId;
    const res = await fetch(
      `${getApiUrl()}/documents/companies/${id}/documents/upload`,
      { method: "POST", headers, body: form },
    );
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string; message?: string };
      const msg =
        body.detail ??
        body.message ??
        "No se pudo subir a OneDrive. Verifique conexión Microsoft 365 y permisos Files.ReadWrite.All.";
      throw new ApiError(res.status, "UPLOAD_FAILED", msg);
    }
    return res.json() as Promise<import("@/lib/documents-hub").CompanyDocumentUploadResult>;
  },

  getDocumentsHubRepositories: () =>
    request<import("@/lib/settings").RepositoryBinding[]>("/documents/repositories", {}, true),

  syncDocumentsHubRepository: (id: string) =>
    request<{ ok: boolean; message: string; indexed: number }>(
      `/documents/repositories/${id}/sync`,
      { method: "POST" },
      true,
    ),

  getDocumentsHubPending: (params: Record<string, string | undefined> = {}) =>
    request<import("@/lib/documents-hub").DocumentPendingItem[]>(
      `/documents/pending${buildQuery(params)}`,
      {},
      true,
    ),

  scanDocumentsHubPending: () =>
    request<{ created: number }>("/documents/pending/scan", { method: "POST" }, true),

  markDocumentsPendingReceived: (id: string) =>
    request<import("@/lib/documents-hub").DocumentPendingItem>(
      `/documents/pending/${id}/received`,
      { method: "POST" },
      true,
    ),

  getDocumentsHubLegal: () =>
    request<import("@/lib/licitador").LegalDocumentsDashboard>("/documents/legal", {}, true),

  getDocumentsHubTemplates: () =>
    request<import("@/lib/licitador").DgcpTemplatesDashboard>("/documents/templates/dgcp", {}, true),

  getDocumentsHubPrices: () =>
    request<import("@/lib/licitador").PriceIntelligenceDashboard>("/documents/prices/intelligence", {}, true),

  getDocumentsHubCorporateIdentity: (companyKey: string) =>
    request<Record<string, unknown>>(`/documents/corporate-identity/${companyKey}`, {}, true),

  getLicitadorLegalDashboard: () =>
    request<import("@/lib/licitador").LegalDocumentsDashboard>("/licitador/documentos-legales", {}, true),

  getLicitadorTemplatesDashboard: () =>
    request<import("@/lib/licitador").DgcpTemplatesDashboard>("/licitador/plantillas", {}, true),

  getLicitadorPriceDashboard: () =>
    request<import("@/lib/licitador").PriceIntelligenceDashboard>("/licitador/precios", {}, true),

  requestLegalUpdateEmail: (companyKey: string) =>
    request<{ subject: string; body: string }>(
      `/licitador/documentos-legales/${companyKey}/solicitar-actualizacion`,
      { method: "POST" },
      true,
    ),

  previewLicitadorTemplate: (templateType: string, companyKey: string) =>
    request<import("@/lib/licitador").TemplatePreview>(
      `/licitador/plantillas/preview${buildQuery({ template_type: templateType, company_key: companyKey })}`,
      { method: "POST" },
      true,
    ),

  getLotteryHealth: () => request<LotteryHealth>("/lottery/health", {}, true),

  getLotteryLotteries: (
    limit = 50,
    offset = 0,
    filters?: {
      searchable_only?: boolean;
      visible_only?: boolean;
      ai_only?: boolean;
      comparable_only?: boolean;
      include_aggregates?: boolean;
      featured_only?: boolean;
      include_archived?: boolean;
    },
  ) =>
    request<LotteryListResponse>(
      `/lottery/lotteries${buildQuery({
        limit,
        offset,
        searchable_only: filters?.searchable_only,
        visible_only: filters?.visible_only,
        ai_only: filters?.ai_only,
        comparable_only: filters?.comparable_only,
        include_aggregates: filters?.include_aggregates,
        featured_only: filters?.featured_only ?? true,
        include_archived: filters?.include_archived,
      })}`,
      {},
      true,
    ),

  getLotteryDashboardV2: (params?: { from_date?: string; to_date?: string }) =>
    request<LotteryDashboardV2>(`/lottery/dashboard/v2${buildQuery(params ?? {})}`, {}, true),
  getLotteryDashboardV3: (params?: { from_date?: string; to_date?: string }) =>
    request<LotteryDashboardV3>(`/lottery/dashboard/v3${buildQuery(params ?? {})}`, {}, true),

  getLotteryCatalog: (params: {
    q?: string;
    country?: string;
    featured_only?: boolean;
    favorites_only?: boolean;
    include_archived?: boolean;
    page?: number;
    page_size?: number;
  }) =>
    request<LotteryCatalogResponse>(
      `/lottery/catalog${buildQuery({ featured_only: true, ...params })}`,
      {},
      true,
    ),

  getLotteryAdminLotteries: (params?: {
    q?: string;
    active?: boolean;
    visible?: boolean;
    sync_enabled?: boolean;
    featured?: boolean | null;
    limit?: number;
    offset?: number;
  }) => request<LotteryAdminLottery[]>(`/lottery/admin/lotteries${buildQuery(params ?? {})}`, {}, true),

  patchLotteryAdminLottery: (id: string, body: Record<string, unknown>) =>
    request<LotteryAdminLottery>(`/lottery/admin/lotteries/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, true),

  postLotteryAdminLotteriesBulk: (body: {
    lottery_ids: string[];
    action: string;
    display_order?: number;
  }) =>
    request<LotteryAdminBulkResponse>("/lottery/admin/lotteries/bulk", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryByDate: (params: { lottery: string; date: string; game?: string }) =>
    request<DateQueryResponse>(`/lottery/results/by-date${buildQuery(params)}`, {}, true),

  getLotteryFollowingDays: (params: {
    lottery: string;
    date: string;
    days: number;
    include_base_date?: boolean;
  }) =>
    request<CalendarWindowResponse>(
      `/lottery/results/following-days${buildQuery(params)}`,
      {},
      true,
    ),

  getLotteryFollowingDraws: (params: {
    lottery: string;
    date: string;
    count: number;
    include_base_date?: boolean;
  }) =>
    request<DrawsWindowResponse>(
      `/lottery/results/following-draws${buildQuery(params)}`,
      {},
      true,
    ),

  getLotteryFrequencies: (params: {
    lottery: string;
    from: string;
    to: string;
    limit?: number;
  }) =>
    request<FrequencyResponse>(`/lottery/statistics/frequencies${buildQuery(params)}`, {}, true),

  compareLotteries: (body: {
    lotteries: string[];
    from: string;
    to: string;
    mode: string;
    limit?: number;
  }) =>
    request<ComparisonResponse>("/lottery/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  createLotteryChatSession: (title?: string) =>
    request<LotteryChatSession>("/lottery/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title ?? null }),
    }, true),

  listLotteryChatSessions: (limit = 50) =>
    request<{ items: LotteryChatSession[]; total: number }>(
      `/lottery/chat/sessions${buildQuery({ limit })}`,
      {},
      true,
    ),

  getLotteryChatSession: (sessionId: string) =>
    request<LotteryChatSession>(`/lottery/chat/sessions/${sessionId}`, {}, true),

  deleteLotteryChatSession: (sessionId: string) =>
    request<{ ok: boolean }>(`/lottery/chat/sessions/${sessionId}`, { method: "DELETE" }, true),

  bulkDeleteLotteryChatSessions: (sessionIds: string[]) =>
    request<{ deleted_count: number; failed_ids: string[]; success: boolean }>(
      "/lottery/chat/sessions/bulk-delete",
      { method: "POST", body: JSON.stringify({ session_ids: sessionIds }) },
      true,
    ),

  deleteAllLotteryChatSessions: () =>
    request<{ deleted_count: number; failed_ids: string[]; success: boolean }>(
      "/lottery/chat/sessions/delete-all",
      { method: "POST" },
      true,
    ),

  renameLotteryChatSession: (sessionId: string, title: string) =>
    request<LotteryChatSession>(`/lottery/chat/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }, true),

  clearLotteryChatContext: (sessionId: string) =>
    request<LotteryChatSession>(`/lottery/chat/sessions/${sessionId}/clear-context`, {
      method: "POST",
    }, true),

  closeLotteryChatInvestigation: (sessionId: string) =>
    request<{
      ok: boolean;
      active_context?: Record<string, unknown>;
      context?: Record<string, unknown>;
    }>(`/lottery/chat/sessions/${sessionId}/close-investigation`, {
      method: "POST",
    }, true),

  getLotteryExplorerNumber: (number: number) =>
    request<Record<string, unknown>>(`/lottery/chat/explorer/numbers/${number}`, {}, true),

  getLotteryExplorerTable: (table: string) =>
    request<Record<string, unknown>>(`/lottery/chat/explorer/tables/${table}`, {}, true),

  compareLotteryExplorer: (numbers: Array<string | number>) =>
    request<Record<string, unknown>>(`/lottery/chat/explorer/compare`, {
      method: "POST",
      body: JSON.stringify({ numbers }),
    }, true),

  navigateLotteryExplorer: (
    sessionId: string,
    body: {
      action: string;
      number?: string | number | null;
      view?: string | null;
      label?: string | null;
      crumb_id?: string | null;
      origin?: string;
    },
  ) =>
    request<{
      ok: boolean;
      action?: string;
      active_context?: Record<string, unknown>;
      explorer?: Record<string, unknown>;
      card?: Record<string, unknown> | null;
      table?: Record<string, unknown> | null;
      compare?: Record<string, unknown> | null;
      context?: Record<string, unknown>;
      suggested_prompt?: string | null;
    }>(`/lottery/chat/sessions/${sessionId}/explorer/navigate`, {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  listLotteryChatMessages: (sessionId: string, limit = 50, offset = 0) =>
    request<{ items: LotteryChatMessage[]; total: number }>(
      `/lottery/chat/sessions/${sessionId}/messages${buildQuery({ limit, offset })}`,
      {},
      true,
    ),

  sendLotteryChatMessage: (sessionId: string, content: string) =>
    request<LotteryChatSendResponse>(`/lottery/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }, true),

  retryLotteryChatMessage: (sessionId: string) =>
    request<LotteryChatSendResponse>(`/lottery/chat/sessions/${sessionId}/retry`, {
      method: "POST",
    }, true),

  listLotterySavedQueries: () =>
    request<{ items: LotterySavedQuery[]; total: number }>("/lottery/saved-queries", {}, true),

  renameLotterySavedQuery: (queryId: string, name: string) =>
    request<LotterySavedQuery>(`/lottery/saved-queries/${queryId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }, true),

  deleteLotterySavedQuery: (queryId: string) =>
    request<{ ok: boolean }>(`/lottery/saved-queries/${queryId}`, { method: "DELETE" }, true),

  getLotteryHomeHint: () =>
    request<{ role: string; is_lottery_client: boolean; home_path: string }>(
      "/lottery/me/home",
      {},
      true,
    ),

  getLotteryDashboard: () => request<LotteryDashboard>("/lottery/dashboard", {}, true),

  getLotteryDetail: (slug: string) =>
    request<LotteryDetail>(`/lottery/lotteries/${encodeURIComponent(slug)}`, {}, true),

  listLotteryFavorites: () =>
    request<{ items: LotteryFavorite[]; total: number }>("/lottery/favorites", {}, true),

  addLotteryFavorite: (lotteryId: string) =>
    request<LotteryFavorite>(`/lottery/favorites/${lotteryId}`, { method: "POST" }, true),

  removeLotteryFavorite: (lotteryId: string) =>
    request<{ ok: boolean }>(`/lottery/favorites/${lotteryId}`, { method: "DELETE" }, true),

  listLotteryRecentQueries: () =>
    request<{ items: LotteryRecentQuery[]; total: number }>("/lottery/recent-queries", {}, true),

  getLotteryPreferences: () => request<LotteryPreferences>("/lottery/preferences", {}, true),

  patchLotteryPreferences: (body: Partial<LotteryPreferences>) =>
    request<LotteryPreferences>("/lottery/preferences", {
      method: "PATCH",
      body: JSON.stringify(body),
    }, true),

  createLotteryExport: (body: {
    query_type: string;
    query_parameters: Record<string, unknown>;
    format: "csv" | "xlsx" | "pdf";
    title?: string;
  }) =>
    request<LotteryExportResponse>("/lottery/exports", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  downloadLotteryExport: async (exportId: string, filename?: string): Promise<void> => {
    const { fetchAuthenticatedFile, downloadAuthenticatedBlob } = await import(
      "@/lib/authenticated-file"
    );
    const { blob, filename: resolved } = await fetchAuthenticatedFile(
      `/lottery/exports/${exportId}/download`,
    );
    downloadAuthenticatedBlob(blob, filename ?? resolved);
  },

  getLotteryObservability: () =>
    request<Record<string, unknown>>("/lottery/observability", {}, true),

  getLotteryResultados: (params: Record<string, string> = {}) =>
    request<{ items: unknown[]; total: number; filters?: Record<string, unknown> }>(
      `/lottery/resultados${buildQuery(params)}`,
      {},
      true,
    ),

  getLotteryResultadosLotteries: () =>
    request<{ items: { id: string; name: string; slug?: string }[]; total: number }>(
      "/lottery/resultados/lotteries",
      {},
      true,
    ),

  getLotteryResultadosSyncStatus: () =>
    request<Record<string, unknown>>("/lottery/resultados/sync-status", {}, true),

  getLotteryResultadosPending: (date?: string) =>
    request<Record<string, unknown>>(
      `/lottery/resultados/pending${date ? buildQuery({ date }) : ""}`,
      {},
      true,
    ),

  triggerLotteryResultadosSync: () =>
    request<Record<string, unknown>>("/lottery/resultados/sync/trigger", { method: "POST" }, true),

  getLotteryIaDashboard: () =>
    request<Record<string, unknown>>("/lottery/ia/dashboard", {}, true),

  getLotteryIaMotorFreeze: () =>
    request<Record<string, unknown>>("/lottery/ia/motor-freeze", {}, true),

  getLotteryAdminSyncRuns: () =>
    request<{ items: unknown[]; total: number }>("/lottery/admin/sync/runs", {}, true),

  postLotteryAdminSyncDryRun: (body: {
    source?: string;
    from_date?: string;
    to_date?: string;
    lottery_source_id?: number;
    limit?: number;
  }) =>
    request<Record<string, unknown>>("/lottery/admin/sync/dry-run", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryAdminScheduler: () =>
    request<Record<string, unknown>>("/lottery/admin/scheduler", {}, true),

  postLotteryAdminSchedulerRunNow: (source = "fixture") =>
    request<Record<string, unknown>>(
      `/lottery/admin/scheduler/run-now?source=${encodeURIComponent(source)}`,
      { method: "POST" },
      true,
    ),

  postLotteryAdminSchedulerDisable: () =>
    request<Record<string, unknown>>("/lottery/admin/scheduler/disable", { method: "POST" }, true),

  postLotteryAdminSchedulerEnable: (mode = "observe") =>
    request<Record<string, unknown>>(
      `/lottery/admin/scheduler/enable?mode=${encodeURIComponent(mode)}`,
      { method: "POST" },
      true,
    ),

  postLotteryAdminSchedulerSetMode: (mode: string, confirmation?: string) => {
    const q = new URLSearchParams({ mode });
    if (confirmation) q.set("confirmation", confirmation);
    return request<Record<string, unknown>>(
      `/lottery/admin/scheduler/set-mode?${q.toString()}`,
      { method: "POST" },
      true,
    );
  },

  getLotteryAdminSchedulerAlerts: () =>
    request<{ items: unknown[] }>("/lottery/admin/scheduler/alerts", {}, true),

  postLotteryAdminCircuitReset: () =>
    request<Record<string, unknown>>(
      "/lottery/admin/scheduler/circuit-breaker/reset",
      { method: "POST" },
      true,
    ),

  getAdminAccess: () =>
    request<import("@/lib/admin").AdminAccess>("/admin/access", {}, true),

  getAdminUsers: () =>
    request<{ items: import("@/lib/admin").AdminUser[]; total: number }>("/admin/users", {}, true),

  createAdminUser: (payload: Record<string, unknown>) =>
    request<import("@/lib/admin").AdminUser>("/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  updateAdminUser: (id: string, payload: Record<string, unknown>) =>
    request<import("@/lib/admin").AdminUser>(`/admin/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }, true),

  disableAdminUser: (id: string) =>
    request<void>(`/admin/users/${id}/disable`, { method: "POST" }, true),

  getAdminModules: () =>
    request<{ items: import("@/lib/admin").TenantModule[] }>("/admin/modules", {}, true),

  updateAdminModule: (key: string, is_enabled: boolean) =>
    request<import("@/lib/admin").TenantModule>(`/admin/modules/${key}`, {
      method: "PUT",
      body: JSON.stringify({ is_enabled }),
    }, true),

  getAdminRoutingRules: () =>
    request<{ items: import("@/lib/admin").RoutingRuleAdmin[] }>("/admin/routing-rules", {}, true),

  updateAdminRoutingRule: (id: string, payload: Record<string, unknown>) =>
    request<import("@/lib/admin").RoutingRuleAdmin>(`/admin/routing-rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }, true),

  getAdminSettings: () =>
    request<import("@/lib/admin").TenantSettings>("/admin/settings", {}, true),

  getM365AdminConfig: () =>
    request<{
      tenant_id: string;
      client_id: string;
      client_secret_configured: boolean;
      client_secret_masked: string;
      redirect_uri: string;
      webhook_url: string;
      webhook_client_state_configured: boolean;
      read_only: boolean;
      oauth_ready: boolean;
      source: string;
    }>("/admin/m365/config", {}, true),

  updateM365AdminConfig: (payload: { client_secret?: string; webhook_client_state?: string }) =>
    request<{
      tenant_id: string;
      client_id: string;
      client_secret_configured: boolean;
      client_secret_masked: string;
      redirect_uri: string;
      webhook_url: string;
      webhook_client_state_configured: boolean;
      read_only: boolean;
      oauth_ready: boolean;
      source: string;
    }>("/admin/m365/config", { method: "PUT", body: JSON.stringify(payload) }, true),

  testM365Connection: () =>
    request<{
      ok: boolean;
      message: string;
      token_acquired?: boolean;
      graph_reachable?: boolean;
      user_display_name?: string | null;
    }>("/admin/m365/test-connection", { method: "POST" }, true),

  getM365GraphPermissions: () =>
    request<{
      delegated_scopes: { scope: string; required: boolean; description: string }[];
      application_scopes: { scope: string; required: boolean; description: string }[];
      admin_consent_required: boolean;
    }>("/admin/m365/graph-permissions", {}, true),

  renewM365Webhooks: () =>
    request<{ ok: boolean; message: string; subscription_id?: string | null; expiration?: string | null }>(
      "/admin/m365/webhooks/renew",
      { method: "POST" },
      true,
    ),

  getAdminRoles: () =>
    request<{ items: { key: string; label: string; permissions: string[] }[] }>("/admin/roles", {}, true),

  getAdminDepartments: () =>
    request<{ items: import("@/lib/admin").Department[] }>("/admin/departments", {}, true),

  getM365Accounts: () =>
    request<{ items: import("@/lib/admin").M365Account[]; total: number }>("/m365/accounts", {}, true),

  getMyM365Account: () =>
    request<import("@/lib/admin").M365Account | null>("/m365/accounts/me", {}, true),

  prepareM365Account: (payload: Record<string, unknown> = {}) =>
    request<import("@/lib/admin").M365Account>("/m365/accounts/prepare", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  connectM365Imap: (payload: {
    email: string;
    password: string;
    imap_host?: string;
    imap_port?: number;
  }) =>
    request<import("@/lib/admin").M365Account>("/m365/accounts/connect-imap", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  disconnectM365Mailbox: () =>
    request<import("@/lib/admin").M365Account>("/m365/accounts/disconnect", {
      method: "POST",
    }, true),

  deleteM365Account: (id: string) =>
    request<void>(`/m365/accounts/${id}`, { method: "DELETE" }, true),

  getNotifications: (unreadOnly = false, limit = 50) =>
    request<NotificationListResponse>(
      `/notifications${buildQuery({ unread_only: unreadOnly ? "true" : undefined, limit })}`,
      {},
      true,
    ),

  getNotificationUnreadCount: () =>
    request<{ unread_count: number }>("/notifications/unread-count", {}, true),

  markNotificationRead: (id: string) =>
    request(`/notifications/${id}/read`, { method: "POST" }, true),

  markAllNotificationsRead: () =>
    request("/notifications/read-all", { method: "POST" }, true),

  previewRouting: (payload: Record<string, unknown>) =>
    request<RoutingPreview>("/routing/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  applyRouting: (payload: Record<string, unknown>) =>
    request<Task>("/routing/apply", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  assistantQuery: (payload: AssistantQueryRequest) =>
    request<AssistantQueryResponse>(
      "/assistant/query",
      {
        method: "POST",
        body: JSON.stringify(payload),
        timeoutMs: LONG_REQUEST_TIMEOUT_MS,
      },
      true,
    ),

  getAssistantBriefing: (mode: "managerial" | "operational" | "bidding" = "managerial") =>
    request<import("@/lib/assistant").CopilotBriefingResponse>(
      `/assistant/briefing?mode=${mode}`,
      {},
      true,
    ),

  setAssistantBriefingMode: (conversationId: string, mode: "managerial" | "operational" | "bidding") =>
    request<{ status: string; mode: string }>(
      `/assistant/briefing-mode?conversation_id=${encodeURIComponent(conversationId)}&mode=${mode}`,
      { method: "PUT" },
      true,
    ),

  resetAssistantConversation: (conversationId: string) =>
    request<{ status: string }>(
      `/assistant/conversations/reset?conversation_id=${encodeURIComponent(conversationId)}`,
      { method: "POST" },
      true,
    ),

  enterpriseSearch: (params: {
    q: string;
    source?: string;
    type?: string;
    company?: string;
    limit?: number;
  }) =>
    request<EnterpriseSearchResponse>(
      `/search${buildQuery({
        q: params.q,
        source: params.source,
        type: params.type,
        company: params.company,
        limit: params.limit,
      })}`,
      { timeoutMs: LONG_REQUEST_TIMEOUT_MS },
      true,
    ),

  getDocumentsHealth: () => request<DocumentHealth>("/documents/health", {}, true),

  getKnowledgeHealth: () =>
    request<import("@/lib/documents").KnowledgeHealth>("/knowledge/health", {}, true),

  syncKnowledgeRepository: () =>
    request<{ assets_synced: number; assets_created: number; assets_updated: number; errors: string[] }>(
      "/knowledge/sync",
      { method: "POST" },
      true,
    ),

  getDocuments: (params: Record<string, string | number | undefined> = {}) =>
    request<DocumentListResponse>(`/documents${buildQuery(params)}`, {}, true),

  getDocument: (id: string) => request<DocumentItem>(`/documents/${id}`, {}, true),

  searchDocuments: (q: string, limit = 25) =>
    request<DocumentSearchResponse>(`/documents/search${buildQuery({ q, limit })}`, {}, true),

  getDocumentAlerts: (limit = 30) =>
    request<DocumentAlert[]>(`/documents/alerts${buildQuery({ limit })}`, {}, true),

  scanDocumentsFolder: (path = "") =>
    request<DocumentScanResult>(
      `/documents/scan${buildQuery({ path })}`,
      { method: "POST" },
      true,
    ),

  analyzeDocument: (id: string) =>
    request<DocumentItem>(`/documents/${id}/analyze`, { method: "POST" }, true),

  createDocumentTask: (id: string, title?: string) =>
    request<{ task_id: string; title: string }>(
      `/documents/${id}/tasks${buildQuery({ title })}`,
      { method: "POST" },
      true,
    ),

  async uploadDocument(
    file: File,
    meta: {
      title?: string;
      category?: string;
      company?: string;
      client_name?: string;
      supplier_name?: string;
    } = {},
  ): Promise<DocumentItem> {
    const token = getAccessToken();
    const tenantId = getTenantId();
    if (!token) {
      redirectToLogin(true);
      throw new Error("UNAUTHORIZED");
    }
    const form = new FormData();
    form.append("file", file);
    if (meta.title) form.append("title", meta.title);
    if (meta.category) form.append("category", meta.category);
    if (meta.company) form.append("company", meta.company);
    if (meta.client_name) form.append("client_name", meta.client_name);
    if (meta.supplier_name) form.append("supplier_name", meta.supplier_name);

    const response = await fetch(`${getApiUrl()}/documents`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
      },
      body: form,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        body.detail ?? "UPLOAD_ERROR",
        typeof body.detail === "string" ? body.detail : "Error al subir documento",
      );
    }
    return response.json() as Promise<DocumentItem>;
  },

  searchPrices: (params: PriceSearchParams = {}) =>
    request<PriceSearchResponse>(
      `/prices/search${buildQuery(params as Record<string, string | number | boolean | undefined>)}`,
      {},
      true,
    ),

  comparePrices: (params: PriceSearchParams = {}) =>
    request<PriceCompareResponse>(
      `/prices/compare${buildQuery(params as Record<string, string | number | boolean | undefined>)}`,
      {},
      true,
    ),

  comparePricesPro: (params: {
    q: string;
    cantidad?: number;
    margen_objetivo?: number;
    include_live?: boolean;
    include_omega_live?: boolean;
    include_indexed?: boolean;
    include_historical?: boolean;
    marca?: string;
    ram_gb?: number;
    almacenamiento_gb?: number;
  }) =>
    request<import("./prices").PriceCompareProResponse>(
      `/prices/compare-pro${buildQuery(params as Record<string, string | number | boolean | undefined>)}`,
      {},
      true,
    ),

  ingramConnectorStatus: () =>
    request<Record<string, unknown>>("/prices/connectors/ingram/status", {}, true),

  ingramMfaStart: () =>
    request<{
      ok: boolean;
      status: string;
      message?: string;
      session_active?: boolean;
    }>("/prices/connectors/ingram/mfa/start", { method: "POST" }, true),

  ingramMfaVerify: (pass_code: string) =>
    request<{
      ok: boolean;
      status: string;
      message?: string;
      session_active?: boolean;
      expires_at?: number;
    }>("/prices/connectors/ingram/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ pass_code }),
    }, true),

  ingramMfaDisconnect: () =>
    request<{ ok: boolean; status: string; message?: string }>(
      "/prices/connectors/ingram/mfa/disconnect",
      { method: "POST" },
      true,
    ),

  ingramLiveSearch: (q: string, limit = 20) =>
    request<import("./prices").SupplierLiveSearchResponse>(
      `/prices/connectors/ingram/search${buildQuery({ q, limit })}`,
      {},
      true,
    ),

  omegaConnectorStatus: () =>
    request<Record<string, unknown>>("/prices/connectors/omega/status", {}, true),

  omegaLogin: () =>
    request<{
      ok: boolean;
      status: string;
      message?: string;
      session_active?: boolean;
      authenticated?: boolean;
    }>("/prices/connectors/omega/login", { method: "POST" }, true),

  omegaDisconnect: () =>
    request<{ ok: boolean; status: string; message?: string; session_active?: boolean }>(
      "/prices/connectors/omega/disconnect",
      { method: "POST" },
      true,
    ),

  omegaLiveSearch: (q: string, limit = 20) =>
    request<import("./prices").SupplierLiveSearchResponse>(
      `/prices/connectors/omega/search${buildQuery({ q, limit })}`,
      {},
      true,
    ),

  analyzeDGCPrices: (opportunityId: string) =>
    request<import("./prices").DGCPPriceAnalysis>(
      `/prices/dgcp/${opportunityId}/analyze`,
      {},
      true,
    ),

  getPriceProductHistory: (productId: string) =>
    request<{
      product_id: string;
      trend: string;
      current_price: string | null;
      price_30d_ago: string | null;
      price_90d_ago: string | null;
      points: Array<{ date: string; price: string; supplier: string | null }>;
    }>(`/prices/products/${productId}/history`, {}, true),

  getPriceProduct: (id: string) =>
    request<import("./prices").PriceProductDetail>(`/prices/products/${id}`, {}, true),

  createPriceQuoteDraft: (payload: { product_id: string; client_name?: string; quantity?: number; margin_percent?: number }) =>
    request<import("./prices").PriceQuoteDraft>("/prices/quote-drafts", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  listPriceQuoteDrafts: () =>
    request<{ items: import("./prices").PriceQuoteDraft[]; total: number }>("/prices/quote-drafts", {}, true),

  getPriceOdooMatch: (productId: string) =>
    request<import("./prices").PriceOdooMatch>(`/prices/products/${productId}/odoo-match`, {}, true),

  syncPriceLists: () =>
    request<{
      files_detected: number;
      files_new: number;
      records_created: number;
      errors: string[];
    }>("/prices/sync", { method: "POST" }, true),

  getCommunicationsHubStatus: () =>
    request<import("./communications").CommunicationsHubStatus>("/communications/hub/status", {}, true),

  listWhatsappSessions: () =>
    request<{ items: import("./communications").WhatsappSession[] }>("/communications/whatsapp/sessions", {}, true),

  createWhatsappSession: (payload: { label?: string; account_type?: string }) =>
    request<import("./communications").WhatsappSession>("/communications/whatsapp/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

  getWhatsappSession: (sessionId: string) =>
    request<import("./communications").WhatsappSession>(`/communications/whatsapp/sessions/${sessionId}`, {}, true),

  disconnectWhatsappSession: (sessionId: string) =>
    request<{ status: string }>(`/communications/whatsapp/sessions/${sessionId}/disconnect`, { method: "POST" }, true),

  listWhatsappChats: (sessionId: string, sync = true) =>
    request<{ items: import("./communications").WhatsappChat[] }>(
      `/communications/whatsapp/sessions/${sessionId}/chats?sync=${sync}`,
      {},
      true,
    ),

  listWhatsappMessages: (sessionId: string, remoteJid: string) =>
    request<{ items: import("./communications").WhatsappMessage[] }>(
      `/communications/whatsapp/sessions/${sessionId}/chats/${encodeURIComponent(remoteJid)}/messages`,
      {},
      true,
    ),

  sendWhatsappMessage: (sessionId: string, remoteJid: string, text: string, quotedMessageId?: string) =>
    request<import("./communications").WhatsappMessage>(
      `/communications/whatsapp/sessions/${sessionId}/chats/${encodeURIComponent(remoteJid)}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ text, quoted_message_id: quotedMessageId }),
      },
      true,
    ),

  whatsappAiAction: (sessionId: string, payload: { action: string; chat_id?: string }) =>
    request<import("./communications").WhatsappAiActionResponse>(
      `/communications/whatsapp/sessions/${sessionId}/ai`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  getWhatsappChatIntelligence: (sessionId: string, chatId: string) =>
    request<import("./communications").WhatsappChatIntelligence>(
      `/communications/whatsapp/sessions/${sessionId}/chats/${chatId}/intelligence`,
      {},
      true,
    ),

  searchCommunications: (q: string, channel?: string, limit = 8) =>
    request<import("./communications").CommunicationsUnifiedSearchResult>(
      `/communications/search?q=${encodeURIComponent(q)}${channel ? `&channel=${channel}` : ""}&limit=${limit}`,
      {},
      true,
    ),

  listUnifiedContacts: (q = "", sync = true, limit = 50) =>
    request<{ items: import("./communications").UnifiedContact[]; total: number }>(
      `/communications/contacts?q=${encodeURIComponent(q)}&sync=${sync}&limit=${limit}`,
      {},
      true,
    ),

  syncUnifiedContacts: (limit = 80) =>
    request<{ created: number; updated: number; total: number; sources_synced: string[] }>(
      `/communications/contacts/sync?limit=${limit}`,
      { method: "POST" },
      true,
    ),

  getUnifiedContactProfile: (contactId: string) =>
    request<import("./communications").UnifiedContactProfile360>(
      `/communications/contacts/${contactId}`,
      {},
      true,
    ),

  listCommunicationsRepository: (params?: { q?: string; category?: string; source?: string; limit?: number }) =>
    request<import("./communications").CommunicationsRepositoryList>(
      `/communications/documents/repository${buildQuery({
        q: params?.q,
        category: params?.category,
        source: params?.source,
        limit: params?.limit,
      })}`,
      {},
      true,
    ),

  whatsappAttachDocument: (
    sessionId: string,
    remoteJid: string,
    payload: { source: string; item_id: string; caption?: string },
  ) =>
    request<import("./communications").CommunicationsAttachAction>(
      `/communications/whatsapp/sessions/${sessionId}/chats/${encodeURIComponent(remoteJid)}/attach`,
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  outlookAttachDocument: (payload: {
    to: string[];
    subject: string;
    body?: string;
    source: string;
    item_id: string;
    account_id?: string;
  }) =>
    request<import("./communications").CommunicationsAttachAction>(
      "/communications/outlook/attach",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  teamsShareDocument: (payload: {
    team_id: string;
    channel_id: string;
    message?: string;
    source: string;
    item_id: string;
    account_id?: string;
  }) =>
    request<import("./communications").CommunicationsAttachAction>(
      "/communications/teams/share",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  // ── Lottery AI Admin ────────────────────────────────────────────────────

  getLotteryNumericRelationsTables: () =>
    request<{
      table1: Record<string, unknown>[];
      table2: Record<string, unknown>[];
      range: { min: number; max: number };
      tables_are_separate?: boolean;
      source?: string;
    }>("/lottery/admin/numeric-relations/tables", {}, true),

  getLotteryNumericRelationsGroups: () =>
    request<{
      table1_groups: Record<string, { code: number; numbers: number[]; table: string }>;
      table2_groups: Record<string, { code: number; numbers: number[]; table: string }>;
      tables_are_separate?: boolean;
      source?: string;
    }>("/lottery/admin/numeric-relations/groups", {}, true),

  getLotteryNumericRelationsLotteries: (params?: { scope?: "active" | "archived" }) =>
    request<{
      items: { id: string; name: string; slug?: string; analysis_scope?: string }[];
      count?: number;
      analysis_scope?: string;
      user_note?: string;
      source?: string;
    }>(`/lottery/admin/numeric-relations/lotteries${buildQuery(params || { scope: "active" })}`, {}, true),

  getLotteryNumericRelationsNumber: (n: number, table: "table1" | "table2") =>
    request<Record<string, unknown>>(
      `/lottery/admin/numeric-relations/numbers/${n}?table=${encodeURIComponent(table)}`,
      {},
      true,
    ),

  getLotteryNumericRelationsExport: (table: "table1" | "table2", format: "json" | "csv") =>
    request<{
      table: string;
      format: string;
      count: number;
      items?: Record<string, unknown>[];
      csv?: string;
      read_only?: boolean;
    }>(
      `/lottery/admin/numeric-relations/export?table=${encodeURIComponent(table)}&format=${encodeURIComponent(format)}`,
      {},
      true,
    ),

  postLotteryNumericRelationsAnalyze: (body: {
    observed_number: number;
    lottery_ids: string[];
    occurrence_mode: "last_k" | "all";
    occurrence_k?: number | null;
  }) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/analyze", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  /** Motor Validation Lab — explain-only; does not modify NR formulas. */
  postLotteryNumericRelationsValidationLab: (body: {
    observations: Array<{ number: number; lottery_name?: string; lottery_id?: string }>;
    manual_fuerte?: number | null;
    date?: string | null;
  }) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/validation-lab", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNumericRelationsHistoricalAudit: (body: Record<string, unknown> = {}) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/historical-audit", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryNumericRelationsHistoricalAudit: (auditId: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/numeric-relations/historical-audit/${encodeURIComponent(auditId)}`,
      undefined,
      true,
    ),

  getLotteryNumericRelationsHistoricalAuditCases: (
    auditId: string,
    params?: { page?: number; page_size?: number; verdict?: string },
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.verdict) q.set("verdict", params.verdict);
    const qs = q.toString();
    return request<Record<string, unknown>>(
      `/lottery/admin/numeric-relations/historical-audit/${encodeURIComponent(auditId)}/cases${qs ? `?${qs}` : ""}`,
      undefined,
      true,
    );
  },

  getLotteryNumericRelationsFourYearAuditSummary: () =>
    request<Record<string, unknown>>(
      "/lottery/admin/numeric-relations/historical-audit/four-year/summary",
      undefined,
      true,
    ),

  postLotteryNrHistoryConditions: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/conditions/search", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryPosterior: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/posterior/summary", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryCombinations: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/combinations", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryMatrix: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/matrix", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryPatternDetail: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/patterns/detail", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryCycles: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/cycles", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryCompare: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrHistoryEvidenceByDraw: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/evidence/by-draw", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrNumberProfile: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/numbers/profile", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrNumberOccurrences: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/numbers/occurrences", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrNumberOccurrenceDetail: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      "/lottery/admin/numeric-relations/history/numbers/occurrences/detail",
      { method: "POST", body: JSON.stringify(body) },
      true,
    ),

  postLotteryNrNumberNextDraws: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
      { method: "POST", body: JSON.stringify(body) },
      true,
    ),

  postLotteryNrNumbersCompare: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/numeric-relations/history/numbers/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryNrWhyStrengthened: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      "/lottery/admin/numeric-relations/history/numbers/why-strengthened",
      { method: "POST", body: JSON.stringify(body) },
      true,
    ),

  getLotteryPredictionMotors: () =>
    request<{ items: Record<string, unknown>[] }>("/lottery/admin/predictions/motors", {}, true),

  patchLotteryPredictionMotor: (key: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/lottery/admin/predictions/motors/${encodeURIComponent(key)}`,
      { method: "PATCH", body: JSON.stringify(body) },
      true,
    ),

  postLotteryPredictionNumericRelations: (body: {
    observed_number: number;
    lottery_ids: string[];
    occurrence_mode: "last_k" | "all";
    occurrence_k?: number | null;
  }) =>
    request<Record<string, unknown>>("/lottery/admin/predictions/numeric-relations/run", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryAIAdminDashboard: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/dashboard", {}, true),

  getLotteryAIConsumo: (params?: {
    period?: string;
    date_from?: string;
    date_to?: string;
    user_id?: string;
    lottery_key?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.period) q.set("period", params.period);
    if (params?.date_from) q.set("date_from", params.date_from);
    if (params?.date_to) q.set("date_to", params.date_to);
    if (params?.user_id) q.set("user_id", params.user_id);
    if (params?.lottery_key) q.set("lottery_key", params.lottery_key);
    const qs = q.toString();
    return request<Record<string, unknown>>(
      `/lottery/admin/ai/consumo${qs ? `?${qs}` : ""}`,
      {},
      true,
    );
  },

  getLotteryAIAlerts: (params?: { status?: string; severity?: string; code?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.severity) q.set("severity", params.severity);
    if (params?.code) q.set("code", params.code);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<{ items: unknown[]; counts?: Record<string, number>; open_alerts_count?: number }>(
      `/lottery/admin/ai/alerts${qs ? `?${qs}` : ""}`,
      {},
      true,
    );
  },

  getLotteryAIAlert: (id: string) =>
    request<Record<string, unknown>>(`/lottery/admin/ai/alerts/${encodeURIComponent(id)}`, {}, true),

  postLotteryAIAlertAcknowledge: (id: string, body?: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/alerts/${encodeURIComponent(id)}/acknowledge`,
      { method: "POST", body: JSON.stringify(body ?? {}) },
      true,
    ),

  postLotteryAIAlertResolve: (id: string, body?: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/alerts/${encodeURIComponent(id)}/resolve`,
      { method: "POST", body: JSON.stringify(body ?? {}) },
      true,
    ),

  postLotteryAIAlertSilence: (id: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/alerts/${encodeURIComponent(id)}/silence`,
      { method: "POST", body: JSON.stringify(body) },
      true,
    ),

  postLotteryAIAlertReopen: (id: string, body?: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/alerts/${encodeURIComponent(id)}/reopen`,
      { method: "POST", body: JSON.stringify(body ?? {}) },
      true,
    ),

  postLotteryAIAlertDetectorRunNow: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/alerts/detector/run-now", { method: "POST" }, true),

  getLotteryAITones: () => request<{ items: unknown[] }>("/lottery/admin/ai/tones", {}, true),

  getLotteryAITonePreference: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/tones/preference", {}, true),

  putLotteryAITonePreference: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/tones/preference", {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  postLotteryAITonePreview: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/tones/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryAIHermes: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/hermes", {}, true),

  getLotteryAIRuntime: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/runtime", {}, true),

  getLotteryAIPrompts: () =>
    request<{
      items: unknown[];
      active_prompt_id?: string | null;
      active_version?: string | null;
      prompt_blocks?: string[];
      publish_gates?: { can_publish: boolean; blockers: { code?: string; message: string }[] };
      empty_reason?: string | null;
    }>("/lottery/admin/ai/prompts", {}, true),

  getLotteryAIPrompt: (id: string) =>
    request<Record<string, unknown>>(`/lottery/admin/ai/prompts/${encodeURIComponent(id)}`, {}, true),

  postLotteryAIPrompt: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/prompts", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  putLotteryAIPrompt: (id: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/lottery/admin/ai/prompts/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  getLotteryPromptStudioSchema: () =>
    request<{ blocks: unknown[]; tools?: unknown[]; guide?: string }>(
      "/lottery/admin/ai/prompt-studio/schema",
      {},
      true,
    ),

  getLotteryPromptCompiled: (id: string, q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : "";
    return request<Record<string, unknown>>(
      `/lottery/admin/ai/prompts/${encodeURIComponent(id)}/compiled${qs}`,
      {},
      true,
    );
  },

  getLotteryPromptCompare: (a: string, b: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/prompt-studio/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`,
      {},
      true,
    ),

  postLotteryControlCenterBenchmark: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/control-center/benchmark/run", {
      method: "POST",
      body: "{}",
    }, true),

  postLotteryControlCenterPlayground: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/control-center/playground", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryAIPromptPublish: (id: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/prompts/${encodeURIComponent(id)}/publish`,
      { method: "POST" },
      true,
    ),

  postLotteryAIPromptPublishImmutable: (id: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/prompts/${encodeURIComponent(id)}/publish-immutable`,
      { method: "POST", body: "{}" },
      true,
    ),

  postLotteryAIPromptActivateDev: (id: string, body?: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/prompts/${encodeURIComponent(id)}/activate-dev`,
      { method: "POST", body: JSON.stringify(body || {}) },
      true,
    ),

  getLotteryPromptRuntimeStatus: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/prompt-runtime/status", {}, true),

  postLotteryPromptRuntimeSeedCandidate: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/prompt-runtime/seed-candidate", {
      method: "POST",
      body: "{}",
    }, true),

  postLotteryAIPromptRollback: (id: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/prompts/${encodeURIComponent(id)}/rollback`,
      { method: "POST" },
      true,
    ),

  getLotteryAIModels: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/models", {}, true),

  postLotteryAIModelsProbe: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/models/probe", { method: "POST" }, true),

  getLotteryAIConversationSettings: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/conversation-settings", {}, true),

  postLotteryAIConversationSettingsTest: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/conversation-settings/test", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  putLotteryAIConversationSettings: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/conversation-settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  deleteLotteryAIOpenAICredential: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/conversation-settings/openai-credential", {
      method: "DELETE",
    }, true),

  postLotteryAIOpenAIModels: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/conversation-settings/openai-models", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryAIAgent: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/agent", {}, true),

  putLotteryAIAgent: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/agent", {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  postLotteryAIAgentPublish: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/agent/publish", { method: "POST" }, true),

  postLotteryAIAgentRevert: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/agent/revert", { method: "POST" }, true),

  getLotteryAIMemory: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/memory", {}, true),

  getLotteryAIMemorySession: (sessionId: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/memory/sessions/${encodeURIComponent(sessionId)}`,
      {},
      true,
    ),

  postLotteryAIMemorySessionClear: (sessionId: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/memory/sessions/${encodeURIComponent(sessionId)}/clear`,
      { method: "POST" },
      true,
    ),

  getLotteryAITools: () =>
    request<{ items: unknown[] }>("/lottery/admin/ai/tools", {}, true),

  patchLotteryAITool: (name: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/lottery/admin/ai/tools/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, true),

  getLotteryAIAnalysisPacks: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/analysis-packs", {}, true),

  putLotteryAIAnalysisPacks: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/analysis-packs", {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  getLotteryAIDefaults: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/defaults", {}, true),

  putLotteryAIDefaults: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/defaults", {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  getLotteryAISafety: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/safety", {}, true),

  postLotteryAISafetyRunTests: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/safety/run-tests", { method: "POST" }, true),

  postLotteryAIPlayground: (body: { session_id?: string; message: string; context?: Record<string, unknown> }) =>
    request<Record<string, unknown>>("/lottery/admin/ai/playground", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getLotteryAIBenchmarks: () =>
    request<{ items: unknown[] }>("/lottery/admin/ai/benchmarks", {}, true),

  postLotteryAIBenchmark: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/benchmarks", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  postLotteryAIBenchmarkRun: (id: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/benchmarks/${encodeURIComponent(id)}/run`,
      { method: "POST" },
      true,
    ),

  postLotteryAIBenchmarkRun300: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/benchmarks/run-300", { method: "POST" }, true),

  postLotteryAIBenchmarkCompareV2V3: () =>
    request<Record<string, unknown>>(
      "/lottery/admin/ai/benchmarks/compare-v2-v3",
      { method: "POST" },
      true,
    ),

  getLotteryAIAlertThresholds: () =>
    request<Record<string, unknown>>("/lottery/admin/ai/alert-thresholds", {}, true),

  putLotteryAIAlertThresholds: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/lottery/admin/ai/alert-thresholds", {
      method: "PUT",
      body: JSON.stringify(body),
    }, true),

  getLotteryAISessions: (params?: { limit?: number; offset?: number; q?: string }) =>
    request<{ items: unknown[]; total?: number }>(
      `/lottery/admin/ai/sessions${buildQuery(params ?? {})}`,
      {},
      true,
    ),

  getLotteryAIVersions: () =>
    request<{ items: unknown[] }>("/lottery/admin/ai/versions", {}, true),

  postLotteryAIVersionPublish: (id: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/versions/${encodeURIComponent(id)}/publish`,
      { method: "POST" },
      true,
    ),

  postLotteryAIVersionRollback: (id: string) =>
    request<Record<string, unknown>>(
      `/lottery/admin/ai/versions/${encodeURIComponent(id)}/rollback`,
      { method: "POST" },
      true,
    ),

  getLotteryAIAudit: (params?: { limit?: number; offset?: number }) =>
    request<{ items: unknown[]; total: number }>(
      `/lottery/admin/ai/audit${buildQuery(params ?? {})}`,
      {},
      true,
    ),

  getLotteryAIPublishGates: () =>
    request<{ can_publish: boolean; blockers: { code: string; message: string; severity?: string }[]; flow?: string[] }>(
      "/lottery/admin/ai/publish-gates",
      {},
      true,
    ),

  postLotteryAIDeveloperMode: (enabled: boolean) =>
    request<{ ok: boolean; developer_mode: boolean }>(
      "/lottery/admin/ai/developer-mode",
      { method: "POST", body: JSON.stringify({ enabled }) },
      true,
    ),
};

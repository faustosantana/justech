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
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  getTenantId,
  setAuthTokens,
  type AuthTokens,
} from "./auth";

const REQUEST_TIMEOUT_MS = 30_000;

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

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
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

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
  retried = false,
): Promise<T> {
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
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${getApiUrl()}${path}`, {
      ...options,
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
      const detail =
        typeof body.detail === "string"
          ? body.detail
          : Array.isArray(body.detail)
            ? body.detail.map((d) => d.msg).filter(Boolean).join("; ")
            : undefined;
      throw new ApiError(
        response.status,
        body.error ?? "API_ERROR",
        detail ?? body.message ?? `API error: ${response.status}`,
      );
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
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

  getDGCPDashboard: () => request<DGCPSummary>("/dgcp/dashboard", {}, true),
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

  getDGCPOpportunities: (filters?: {
    status?: OpportunityStatus;
    company?: OpportunityCompany;
    priority?: OpportunityPriority;
    skip?: number;
    limit?: number;
  }) =>
    request<DGCPOpportunityListResponse>(
      `/dgcp/opportunities${buildQuery(filters ?? {})}`,
      {},
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
    }>(`/dgcp/opportunities/${id}/requirements/analyze`, { method: "POST", body: "{}" }, true),

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
    data: { document_id?: string; knowledge_asset_id?: string },
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

  prepareDGCPExpediente: (id: string) =>
    request<import("@/lib/dgcp").DGCPExpedientePrepareResult>(
      `/dgcp/opportunities/${id}/bid-package/prepare`,
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
      const payload = await fetchAuthenticatedFile(`/dgcp/opportunities/${id}/bid-package/download`);
      return { blob: payload.blob, filename: filename ?? `expediente_${id}.zip` };
    })();
    const { downloadAuthenticatedBlob } = await import("@/lib/authenticated-file");
    downloadAuthenticatedBlob(blob, resolvedName);
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
      { method: "POST", body: JSON.stringify({ max_pages: maxPages, page_size: pageSize }) },
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

  getOdooHealth: () => request<OdooHealth>("/odoo/health", {}, true),

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

  getM365Status: () => request<M365Status>("/m365/status", {}, true),

  getM365OutlookMessages: (search = "", limit = 50) =>
    request<M365ListResponse>(`/m365/outlook/messages${buildQuery({ search, limit })}`, {}, true),

  getM365SharePointSites: (search = "", limit = 50) =>
    request<M365ListResponse>(`/m365/sharepoint/sites${buildQuery({ search, limit })}`, {}, true),

  getM365OneDriveFiles: (search = "", limit = 50) =>
    request<M365ListResponse>(`/m365/onedrive/files${buildQuery({ search, limit })}`, {}, true),

  getM365CalendarEvents: (limit = 50) =>
    request<M365ListResponse>(`/m365/calendar/events${buildQuery({ limit })}`, {}, true),

  getM365Teams: (limit = 50) =>
    request<M365ListResponse>(`/m365/teams${buildQuery({ limit })}`, {}, true),

  getM365Documents: (search = "", limit = 50) =>
    request<M365ListResponse>(`/m365/documents${buildQuery({ search, limit })}`, {}, true),

  getM365Search: (q: string, limit = 25) =>
    request<M365SearchResponse>(`/m365/search${buildQuery({ q, limit })}`, {}, true),

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
    request<AssistantQueryResponse>("/assistant/query", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),

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
      {},
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
};

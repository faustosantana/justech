export type SupplierType =
  | "proveedor"
  | "fabricante"
  | "mayorista"
  | "distribuidor"
  | "cliente"
  | "aliado"
  | "subcontratista"
  | "transportista"
  | "tecnico_externo"
  | "competidor";

export type SupplierStatus = "activo" | "inactivo" | "preferido" | "bloqueado";

export interface SupplierCategory {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  synonyms: string[];
  parent_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Supplier {
  id: string;
  name: string;
  legal_name?: string | null;
  company_type: SupplierType;
  tax_id?: string | null;
  email?: string | null;
  phone?: string | null;
  whatsapp?: string | null;
  primary_contact?: string | null;
  website?: string | null;
  address?: string | null;
  city?: string | null;
  province?: string | null;
  country?: string | null;
  category?: string | null;
  primary_category_id?: string | null;
  category_ids: string[];
  categories: SupplierCategory[];
  subcategories: string[];
  brands: string[];
  products_services: string[];
  payment_terms?: string | null;
  delivery_time?: string | null;
  currency?: string | null;
  commercial_terms?: string | null;
  notes?: string | null;
  tags: string[];
  status: SupplierStatus;
  internal_rating?: number | null;
  odoo_partner_id?: number | null;
  price_supplier_name?: string | null;
  last_purchase_at?: string | null;
  last_quote_at?: string | null;
  price_lists_count: number;
  products_indexed_count: number;
  created_at: string;
  updated_at: string;
}

export interface SupplierListResponse {
  items: Supplier[];
  total: number;
}

export interface SupplierDashboardStats {
  total_suppliers: number;
  active_suppliers: number;
  preferred_suppliers: number;
  by_type: Record<string, number>;
  by_category: Array<{ name: string; count: number }>;
}

export interface SupplierSearchMatch {
  supplier: Supplier;
  score: number;
  matched_terms: string[];
  matched_categories: string[];
  matched_brands: string[];
  confidence: string;
  recommendation_reason?: string | null;
}

export interface SupplierSearchResponse {
  query: string;
  interpreted_categories: string[];
  interpreted_brands: string[];
  results: SupplierSearchMatch[];
  total: number;
}

export interface SupplierPriceListSummary {
  id: string;
  price_list_file_id: string;
  filename?: string | null;
  detected_brands: string[];
  detected_categories: string[];
  product_count: number;
  linked_at: string;
  file_modified_at?: string | null;
}

export interface SupplierInteraction {
  id: string;
  interaction_type: string;
  channel: string;
  subject?: string | null;
  body?: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface SupplierQuoteResponse {
  supplier_id: string;
  subject: string;
  email_body?: string | null;
  whatsapp_message?: string | null;
  interaction_id?: string | null;
}

export const SUPPLIER_TYPE_LABELS: Record<SupplierType, string> = {
  proveedor: "Proveedor",
  fabricante: "Fabricante",
  mayorista: "Mayorista",
  distribuidor: "Distribuidor",
  cliente: "Cliente",
  aliado: "Aliado",
  subcontratista: "Subcontratista",
  transportista: "Transportista",
  tecnico_externo: "Técnico externo",
  competidor: "Competidor",
};

export const SUPPLIER_STATUS_LABELS: Record<SupplierStatus, string> = {
  activo: "Activo",
  inactivo: "Inactivo",
  preferido: "Preferido",
  bloqueado: "Bloqueado",
};

export function whatsappUrl(phone?: string | null, message?: string) {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, "");
  if (!digits) return null;
  const base = `https://wa.me/${digits.startsWith("1") ? digits : `1${digits}`}`;
  return message ? `${base}?text=${encodeURIComponent(message)}` : base;
}

export function mailtoUrl(email?: string | null, subject?: string, body?: string) {
  if (!email) return null;
  const params = new URLSearchParams();
  if (subject) params.set("subject", subject);
  if (body) params.set("body", body);
  const qs = params.toString();
  return qs ? `mailto:${email}?${qs}` : `mailto:${email}`;
}

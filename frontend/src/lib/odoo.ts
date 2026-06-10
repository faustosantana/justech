export interface OdooHealth {
  connected: boolean;
  read_only: boolean;
  version?: string | null;
  database?: string | null;
  message: string;
  active_company_id?: number | null;
  active_company_name?: string | null;
}

export interface OdooCompany {
  id: number;
  name: string;
  currency_id?: number | null;
  currency_name?: string | null;
  partner_id?: number | null;
  is_active: boolean;
  selected_by_current_user: boolean;
}

export interface OdooCompaniesResponse {
  items: OdooCompany[];
  connected: boolean;
  message?: string | null;
}

export interface OdooUserMapping {
  id?: string | null;
  tenant_id: string;
  jaios_user_id: string;
  odoo_user_id: number;
  odoo_login: string;
  odoo_partner_id?: number | null;
  allowed_company_ids: number[];
  default_company_id?: number | null;
  is_active: boolean;
  last_verified_at?: string | null;
}

export interface OdooMe {
  jaios_user_id: string;
  jaios_email: string;
  jaios_name: string;
  odoo_connected: boolean;
  read_only: boolean;
  company_context: OdooCompanyContext;
  user_mapping: OdooUserMapping | null;
}

export interface OdooCompanyContext {
  selected: boolean;
  odoo_company_id?: number | null;
  odoo_company_name?: string | null;
  is_default?: boolean;
  selected_at?: string | null;
  message?: string | null;
}

export interface OdooSummary {
  customers: number;
  products: number;
  open_invoices: number;
  overdue_invoices: number;
  quotations: number;
  opportunities: number;
  projects: number;
  connected: boolean;
  company_id?: number | null;
  company_name?: string | null;
}

export interface OdooCustomer {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  vat?: string | null;
  city?: string | null;
  is_company: boolean;
}

export interface OdooProduct {
  id: number;
  name: string;
  default_code?: string | null;
  list_price: string;
  standard_price: string;
  qty_available: number;
  uom?: string | null;
}

export interface OdooVendor {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
  vat?: string | null;
}

export interface OdooSaleHistoryItem {
  id: number;
  order_name: string;
  order_date?: string | null;
  partner_id?: number | null;
  partner_name: string;
  product_id?: number | null;
  product_name: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  margin?: string | null;
  margin_pct?: number | null;
}

export interface OdooInvoice {
  id: number;
  name: string;
  partner_name: string;
  invoice_date?: string | null;
  due_date?: string | null;
  amount_total: string;
  amount_residual: string;
  currency: string;
  state: string;
  payment_state?: string | null;
}

export interface OdooQuotation {
  id: number;
  name: string;
  partner_id?: number | null;
  partner_name: string;
  date_order?: string | null;
  amount_total: string;
  currency?: string;
  state: string;
  user_id?: number | null;
  salesperson_name?: string | null;
  company_id?: number | null;
  company_name?: string | null;
  validity_date?: string | null;
}

export interface OdooQuotationLine {
  product_id?: number | null;
  product_name: string;
  description?: string | null;
  quantity: number;
  price_unit: string;
  discount: number;
  subtotal: string;
  taxes: string[];
}

export interface OdooQuotationDetail extends OdooQuotation {
  lines: OdooQuotationLine[];
  connected: boolean;
  message?: string | null;
}

export interface OdooOpportunity {
  id: number;
  name: string;
  partner_name?: string | null;
  expected_revenue: string;
  probability: number;
  stage?: string | null;
  date_deadline?: string | null;
}

export interface OdooProject {
  id: number;
  name: string;
  partner_name?: string | null;
  stage?: string | null;
}

export interface OdooListResponse<T = unknown> {
  items: T[];
  total: number;
  connected: boolean;
  message?: string | null;
}

export interface OdooQueryResponse {
  question: string;
  answer: string;
  data: Record<string, unknown>;
  query_type: string;
}

export interface OdooInvoiceLine {
  id: number;
  product_id?: number | null;
  product_name: string;
  quantity: number;
  unit_price: string;
  discount: number;
  tax_names?: string | null;
  subtotal: string;
  cost?: string | null;
  margin?: string | null;
  margin_pct?: number | null;
}

export interface OdooCustomerDetail {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  vat?: string | null;
  city?: string | null;
  salesperson?: string | null;
  company_name?: string | null;
  connected: boolean;
  open_invoices: OdooInvoice[];
  overdue_invoices: OdooInvoice[];
  quotations: OdooQuotation[];
  opportunities: OdooOpportunity[];
  projects: OdooProject[];
  sales_history: OdooSaleHistoryItem[];
  products_purchased: { product_id: number; product_name: string; last_price?: string | null; average_price?: string | null; total_qty: number; sales_count: number }[];
  total_sales_historical: string;
  total_due: string;
  total_overdue: string;
  message?: string | null;
}

export interface OdooProductDetail {
  id: number;
  name: string;
  default_code?: string | null;
  category?: string | null;
  list_price: string;
  standard_price: string;
  qty_available: number;
  uom?: string | null;
  connected: boolean;
  sales_history: OdooSaleHistoryItem[];
  purchase_history: { id: number; vendor_name: string; order_name: string; order_date?: string | null; quantity: number; unit_price: string; subtotal: string }[];
  buyers: { partner_id: number; partner_name: string; last_price?: string | null; average_price?: string | null; sales_count: number }[];
  last_price?: string | null;
  average_price?: string | null;
  min_price?: string | null;
  max_price?: string | null;
  estimated_margin_pct?: number | null;
  message?: string | null;
}

export interface OdooInvoiceDetail {
  id: number;
  name: string;
  partner_id: number;
  partner_name: string;
  invoice_date?: string | null;
  due_date?: string | null;
  amount_total: string;
  amount_residual: string;
  currency: string;
  state: string;
  payment_state?: string | null;
  lines: OdooInvoiceLine[];
  total_margin?: string | null;
  margin_pct?: number | null;
  odoo_url?: string | null;
  connected: boolean;
  message?: string | null;
}

export interface OdooVendorDetail {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  vat?: string | null;
  city?: string | null;
  connected: boolean;
  purchase_history: { id: number; order_name: string; product_name: string; quantity: number; unit_price: string; subtotal: string }[];
  products_supplied: { product_id: number; product_name: string; last_cost?: string | null; average_cost?: string | null; total_qty: number; purchase_count: number }[];
  total_purchase_value: string;
  purchase_orders: { name: string; date: string; amount_total: string; state: string }[];
  message?: string | null;
}

export function formatOdooAmount(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("es-DO", {
    style: "currency",
    currency: "DOP",
    minimumFractionDigits: 2,
  }).format(num);
}

export type CompanyType = "proveedor" | "fabricante" | "cliente" | "aliado" | "competidor";
export type CompanyStatus = "activo" | "inactivo";

export interface BusinessCompany {
  id: string;
  name: string;
  company_type: CompanyType;
  tax_id?: string | null;
  email?: string | null;
  phone?: string | null;
  primary_contact?: string | null;
  website?: string | null;
  category?: string | null;
  brands: string[];
  commercial_terms?: string | null;
  notes?: string | null;
  status: CompanyStatus;
  odoo_partner_id?: number | null;
  price_supplier_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessCompanyListResponse {
  items: BusinessCompany[];
  total: number;
}

export const COMPANY_TYPE_LABELS: Record<CompanyType, string> = {
  proveedor: "Proveedor",
  fabricante: "Fabricante",
  cliente: "Cliente",
  aliado: "Aliado estratégico",
  competidor: "Competidor",
};

export const COMPANY_STATUS_LABELS: Record<CompanyStatus, string> = {
  activo: "Activo",
  inactivo: "Inactivo",
};

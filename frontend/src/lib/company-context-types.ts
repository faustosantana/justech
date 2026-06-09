export interface CompanyOption {
  id: number;
  name: string;
  selected: boolean;
}

export interface GlobalCompanyContext {
  selection_mode: "single" | "multi" | "all";
  active_company_id?: number | null;
  active_company_name?: string | null;
  selected_company_ids: number[];
  selected_company_names: string[];
  allowed_companies: CompanyOption[];
  can_select_all: boolean;
  can_select_multiple: boolean;
  scope_label: string;
  odoo_connected: boolean;
}

export interface GlobalCompanyContextUpdate {
  selection_mode: "single" | "multi" | "all";
  active_company_id?: number;
  selected_company_ids?: number[];
}

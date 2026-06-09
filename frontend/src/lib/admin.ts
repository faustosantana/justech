/** Tipos — Centro de Administración */

export interface AdminAccess {
  can_view: boolean;
  can_mutate: boolean;
  role: string;
  permissions: string[];
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: string;
  department: string | null;
  supervisor_id: string | null;
  supervisor_name: string | null;
  visible_company_ids: number[];
  odoo_user_id: number | null;
  m365_prepared: boolean;
  m365_connection_status: string | null;
}

export interface TenantModule {
  module_key: string;
  name: string;
  is_enabled: boolean;
  is_future: boolean;
}

export interface Department {
  id: string;
  key: string;
  name: string;
  is_active: boolean;
}

export interface RoutingRuleAdmin {
  id: string;
  event_type: string;
  name: string;
  category: string;
  department: string;
  default_priority: string;
  default_assignee_name: string | null;
  default_supervisor_name: string | null;
  due_hours: number | null;
  notification_message: string | null;
  is_active: boolean;
}

export interface TenantSettings {
  language: string;
  timezone: string;
  default_currency: string;
  primary_company: string | null;
  qa_policies_visible: boolean;
  integration_status: Record<string, string>;
}

export interface M365Account {
  id: string;
  jaios_user_id: string;
  jaios_user_name: string | null;
  jaios_user_email: string | null;
  email: string | null;
  connection_status: string;
  scopes_granted: string[];
  last_sync_at: string | null;
  is_active: boolean;
  can_connect: boolean;
  required_scopes: string[];
}

export const M365_STATUS_LABELS: Record<string, string> = {
  not_connected: "No conectado",
  prepared: "Preparado",
  connected: "Conectado",
  expired: "Expirado",
};

export const ROLE_LABELS: Record<string, string> = {
  owner: "Propietario",
  admin: "Administrador",
  gerencia: "Gerencia",
  ventas: "Ventas",
  facturacion: "Facturación",
  finanzas: "Finanzas",
  compras: "Compras",
  soporte: "Soporte",
  operaciones: "Operaciones",
  licitaciones: "Licitaciones",
  usuario: "Usuario",
  member: "Usuario",
};

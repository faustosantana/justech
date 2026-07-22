export type IntegrationStatus =
  | "not_configured"
  | "configured"
  | "connected"
  | "credential_error"
  | "permission_missing"
  | "read_only"
  | "read_write";

export interface IntegrationCard {
  provider: string;
  label: string;
  category: string;
  connected: boolean;
  credentials_configured: boolean;
  status?: IntegrationStatus;
  read_only?: boolean | null;
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  last_test_message?: string | null;
  environment: string;
  source: string;
  recent_logs: SettingsAuditEntry[];
}

export interface IntegrationField {
  key: string;
  label: string;
  value?: string | number | boolean | null;
  masked?: string | null;
  secret: boolean;
  configured: boolean;
  field_type?: "text" | "boolean" | "secret";
}

export interface IntegrationDetail {
  provider: string;
  label: string;
  connected: boolean;
  credentials_configured?: boolean;
  status?: IntegrationStatus;
  read_only?: boolean | null;
  environment: string;
  source: string;
  fields: IntegrationField[];
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  last_test_message?: string | null;
  permissions?: Record<string, unknown>[];
  recent_logs?: SettingsAuditEntry[];
  extra?: Record<string, unknown>;
}

export interface RepositoryBinding {
  id?: string | null;
  folder_key: string;
  label: string;
  repository_type?: string;
  provider: string;
  graph_item_id?: string | null;
  drive_id?: string | null;
  folder_path?: string | null;
  web_url?: string | null;
  auto_sync: boolean;
  sync_interval_minutes?: number;
  last_sync_at?: string | null;
  indexed_files: number;
  status: string;
  last_error?: string | null;
  company_key?: string | null;
}

export interface RepositorySyncJob {
  id: string;
  binding_id?: string | null;
  trigger: string;
  status: string;
  files_synced: number;
  files_new: number;
  records_indexed: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface CompanyProfile {
  id: string;
  company_key: string;
  razon_social?: string | null;
  rnc?: string | null;
  rpe?: string | null;
  completeness_score: number;
  missing_fields: string[];
  synced_at?: string | null;
}

export interface SystemStatusItem {
  name: string;
  status: string;
  message?: string | null;
  checked_at?: string | null;
}

export interface SettingsAuditEntry {
  id: string;
  action: string;
  user_id?: string | null;
  resource_type?: string | null;
  details: Record<string, unknown>;
  ip_address?: string | null;
  created_at: string;
}

export const CONFIG_NAV = [
  { href: "/configuracion", label: "General", icon: "home" },
  { href: "/configuracion/integraciones", label: "Integraciones", icon: "plug" },
  { href: "/configuracion/integraciones/diagnostico", label: "Diagnóstico integraciones", icon: "activity" },
  { href: "/configuracion/ia/hermes", label: "IA — Hermes / Modelos", icon: "brain" },
  { href: "/configuracion/ia/prompts", label: "IA — Prompts", icon: "brain" },
  { href: "/configuracion/seguridad/permisos-ia", label: "Seguridad — Permisos IA", icon: "shield" },
  { href: "/inteligencia/bandeja", label: "Bandeja Inteligente", icon: "brain" },
  { href: "/inteligencia/comercial", label: "Inteligencia Comercial", icon: "brain" },
  { href: "/comunicaciones", label: "Comunicaciones", icon: "message" },
  { href: "/configuracion/integraciones/hermes", label: "Hermes (integración)", icon: "plug" },
  { href: "/configuracion/integraciones/proveedores", label: "Integraciones de Proveedores", icon: "plug" },
  { href: "/configuracion/integraciones/microsoft365", label: "Microsoft 365", icon: "cloud" },
  { href: "/configuracion/integraciones/odoo", label: "Odoo", icon: "database" },
  { href: "/configuracion/integraciones/whatsapp", label: "WhatsApp", icon: "message" },
  { href: "/configuracion/repositorios", label: "Repositorios", icon: "folder" },
  { href: "/configuracion/estado", label: "Estado del sistema", icon: "activity" },
  { href: "/configuracion/auditoria", label: "Logs / Auditoría", icon: "shield" },
  { href: "/configuracion/usuarios", label: "Usuarios", icon: "users" },
  { href: "/odoo/settings", label: "Vincular usuario Odoo", icon: "link" },
  { href: "/m365/cuentas", label: "Cuentas M365", icon: "user" },
] as const;

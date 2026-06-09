/** Microsoft 365 Intelligence Center — tipos API */

export const M365_NOT_CONNECTED = "Microsoft 365 no conectado";

export interface M365ConfigKey {
  key: string;
  label: string;
  description: string;
  configured: boolean;
}

export interface M365RequiredConfig {
  read_only: boolean;
  redirect_uri: string;
  missing_env_keys: string[];
  config_keys: M365ConfigKey[];
  delegated_scopes: string[];
  application_scopes: string[];
  oauth_ready: boolean;
  graph_ready: boolean;
  multi_user_ready: boolean;
  indexing_ready: boolean;
  enterprise_search_ready: boolean;
  hermes_memory_ready: boolean;
  qdrant_ready: boolean;
}

export interface M365Diagnostics {
  api_reachable: boolean;
  graph_configured: boolean;
  oauth_implemented: boolean;
  graph_implemented: boolean;
  read_only_enforced: boolean;
  audit_enabled: boolean;
  notes: string[];
}

export interface M365SetupStep {
  step: number;
  title: string;
  description: string;
  status: string;
}

export interface M365Health {
  connected: boolean;
  read_only: boolean;
  message: string;
  required_config: M365RequiredConfig;
  diagnostics?: M365Diagnostics;
}

export interface M365Status {
  connected: boolean;
  read_only: boolean;
  message: string;
  required_config: M365RequiredConfig;
  setup_steps: M365SetupStep[];
  diagnostics?: M365Diagnostics;
}

export interface M365ListResponse<T = unknown> {
  items: T[];
  total: number;
  connected: boolean;
  read_only: boolean;
  message: string;
  required_config: M365RequiredConfig;
}

export interface M365SearchResponse {
  query: string;
  hits: Record<string, unknown>[];
  total: number;
  connected: boolean;
  read_only: boolean;
  message: string;
  required_config: M365RequiredConfig;
}

export const M365_TABS = [
  { id: "resumen", label: "Resumen" },
  { id: "outlook", label: "Outlook" },
  { id: "sharepoint", label: "SharePoint" },
  { id: "onedrive", label: "OneDrive" },
  { id: "calendario", label: "Calendario" },
  { id: "teams", label: "Teams" },
  { id: "documentos", label: "Documentos" },
  { id: "busqueda", label: "Búsqueda Inteligente" },
  { id: "configuracion", label: "Configuración" },
] as const;

export type M365TabId = (typeof M365_TABS)[number]["id"];

/** Estado local cuando la API no responde — nunca mostrar error rojo por "no conectado". */
export const DEFAULT_M365_REQUIRED_CONFIG: M365RequiredConfig = {
  read_only: true,
  redirect_uri: "http://localhost:8000/api/v1/m365/auth/callback",
  missing_env_keys: ["M365_TENANT_ID", "M365_CLIENT_ID", "M365_CLIENT_SECRET"],
  config_keys: [
    {
      key: "M365_TENANT_ID",
      label: "Tenant ID (Azure AD)",
      description: "Identificador del directorio Microsoft Entra ID",
      configured: false,
    },
    {
      key: "M365_CLIENT_ID",
      label: "Client ID (App Registration)",
      description: "ID de la aplicación registrada en Azure",
      configured: false,
    },
    {
      key: "M365_CLIENT_SECRET",
      label: "Client Secret",
      description: "Secreto de aplicación (almacenamiento seguro futuro)",
      configured: false,
    },
    {
      key: "M365_REDIRECT_URI",
      label: "Redirect URI",
      description: "Callback OAuth tras consentimiento del usuario",
      configured: false,
    },
  ],
  delegated_scopes: [
    "openid",
    "profile",
    "offline_access",
    "Mail.Read",
    "Calendars.Read",
    "Files.Read.All",
    "Sites.Read.All",
    "Team.ReadBasic.All",
    "ChannelMessage.Read.All",
    "User.Read",
  ],
  application_scopes: ["Mail.Read", "Calendars.Read", "Files.Read.All", "Sites.Read.All"],
  oauth_ready: false,
  graph_ready: false,
  multi_user_ready: false,
  indexing_ready: false,
  enterprise_search_ready: false,
  hermes_memory_ready: false,
  qdrant_ready: false,
};

export const DEFAULT_M365_HEALTH: M365Health = {
  connected: false,
  read_only: true,
  message: M365_NOT_CONNECTED,
  required_config: DEFAULT_M365_REQUIRED_CONFIG,
  diagnostics: {
    api_reachable: false,
    graph_configured: false,
    oauth_implemented: false,
    graph_implemented: false,
    read_only_enforced: true,
    audit_enabled: true,
    notes: ["Integración en modo desconectado. Configure Microsoft 365 en la pestaña Configuración."],
  },
};

export const DEFAULT_M365_STATUS: M365Status = {
  connected: false,
  read_only: true,
  message: M365_NOT_CONNECTED,
  required_config: DEFAULT_M365_REQUIRED_CONFIG,
  setup_steps: [
    {
      step: 1,
      title: "Registrar aplicación en Azure",
      description: "Crear App Registration en Microsoft Entra ID con permisos delegados de lectura.",
      status: "pending",
    },
    {
      step: 2,
      title: "Configurar variables de entorno",
      description: "Completar M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET y M365_REDIRECT_URI.",
      status: "pending",
    },
    {
      step: 3,
      title: "Conectar cuenta Microsoft 365",
      description: "OAuth por usuario JAIOS con consentimiento y refresh tokens.",
      status: "pending",
    },
    {
      step: 4,
      title: "Validar permisos y modo lectura",
      description: "Confirmar M365_READ_ONLY=true y auditoría de consultas.",
      status: "pending",
    },
    {
      step: 5,
      title: "Habilitar búsqueda e indexación",
      description: "Búsqueda empresarial, Qdrant y JAIOS Assistant con contexto M365.",
      status: "pending",
    },
  ],
  diagnostics: DEFAULT_M365_HEALTH.diagnostics,
};

export function emptyM365ListResponse(): M365ListResponse {
  return {
    items: [],
    total: 0,
    connected: false,
    read_only: true,
    message: M365_NOT_CONNECTED,
    required_config: DEFAULT_M365_REQUIRED_CONFIG,
  };
}

export function emptyM365SearchResponse(query = ""): M365SearchResponse {
  return {
    query,
    hits: [],
    total: 0,
    connected: false,
    read_only: true,
    message: M365_NOT_CONNECTED,
    required_config: DEFAULT_M365_REQUIRED_CONFIG,
  };
}

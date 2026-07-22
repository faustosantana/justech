export type ConnectorType =
  | "rest_api"
  | "oauth2"
  | "api_key"
  | "basic_auth"
  | "bearer_token"
  | "webhook";

export type AuthMethod =
  | "api_key"
  | "oauth2"
  | "basic_auth"
  | "bearer_token"
  | "none";

export interface ConnectorSummary {
  id: string;
  slug: string;
  name: string;
  connector_type: string;
  auth_method: string;
  base_url?: string | null;
  is_active: boolean;
  is_builtin: boolean;
  is_dynamic: boolean;
  connected: boolean;
  status: string;
  read_only?: boolean;
  environment: string;
  user_link_mode: string;
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  last_test_message?: string | null;
  endpoint_count: number;
  user_link_count: number;
  config_url?: string;
  documentation?: string | null;
  model?: string | null;
  latency_ms?: number | null;
}

export interface ConnectorEndpoint {
  id?: string;
  name: string;
  path: string;
  http_method: string;
  query_params?: Record<string, unknown>;
  body_template?: string | null;
  headers?: Record<string, string>;
  response_hint?: Record<string, unknown>;
  transform?: Record<string, unknown>;
  assistant_enabled?: boolean;
  sort_order?: number;
}

export interface ConnectorDetail {
  id: string;
  slug: string;
  name: string;
  connector_type: string;
  auth_method: string;
  base_url?: string | null;
  config: Record<string, unknown>;
  secrets_masked: Record<string, string | null>;
  is_active: boolean;
  is_builtin: boolean;
  user_link_mode: string;
  documentation?: string | null;
  read_only: boolean;
  environment: string;
  connected: boolean;
  status: string;
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  last_test_message?: string | null;
  endpoints: ConnectorEndpoint[];
  recent_test_logs: Record<string, unknown>[];
}

export interface ConnectorCreatePayload {
  name: string;
  connector_type: ConnectorType;
  auth_method: AuthMethod;
  base_url?: string;
  config?: Record<string, unknown>;
  secrets?: Record<string, string>;
  user_link_mode?: string;
  documentation?: string;
  read_only?: boolean;
  environment?: string;
  endpoints?: ConnectorEndpoint[];
}

export const CONNECTOR_TYPES = [
  { value: "rest_api", label: "REST API" },
  { value: "oauth2", label: "OAuth2" },
  { value: "api_key", label: "API Key" },
  { value: "basic_auth", label: "Basic Auth" },
  { value: "bearer_token", label: "Bearer Token" },
  { value: "webhook", label: "Webhook" },
] as const;

export const AUTH_METHODS = [
  { value: "api_key", label: "API Key en header" },
  { value: "bearer_token", label: "Bearer Token" },
  { value: "basic_auth", label: "Basic Auth" },
  { value: "oauth2", label: "OAuth2" },
  { value: "none", label: "Sin autenticación" },
] as const;

export const WIZARD_STEPS = [
  "Datos generales",
  "Autenticación",
  "Endpoints",
  "Prueba de conexión",
  "Permisos",
  "Guardar",
] as const;

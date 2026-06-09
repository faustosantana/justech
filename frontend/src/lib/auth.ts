const ACCESS_KEY = "jaios_access_token";
const REFRESH_KEY = "jaios_refresh_token";
const TENANT_KEY = "jaios_tenant_id";
const ROLE_KEY = "jaios_role";

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  tenant_id?: string | null;
  role?: string | null;
}

export function setAuthTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  if (tokens.tenant_id) {
    localStorage.setItem(TENANT_KEY, tokens.tenant_id);
  }
  if (tokens.role) {
    localStorage.setItem(ROLE_KEY, tokens.role);
  }
}

export function getUserRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ROLE_KEY);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getTenantId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TENANT_KEY);
}

export function clearAuthTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(TENANT_KEY);
  localStorage.removeItem(ROLE_KEY);
}

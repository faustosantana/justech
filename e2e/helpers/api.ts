import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "../..");
const E2E_DIR = process.env.E2E_DIR ?? path.join(ROOT, ".qa/e2e");
export const API_BASE = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000/api/v1";

export type E2EFixtures = {
  tenant_id: string;
  admin_user_id: string;
  marieli_user_id: string | null;
  jennipher_user_id: string | null;
  document_ids: string[];
  draft_ids: string[];
  product_id: string | null;
  e2e_prefix: string;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  tenant_id?: string;
  role?: string;
};

export function loadFixtures(): E2EFixtures {
  const raw = fs.readFileSync(path.join(E2E_DIR, "fixtures.json"), "utf8");
  return JSON.parse(raw) as E2EFixtures;
}

export function loadTokens(): AuthTokens {
  const raw = fs.readFileSync(path.join(E2E_DIR, "tokens.json"), "utf8");
  return JSON.parse(raw) as AuthTokens;
}

export function authHeaders(tokens: AuthTokens = loadTokens()): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${tokens.access_token}`,
    "Content-Type": "application/json",
  };
  if (tokens.tenant_id) {
    headers["X-Tenant-Id"] = tokens.tenant_id;
  }
  return headers;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(`GET ${path} → ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`POST ${path} → ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`PUT ${path} → ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export function evidencePath(testName: string, file: string): string {
  const dir = path.join(E2E_DIR, "evidence", testName.replace(/\W+/g, "-"));
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, file);
}

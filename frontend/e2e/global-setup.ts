import fs from "node:fs";
import path from "node:path";

import type { FullConfig } from "@playwright/test";

const ROOT = path.resolve(__dirname, "../..");
const E2E_DIR = path.join(ROOT, ".qa/e2e");
const API_BASE = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000/api/v1";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  tenant_id?: string;
  role?: string;
};

type Fixtures = {
  tenant_id: string;
  admin_user_id: string;
  marieli_user_id: string | null;
  jennipher_user_id: string | null;
  document_ids: string[];
  draft_ids: string[];
  product_id: string | null;
  e2e_prefix: string;
};

async function login(): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "admin@justech.do",
      password: "JaiosAdmin2026!",
      tenant_slug: "justech",
    }),
  });
  if (!res.ok) {
    throw new Error(`Login E2E falló: ${res.status} ${await res.text()}`);
  }
  return res.json() as Promise<LoginResponse>;
}

export default async function globalSetup(_config: FullConfig) {
  fs.mkdirSync(E2E_DIR, { recursive: true });

  const health = await fetch(`${API_BASE}/health`);
  if (!health.ok) {
    throw new Error(`Backend no disponible en ${API_BASE}/health (${health.status})`);
  }

  const tokens = await login();
  fs.writeFileSync(
    path.join(E2E_DIR, "tokens.json"),
    JSON.stringify(tokens, null, 2),
    "utf8",
  );

  const fixturesPath = path.join(E2E_DIR, "fixtures.json");
  if (!fs.existsSync(fixturesPath)) {
    throw new Error(
      `Faltan fixtures E2E en ${fixturesPath}. Ejecute: docker compose exec backend python -m app.scripts.e2e_seed_fixtures /tmp/e2e-fixtures.json && docker compose cp backend:/tmp/e2e-fixtures.json ${fixturesPath}`,
    );
  }
  const fixtures = JSON.parse(fs.readFileSync(fixturesPath, "utf8")) as Fixtures;
  fs.writeFileSync(path.join(E2E_DIR, "fixtures.snapshot.json"), JSON.stringify(fixtures, null, 2));

  const authState = {
    cookies: [],
    origins: [
      {
        origin: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
        localStorage: [
          { name: "jaios_access_token", value: tokens.access_token },
          { name: "jaios_refresh_token", value: tokens.refresh_token },
          ...(tokens.tenant_id ? [{ name: "jaios_tenant_id", value: tokens.tenant_id }] : []),
          ...(tokens.role ? [{ name: "jaios_role", value: tokens.role }] : []),
        ],
      },
    ],
  };
  fs.writeFileSync(path.join(E2E_DIR, "auth-state.json"), JSON.stringify(authState), "utf8");
}

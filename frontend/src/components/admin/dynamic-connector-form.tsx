"use client";

import { SecretInput } from "@/components/settings/secret-input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AUTH_METHODS, CONNECTOR_TYPES, type ConnectorCreatePayload } from "@/lib/connectors";

type Props = {
  value: ConnectorCreatePayload;
  onChange: (v: ConnectorCreatePayload) => void;
  onSubmit?: () => void;
  submitLabel?: string;
  loading?: boolean;
};

export function DynamicConnectorForm({ value, onChange, onSubmit, submitLabel = "Guardar", loading }: Props) {
  const set = <K extends keyof ConnectorCreatePayload>(key: K, val: ConnectorCreatePayload[K]) =>
    onChange({ ...value, [key]: val });

  const config = value.config || {};
  const setConfig = (key: string, val: unknown) => set("config", { ...config, [key]: val });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Datos del conector</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Nombre del conector</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="Ej: Ingram Micro"
              value={value.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Tipo</label>
            <select
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              value={value.connector_type}
              onChange={(e) => set("connector_type", e.target.value as ConnectorCreatePayload["connector_type"])}
            >
              {CONNECTOR_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Autenticación</label>
            <select
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              value={value.auth_method}
              onChange={(e) => set("auth_method", e.target.value as ConnectorCreatePayload["auth_method"])}
            >
              {AUTH_METHODS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">URL base</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono"
              placeholder="https://api.ejemplo.com/v1"
              value={value.base_url || ""}
              onChange={(e) => set("base_url", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Ambiente</label>
            <select
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              value={value.environment || "development"}
              onChange={(e) => set("environment", e.target.value)}
            >
              <option value="development">Desarrollo</option>
              <option value="production">Producción</option>
              <option value="testing">Testing</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Vinculación de usuarios</label>
            <select
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              value={value.user_link_mode || "none"}
              onChange={(e) => set("user_link_mode", e.target.value)}
            >
              <option value="none">Credencial compartida (sin vínculo)</option>
              <option value="shared">Compartida + opcional por usuario</option>
              <option value="per_user">Cada usuario con su cuenta</option>
            </select>
          </div>
          <label className="flex items-center gap-2 md:col-span-2">
            <input
              type="checkbox"
              checked={value.read_only !== false}
              onChange={(e) => set("read_only", e.target.checked)}
            />
            <span className="text-sm">Modo solo lectura</span>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Credenciales</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <SecretInput
            label="API Key / Token"
            value={value.secrets?.api_key || ""}
            onChange={(v) => set("secrets", { ...(value.secrets || {}), api_key: v })}
          />
          <SecretInput
            label="Client ID"
            value={value.secrets?.client_id || ""}
            onChange={(v) => set("secrets", { ...(value.secrets || {}), client_id: v })}
          />
          <SecretInput
            label="Client Secret"
            value={value.secrets?.client_secret || ""}
            onChange={(v) => set("secrets", { ...(value.secrets || {}), client_secret: v })}
          />
          <SecretInput
            label="Bearer Token"
            value={value.secrets?.bearer_token || ""}
            onChange={(v) => set("secrets", { ...(value.secrets || {}), bearer_token: v })}
          />
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Header de autenticación</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="Authorization"
              value={String(config.header_name || "")}
              onChange={(e) => setConfig("header_name", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Timeout (segundos)</label>
            <input
              type="number"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              value={Number(config.timeout || 30)}
              onChange={(e) => setConfig("timeout", Number(e.target.value))}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">OAuth — Token URL</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono"
              value={String(config.token_url || "")}
              onChange={(e) => setConfig("token_url", e.target.value)}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">OAuth — Authorization URL</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono"
              value={String(config.authorization_url || "")}
              onChange={(e) => setConfig("authorization_url", e.target.value)}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Redirect URI</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono"
              value={String(config.redirect_uri || "")}
              onChange={(e) => setConfig("redirect_uri", e.target.value)}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Scopes</label>
            <input
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="read write offline_access"
              value={String(config.scopes || "")}
              onChange={(e) => setConfig("scopes", e.target.value)}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Documentación interna</label>
            <textarea
              rows={3}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              value={value.documentation || ""}
              onChange={(e) => set("documentation", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {onSubmit && (
        <Button onClick={onSubmit} disabled={loading || !value.name.trim()}>
          {loading ? "Guardando…" : submitLabel}
        </Button>
      )}
    </div>
  );
}

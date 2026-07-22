"use client";

import { useEffect, useState } from "react";
import { Unplug } from "lucide-react";

import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import { IntegrationLogs } from "@/components/settings/integration-logs";
import { PermissionChecklist } from "@/components/settings/permission-checklist";
import { SecretInput } from "@/components/settings/secret-input";
import { TestConnectionButton } from "@/components/settings/test-connection-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { IntegrationDetail, IntegrationStatus } from "@/lib/settings";

type Props = {
  provider: string;
  title?: string;
  onSaved?: () => void;
  showLogs?: boolean;
  showCompanies?: boolean;
};

const HERMES_MODELS = [
  { id: "DeepSeek-V3.2", label: "DeepSeek V3.2 — Copiloto (recomendado)" },
  { id: "deepseek-v4-flash", label: "DeepSeek V4 Flash — Análisis" },
  { id: "DeepSeek-R1", label: "DeepSeek R1" },
  { id: "gpt-4.1", label: "GPT-4.1" },
  { id: "gpt-5", label: "GPT-5" },
  { id: "claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
];

export function IntegrationForm({ provider, title, onSaved, showLogs = true, showCompanies = false }: Props) {
  const [detail, setDetail] = useState<IntegrationDetail | null>(null);
  const [config, setConfig] = useState<Record<string, string | boolean>>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
    detail?: string;
    missing_config?: string[];
    latency_ms?: number;
  } | null>(null);
  const [testDetails, setTestDetails] = useState<Record<string, unknown> | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await apiClient.getSettingsIntegration(provider);
      setDetail(d);
      const cfg: Record<string, string | boolean> = {};
      for (const f of d.fields) {
        if (!f.secret && f.value != null) {
          cfg[f.key] = f.field_type === "boolean" ? Boolean(f.value) : String(f.value);
        }
        if (f.field_type === "boolean" && f.value == null) {
          cfg[f.key] = false;
        }
      }
      setConfig(cfg);
      setSecrets({});
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo cargar la configuración. Verifique que tiene permisos de administrador.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [provider]);

  const save = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const d = await apiClient.updateSettingsIntegration(provider, { config, secrets });
      setDetail(d);
      setSecrets({});
      setMessage("Configuración guardada de forma segura.");
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setError(null);
    setMessage(null);
    setTestResult(null);
    try {
      const res = await apiClient.testSettingsIntegration(provider);
      if (res.ok) {
        setTestResult({
          ok: true,
          message: "Conexión exitosa.",
          detail: res.message || "Proveedor autenticado correctamente.",
          missing_config: res.missing_config,
          latency_ms: res.latency_ms,
        });
      } else {
        setTestResult({
          ok: false,
          message: res.message || "No fue posible conectar con el proveedor.",
          detail: res.error || res.message || "Error desconocido",
          missing_config: res.missing_config,
          latency_ms: res.latency_ms,
        });
      }
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "Error de red o servidor";
      setTestResult({
        ok: false,
        message: "No fue posible conectar con el proveedor.",
        detail,
      });
    } finally {
      setTesting(false);
    }
  };

  const disconnect = async () => {
    setDisconnecting(true);
    setError(null);
    try {
      const d = await apiClient.disconnectSettingsIntegration(provider);
      setDetail(d);
      setMessage("Integración desconectada.");
      setTestDetails(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desconectar.");
    } finally {
      setDisconnecting(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">Cargando configuración…</p>;
  if (!detail) {
    return error ? <p className="text-sm text-destructive">{error}</p> : null;
  }

  const companies = (testDetails?.companies || detail.extra?.companies) as
    | { id: number; name: string }[]
    | undefined;

  const permissionItems =
    provider === "odoo"
      ? [
          { key: "url", label: "URL de Odoo", granted: detail.fields.find((f) => f.key === "url")?.configured ?? false },
          { key: "db", label: "Base de datos", granted: detail.fields.find((f) => f.key === "database")?.configured ?? false },
          { key: "user", label: "Usuario API", granted: detail.fields.find((f) => f.key === "username")?.configured ?? false },
          { key: "key", label: "API Key", granted: detail.fields.find((f) => f.key === "api_key")?.configured ?? false },
          {
            key: "write",
            label: "Escritura habilitada",
            granted: detail.read_only === false,
            detail: detail.read_only ? "Desactive «Modo solo lectura» y guarde para permitir escrituras." : undefined,
          },
        ]
      : [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{title || detail.label}</CardTitle>
            <ConnectionStatusBadge
              status={detail.status as IntegrationStatus}
              connected={detail.connected}
              configured={detail.credentials_configured}
            />
          </div>
          <p className="text-sm text-muted-foreground">
            Ambiente: <strong>{detail.environment}</strong>
            {detail.source === "database" && <span className="ml-2">— Guardado en JAIOS (cifrado)</span>}
            {detail.environment === "production" && (
              <span className="ml-2 text-amber-700">— Está modificando configuración productiva.</span>
            )}
          </p>
          {detail.last_test_message && (
            <p className="text-sm text-muted-foreground">Última prueba: {detail.last_test_message}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {message && !testResult && <p className="text-sm text-emerald-700">{message}</p>}

          {testResult && (
            <div
              className={`rounded-lg border px-3 py-2 text-sm ${
                testResult.ok
                  ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-800"
                  : "border-destructive/40 bg-destructive/5 text-destructive"
              }`}
            >
              <p className="font-medium">{testResult.ok ? "✅ " : "❌ "}{testResult.message}</p>
              {testResult.detail && (
                <p className="mt-1 text-xs opacity-90">Detalle técnico: {testResult.detail}</p>
              )}
              {testResult.missing_config && testResult.missing_config.length > 0 && (
                <p className="mt-1 text-xs opacity-90">
                  Campos faltantes: {testResult.missing_config.join(", ")}
                </p>
              )}
              {testResult.latency_ms != null && (
                <p className="mt-1 text-xs opacity-90">Latencia: {testResult.latency_ms} ms</p>
              )}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {detail.fields.map((f) => {
              if (f.secret) {
                return (
                  <SecretInput
                    key={f.key}
                    label={f.label}
                    value={secrets[f.key] || ""}
                    masked={f.masked}
                    configured={f.configured}
                    onChange={(v) => setSecrets((s) => ({ ...s, [f.key]: v }))}
                  />
                );
              }
              if (f.field_type === "boolean") {
                const checked = Boolean(config[f.key] ?? f.value ?? false);
                return (
                  <label key={f.key} className="flex items-center gap-3 rounded-lg border border-border px-3 py-3">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.checked }))}
                      className="h-4 w-4"
                    />
                    <span className="text-sm">
                      <span className="font-medium">{f.label}</span>
                      {f.key === "read_only" && (
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          Si está activo, JAIOS no permitirá crear ni modificar registros en Odoo.
                        </span>
                      )}
                    </span>
                  </label>
                );
              }
              if (provider === "hermes" && f.key === "model") {
                return (
                  <div key={f.key} className="space-y-1.5">
                    <label className="text-sm font-medium">{f.label}</label>
                    <select
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                      value={String(config[f.key] ?? f.value ?? "DeepSeek-V3.2")}
                      onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))}
                    >
                      {HERMES_MODELS.map((m) => (
                        <option key={m.id} value={m.id}>{m.label}</option>
                      ))}
                    </select>
                  </div>
                );
              }
              if (f.field_type === "textarea" || f.key === "system_prompt") {
                return (
                  <div key={f.key} className="space-y-1.5 md:col-span-2">
                    <label className="text-sm font-medium">{f.label}</label>
                    <p className="text-xs text-muted-foreground">
                      Variables: {"{{empresa_actual}}"}, {"{{usuario_actual}}"}, {"{{modulo_actual}}"}, {"{{fecha_actual}}"}, {"{{contexto}}"}
                    </p>
                    <textarea
                      className="min-h-[280px] w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
                      value={String(config[f.key] ?? f.value ?? "")}
                      onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))}
                    />
                  </div>
                );
              }
              return (
                <div key={f.key} className="space-y-1.5">
                  <label className="text-sm font-medium">{f.label}</label>
                  <input
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    value={String(config[f.key] ?? f.value ?? "")}
                    onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))}
                  />
                </div>
              );
            })}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={save} disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
            <TestConnectionButton onClick={test} loading={testing} />
            {detail.connected && (
              <Button variant="ghost" onClick={disconnect} disabled={disconnecting}>
                <Unplug className="mr-1.5 h-3.5 w-3.5" />
                {disconnecting ? "Desconectando…" : "Desconectar"}
              </Button>
            )}
          </div>

          {showCompanies && companies && companies.length > 0 && (
            <div className="rounded-lg border border-border bg-muted/20 p-4">
              <p className="mb-2 text-sm font-medium">Empresas en Odoo ({companies.length})</p>
              <ul className="max-h-40 space-y-1 overflow-y-auto text-sm">
                {companies.map((c) => (
                  <li key={c.id}>
                    {c.name} <span className="text-muted-foreground">#{c.id}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {permissionItems.length > 0 && <PermissionChecklist items={permissionItems} title="Estado de configuración" />}
        </CardContent>
      </Card>

      {showLogs && detail.recent_logs && detail.recent_logs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Logs recientes</CardTitle>
          </CardHeader>
          <CardContent>
            <IntegrationLogs logs={detail.recent_logs} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { Unplug } from "lucide-react";
import Link from "next/link";

import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import { IntegrationLogs } from "@/components/settings/integration-logs";
import { SecretInput } from "@/components/settings/secret-input";
import { TestConnectionButton } from "@/components/settings/test-connection-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import type { IntegrationDetail, IntegrationStatus } from "@/lib/settings";

type Props = {
  provider: "ingram" | "omega" | string;
  title?: string;
  onSaved?: () => void;
  showLogs?: boolean;
};

export function SupplierIntegrationPanel({ provider, title, onSaved, showLogs = true }: Props) {
  const [detail, setDetail] = useState<IntegrationDetail | null>(null);
  const [config, setConfig] = useState<Record<string, string | boolean>>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string; detail?: string } | null>(null);

  const [mfaCode, setMfaCode] = useState("");
  const [mfaLoading, setMfaLoading] = useState(false);
  const [ingramStatus, setIngramStatus] = useState<Record<string, unknown> | null>(null);
  const [omegaStatus, setOmegaStatus] = useState<Record<string, unknown> | null>(null);

  const loadStatus = useCallback(async () => {
    if (provider === "ingram") {
      try {
        setIngramStatus(await apiClient.ingramConnectorStatus());
      } catch {
        setIngramStatus(null);
      }
    }
    if (provider === "omega") {
      try {
        setOmegaStatus(await apiClient.omegaConnectorStatus());
      } catch {
        setOmegaStatus(null);
      }
    }
  }, [provider]);

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
      await loadStatus();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo cargar la configuración. Verifique permisos de administrador.",
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
    setTestResult(null);
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
        });
      } else {
        setTestResult({
          ok: false,
          message: "No fue posible conectar con el proveedor.",
          detail: res.message || "Error desconocido",
        });
      }
      await load();
      await loadStatus();
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
      setTestResult(null);
      await loadStatus();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desconectar.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connectIngramMfa = async () => {
    if (!mfaCode.trim()) return;
    setMfaLoading(true);
    setError(null);
    try {
      const res = await apiClient.ingramMfaVerify(mfaCode.trim());
      if (!res.ok) {
        setError(res.message ?? "Código MFA inválido");
      } else {
        setMessage(res.message ?? "Sesión Ingram conectada");
        setMfaCode("");
      }
      await loadStatus();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al conectar Ingram MFA");
    } finally {
      setMfaLoading(false);
    }
  };

  const startIngramMfa = async () => {
    setMfaLoading(true);
    try {
      await apiClient.ingramMfaStart();
    } catch {
      /* ignore */
    } finally {
      setMfaLoading(false);
    }
  };

  const disconnectIngramMfa = async () => {
    setMfaLoading(true);
    try {
      await apiClient.ingramMfaDisconnect();
      await loadStatus();
    } finally {
      setMfaLoading(false);
    }
  };

  const connectOmega = async () => {
    setMfaLoading(true);
    setError(null);
    try {
      const res = await apiClient.omegaLogin();
      if (!res.ok) setError(res.message || "Error al conectar Omega");
      else setMessage(res.message || "Sesión Omega activa");
      await loadStatus();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al conectar Omega");
    } finally {
      setMfaLoading(false);
    }
  };

  const disconnectOmega = async () => {
    setMfaLoading(true);
    try {
      await apiClient.omegaDisconnect();
      await loadStatus();
    } finally {
      setMfaLoading(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">Cargando configuración…</p>;
  if (!detail) {
    return error ? <p className="text-sm text-destructive">{error}</p> : null;
  }

  const ingramSessionActive = Boolean(ingramStatus?.session_active);
  const omegaSessionActive = Boolean(omegaStatus?.session_active);

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
            {detail.last_test_at && (
              <span className="ml-2">
                · Última prueba: {new Date(detail.last_test_at).toLocaleString("es-DO")}
              </span>
            )}
          </p>
          {detail.last_test_message && (
            <p className="text-sm text-muted-foreground">Resultado: {detail.last_test_message}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {message && <p className="text-sm text-emerald-700">{message}</p>}

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
                  <label key={f.key} className="flex items-center gap-3 rounded-lg border px-3 py-3">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.checked }))}
                    />
                    <span className="text-sm font-medium">{f.label}</span>
                  </label>
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
            <Button onClick={() => void save()} disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
            <TestConnectionButton onClick={() => void test()} loading={testing} />
            {detail.connected && (
              <Button variant="ghost" onClick={() => void disconnect()} disabled={disconnecting}>
                <Unplug className="mr-1.5 h-3.5 w-3.5" />
                {disconnecting ? "Desconectando…" : "Desconectar"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {provider === "ingram" && (
        <Card className="border-sky-500/30">
          <CardHeader>
            <CardTitle className="text-base">Autenticación MFA — Ingram CEP</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-end">
            <div className="min-w-[200px] flex-1 text-sm">
              <p className="text-muted-foreground">
                Portal mi.ingrammicro.com · código de 6 dígitos del Authenticator
              </p>
              {ingramSessionActive && (
                <p className="mt-1 text-emerald-700 text-xs">Sesión MFA activa</p>
              )}
            </div>
            {!ingramSessionActive && (
              <>
                <Button variant="outline" size="sm" onClick={() => void startIngramMfa()} disabled={mfaLoading}>
                  Preparar MFA
                </Button>
                <Input
                  placeholder="123456"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\s/g, ""))}
                  className="w-full max-w-[140px] font-mono"
                  maxLength={8}
                />
                <Button onClick={() => void connectIngramMfa()} disabled={mfaLoading || mfaCode.length < 4}>
                  Conectar sesión
                </Button>
              </>
            )}
            {ingramSessionActive && (
              <Button variant="outline" onClick={() => void disconnectIngramMfa()} disabled={mfaLoading}>
                Cerrar sesión MFA
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {provider === "omega" && (
        <Card className="border-violet-500/30">
          <CardHeader>
            <CardTitle className="text-base">Sesión tienda Omega</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2">
            {omegaSessionActive ? (
              <>
                <p className="text-sm text-emerald-700">Sesión activa en tienda.omega.com.do</p>
                <Button variant="outline" onClick={() => void disconnectOmega()} disabled={mfaLoading}>
                  Cerrar sesión
                </Button>
              </>
            ) : (
              <Button onClick={() => void connectOmega()} disabled={mfaLoading}>
                Iniciar sesión en tienda
              </Button>
            )}
          </CardContent>
        </Card>
      )}

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

      <p className="text-xs text-muted-foreground">
        <Link href="/configuracion/integraciones/proveedores" className="text-primary hover:underline">
          ← Volver a Integraciones de Proveedores
        </Link>
      </p>
    </div>
  );
}

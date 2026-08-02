"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type Settings = {
  conversation_provider?: string;
  conversation_model?: string;
  temperature?: number;
  max_tokens?: number;
  timeout_seconds?: number;
  is_active?: boolean;
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  last_test_latency_ms?: number | null;
  last_test_model?: string | null;
  last_test_error?: string | null;
  catalog?: Record<string, string[]>;
};

type Probe = {
  ok?: boolean;
  provider?: string;
  model?: string;
  latency_ms?: number;
  total_ms?: number;
  status?: string;
  message_received?: string | null;
  schema_valid?: boolean;
  errors?: string[];
};

export default function LotteryAIConfiguracionPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [provider, setProvider] = useState("huawei");
  const [model, setModel] = useState("deepseek-v4-flash");
  const [temperature, setTemperature] = useState(0);
  const [maxTokens, setMaxTokens] = useState(700);
  const [timeout, setTimeoutSec] = useState(45);
  const [probe, setProbe] = useState<Probe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const catalog = settings?.catalog ?? {
    huawei: ["deepseek-v4-flash", "deepseek-v3", "DeepSeek-V3.2", "DeepSeek-V3"],
    openai: ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o"],
  };

  const models = useMemo(
    () => catalog[provider] ?? catalog.huawei ?? [],
    [catalog, provider],
  );

  const applySettings = (data: Settings) => {
    setSettings(data);
    setProvider(data.conversation_provider || "huawei");
    setModel(data.conversation_model || "deepseek-v4-flash");
    setTemperature(Number(data.temperature ?? 0));
    setMaxTokens(Number(data.max_tokens ?? 700));
    setTimeoutSec(Number(data.timeout_seconds ?? 45));
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getLotteryAIConversationSettings();
      applySettings(data as Settings);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar configuración");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (models.length && !models.includes(model)) {
      setModel(models[0]);
    }
  }, [models, model]);

  const draft = () => ({
    conversation_provider: provider,
    conversation_model: model,
    temperature,
    max_tokens: maxTokens,
    timeout_seconds: timeout,
  });

  const runTest = async () => {
    setBusy(true);
    setError(null);
    setProbe(null);
    try {
      const res = (await apiClient.postLotteryAIConversationSettingsTest(draft())) as Probe;
      setProbe(res);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Prueba de conexión falló");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.putLotteryAIConversationSettings(draft());
      const saved = (res as { settings?: Settings; probe?: Probe }).settings;
      const p = (res as { probe?: Probe }).probe;
      if (saved) applySettings(saved);
      if (p) setProbe(p);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se guardó (la prueba de conexión debe pasar)",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Configuración IA</h2>
        <p className="text-sm text-muted-foreground">
          Proveedor conversacional de Lottery IA (guardado en base de datos). No usa variables de
          entorno para elegir proveedor.
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {!loading && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Proveedor Conversacional</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-6">
              {(["huawei", "openai"] as const).map((p) => (
                <label key={p} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="provider"
                    checked={provider === p}
                    onChange={() => setProvider(p)}
                  />
                  {p === "huawei" ? "Huawei" : "OpenAI"}
                </label>
              ))}
            </div>

            <label className="block space-y-1 text-sm">
              <span className="font-medium">Modelo</span>
              <select
                className="w-full max-w-md rounded border bg-background px-3 py-2"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Temperature</span>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  max={2}
                  className="w-full rounded border bg-background px-3 py-2"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                />
              </label>
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Max Tokens</span>
                <input
                  type="number"
                  min={64}
                  max={8192}
                  className="w-full rounded border bg-background px-3 py-2"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                />
              </label>
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Timeout (s)</span>
                <input
                  type="number"
                  min={5}
                  max={300}
                  className="w-full rounded border bg-background px-3 py-2"
                  value={timeout}
                  onChange={(e) => setTimeoutSec(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void runTest()} disabled={busy}>
                {busy ? "Probando…" : "Probar conexión"}
              </Button>
              <Button onClick={() => void save()} disabled={busy}>
                Guardar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Estado</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-2">
          <MetricLine label="Activo" value={settings?.is_active ? "Sí" : "No"} />
          <MetricLine
            label="Proveedor activo"
            value={settings?.conversation_provider ?? "—"}
          />
          <MetricLine label="Modelo utilizado" value={settings?.conversation_model ?? "—"} />
          <MetricLine label="Última prueba" value={settings?.last_test_at ?? "—"} />
          <MetricLine
            label="Última prueba OK"
            value={
              settings?.last_test_ok == null ? "—" : settings.last_test_ok ? "Sí" : "No"
            }
          />
          <MetricLine label="Latencia" value={settings?.last_test_latency_ms ?? "—"} />
          <MetricLine label="Error última prueba" value={settings?.last_test_error ?? "—"} />
        </CardContent>
      </Card>

      {probe && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resultado de prueba</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            <MetricLine label="Estado" value={probe.status ?? (probe.ok ? "ok" : "failed")} />
            <MetricLine label="Proveedor" value={probe.provider} />
            <MetricLine label="Modelo" value={probe.model} />
            <MetricLine label="Latencia" value={probe.latency_ms} />
            <MetricLine label="Tiempo total" value={probe.total_ms} />
            <MetricLine
              label="Schema válido"
              value={probe.schema_valid ? "Sí" : "No"}
            />
            <div className="sm:col-span-2 space-y-1 text-sm">
              <div className="font-medium">Mensaje recibido</div>
              <pre className="max-h-48 overflow-auto rounded border bg-muted/40 p-2 text-xs whitespace-pre-wrap">
                {probe.message_received || "—"}
              </pre>
            </div>
            {(probe.errors?.length ?? 0) > 0 && (
              <div className="sm:col-span-2 text-sm text-destructive">
                Errores: {(probe.errors || []).join("; ")}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

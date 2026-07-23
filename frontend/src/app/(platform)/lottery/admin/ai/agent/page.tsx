"use client";

import { useCallback, useEffect, useState } from "react";

import { useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type FormState = {
  understanding_mode: string;
  analysis_depth: string;
  max_insights: number;
  max_lotteries: number;
  timeout_seconds: number;
  temperature: number;
  max_tokens: number;
  max_clarifications: number;
  fallback_enabled: boolean;
  proactive_analysis: boolean;
};

const CLASS_HELP: Record<string, string> = {
  A: "Editable y publicable desde UI",
  B: "Editable con benchmark y aprobación",
  C: "Solo visible",
  D: "Requiere cambio de código/despliegue",
  E: "Nunca editable por seguridad",
};

export default function LotteryAIAgentPage() {
  const { developerMode } = useLotteryAIDevMode();
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<FormState>({
    understanding_mode: "hybrid",
    analysis_depth: "standard",
    max_insights: 6,
    max_lotteries: 7,
    timeout_seconds: 45,
    temperature: 0.2,
    max_tokens: 1200,
    max_clarifications: 2,
    fallback_enabled: true,
    proactive_analysis: true,
  });
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const applyFromConfig = (data: Record<string, unknown>) => {
    const payload =
      ((data.draft as { payload?: Record<string, unknown> } | null)?.payload as Record<string, unknown> | undefined) ||
      ((data.active as { payload?: Record<string, unknown> } | null)?.payload as Record<string, unknown> | undefined) ||
      {};
    const models = (payload.models || {}) as Record<string, unknown>;
    setForm({
      understanding_mode: String(payload.understanding_mode ?? data.understanding_mode ?? "hybrid"),
      analysis_depth: String(payload.analysis_depth ?? data.analysis_depth ?? "standard"),
      max_insights: Number(payload.max_insights ?? 6),
      max_lotteries: Number(payload.max_lotteries ?? 7),
      timeout_seconds: Number(payload.timeout_seconds ?? 45),
      temperature: Number(models.temperature ?? data.temperature ?? 0.2),
      max_tokens: Number(models.max_tokens ?? data.max_tokens ?? 1200),
      max_clarifications: Number(payload.max_clarifications ?? 2),
      fallback_enabled: Boolean(payload.fallback_enabled ?? true),
      proactive_analysis: Boolean(payload.proactive_analysis ?? true),
    });
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setMsg(null);
    try {
      const data = await apiClient.getLotteryAIAgent();
      setConfig(data);
      applyFromConfig(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar config del agente");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const saveDraft = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.putLotteryAIAgent({ ...form });
      setMsg("Borrador guardado");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    const gates = (config?.publish_gates || {}) as { can_publish?: boolean; blockers?: { message: string }[] };
    if (gates.can_publish === false) {
      setError(`Publicación bloqueada: ${(gates.blockers ?? []).map((b) => b.message).join("; ")}`);
      return;
    }
    if (!window.confirm("¿Publicar configuración del agente en producción?")) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIAgentPublish();
      setMsg("Configuración publicada");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al publicar");
    } finally {
      setBusy(false);
    }
  };

  const revert = async () => {
    if (!window.confirm("¿Revertir al último estado publicado?")) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIAgentRevert();
      setMsg("Configuración revertida");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al revertir");
    } finally {
      setBusy(false);
    }
  };

  const gates = (config?.publish_gates || null) as {
    can_publish?: boolean;
    blockers?: { message: string }[];
  } | null;
  const classification = (config?.classification || {}) as Record<string, string>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Agente</h2>
          <p className="text-sm text-muted-foreground">Campos A/B editables — seguridad (E) bloqueada</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || busy}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {config && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Resumen</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-1.5 sm:grid-cols-2">
                <MetricLine label="Nombre" value={config.name ?? config.agent_name} />
                <MetricLine label="Versión" value={config.version} />
                <MetricLine label="Estado" value={config.status ?? config.state} />
                <MetricLine label="Proveedor" value={config.provider} />
                <MetricLine label="Modelo" value={config.model} />
                <MetricLine label="Hermes orquestador" value={config.hermes_as_orchestrator ? "sí" : "no (bloqueado)"} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Clasificación de configuración</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                {Object.entries(CLASS_HELP).map(([k, v]) => (
                  <p key={k}>
                    <span className="font-medium">{k}.</span> {v}
                  </p>
                ))}
                <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
                  {Object.entries(classification).map(([k, v]) => (
                    <p key={k}>
                      {k}: clase {v}
                    </p>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {gates && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">
                  Gates: {gates.can_publish ? "listo para publicar" : "publicación bloqueada"}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {gates.can_publish ? (
                  <p className="text-muted-foreground">Sin bloqueos detectados.</p>
                ) : (
                  <ul className="list-disc pl-5 text-destructive">
                    {(gates.blockers ?? []).map((b, i) => (
                      <li key={i}>{b.message}</li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Parámetros editables</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="text-xs text-muted-foreground">Modo de comprensión (A)</span>
                <select
                  className="w-full rounded border border-border bg-background px-2 py-1.5"
                  value={form.understanding_mode}
                  onChange={(e) => setForm((f) => ({ ...f, understanding_mode: e.target.value }))}
                >
                  <option value="hybrid">Híbrido</option>
                  <option value="rules">Reglas</option>
                  <option value="llm">LLM</option>
                </select>
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-xs text-muted-foreground">Profundidad (A)</span>
                <select
                  className="w-full rounded border border-border bg-background px-2 py-1.5"
                  value={form.analysis_depth}
                  onChange={(e) => setForm((f) => ({ ...f, analysis_depth: e.target.value }))}
                >
                  <option value="standard">Estándar</option>
                  <option value="deep">Profunda</option>
                  <option value="light">Ligera</option>
                </select>
              </label>
              {(
                [
                  ["max_insights", "Máx. insights (A)"],
                  ["max_lotteries", "Máx. loterías (A)"],
                  ["timeout_seconds", "Timeout s (A)"],
                  ["max_clarifications", "Máx. aclaraciones (A)"],
                  ["temperature", "Temperatura (B)"],
                  ["max_tokens", "Max tokens (B)"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="space-y-1 text-sm">
                  <span className="text-xs text-muted-foreground">{label}</span>
                  <Input
                    type="number"
                    step={key === "temperature" ? "0.05" : "1"}
                    value={form[key]}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        [key]: key === "temperature" ? Number(e.target.value) : Number.parseInt(e.target.value || "0", 10),
                      }))
                    }
                  />
                </label>
              ))}
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.fallback_enabled}
                  onChange={(e) => setForm((f) => ({ ...f, fallback_enabled: e.target.checked }))}
                />
                Fallback habilitado (A)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.proactive_analysis}
                  onChange={(e) => setForm((f) => ({ ...f, proactive_analysis: e.target.checked }))}
                />
                Análisis proactivo (A)
              </label>
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => void saveDraft()} disabled={busy}>
              Guardar borrador
            </Button>
            <Button size="sm" onClick={() => void publish()} disabled={busy || gates?.can_publish === false}>
              {gates?.can_publish === false ? "Publicar (bloqueado)" : "Publicar"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => void revert()} disabled={busy}>
              Revertir
            </Button>
          </div>

          {developerMode && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Payload (modo desarrollador)</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-64 overflow-auto rounded bg-muted/30 p-2 text-[10px]">
                  {JSON.stringify(
                    (config.draft as { payload?: unknown } | null)?.payload ??
                      (config.active as { payload?: unknown } | null)?.payload ??
                      {},
                    null,
                    2,
                  )}
                </pre>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

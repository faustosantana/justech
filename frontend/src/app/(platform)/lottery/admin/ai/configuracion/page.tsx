"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type Settings = {
  conversation_provider?: string;
  conversation_model?: string;
  active_provider?: string;
  active_model?: string;
  temperature?: number;
  max_tokens?: number;
  timeout_seconds?: number;
  is_active?: boolean;
  openai_key_configured?: boolean;
  key_configured?: boolean;
  openai_key_mask?: string | null;
  openai_base_url?: string | null;
  openai_organization?: string | null;
  openai_project?: string | null;
  credential_source?: string | null;
  credential_updated_at?: string | null;
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  last_test_latency_ms?: number | null;
  last_test_model?: string | null;
  last_test_error?: string | null;
  suggested_models?: Record<string, string[]>;
  catalog?: Record<string, string[]>;
  models_for_provider?: Record<string, string[]>;
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
  credential_source?: string;
  tested_from?: string;
  active_provider?: string | null;
  active_model?: string | null;
  errors?: string[];
};

const HUAWEI_MODELS = ["deepseek-v4-flash", "deepseek-v3", "DeepSeek-V3.2", "DeepSeek-V3"];
const OPENAI_FALLBACK = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini"];

function ProviderBadge({ provider }: { provider?: string | null }) {
  const p = (provider || "").toLowerCase();
  const isOpenAI = p === "openai";
  const isHuawei = p.includes("huawei") || p === "huawei_modelarts";
  const label = isOpenAI ? "OpenAI" : isHuawei ? "Huawei" : provider || "—";
  const cls = isOpenAI
    ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
    : isHuawei
      ? "bg-sky-500/15 text-sky-700 dark:text-sky-300"
      : "bg-muted text-muted-foreground";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ${cls}`}>
      <span aria-hidden>{isOpenAI ? "◎" : isHuawei ? "◇" : "•"}</span>
      {label}
    </span>
  );
}

function StatusPill({ ok, label }: { ok: boolean | null | undefined; label?: string }) {
  if (ok == null) {
    return (
      <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
        {label || "Sin prueba"}
      </span>
    );
  }
  return (
    <span
      className={`rounded-md px-2 py-0.5 text-xs font-medium ${
        ok ? "bg-green-500/15 text-green-700 dark:text-green-300" : "bg-destructive/15 text-destructive"
      }`}
    >
      {label || (ok ? "OK" : "Falló")}
    </span>
  );
}

function friendlyError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const msg = err.message || fallback;
    if (/api.?key|credencial|credential/i.test(msg)) {
      return "Falta o es inválida la API Key de OpenAI. Introdúcela o reemplázala y vuelve a probar.";
    }
    if (/prueba de conexión falló|connection/i.test(msg)) {
      return msg;
    }
    return msg;
  }
  return fallback;
}

export default function LotteryAIConfiguracionPage() {
  /** Configuración realmente activa en BD (Estado). */
  const [active, setActive] = useState<Settings | null>(null);
  /** Borrador del formulario (puede diferir del activo hasta Guardar). */
  const [provider, setProvider] = useState<"huawei" | "openai">("huawei");
  const [model, setModel] = useState("deepseek-v4-flash");
  const [temperature, setTemperature] = useState(0);
  const [maxTokens, setMaxTokens] = useState(700);
  const [timeout, setTimeoutSec] = useState(45);
  const [openaiKey, setOpenaiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [organization, setOrganization] = useState("");
  const [project, setProject] = useState("");
  const [replaceKey, setReplaceKey] = useState(false);
  const [remoteModels, setRemoteModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [probe, setProbe] = useState<Probe | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"test" | "save" | "delete" | "models" | null>(null);
  const modelsFetchedFor = useRef<string>("");

  const huaweiModels = useMemo(() => {
    return (
      active?.models_for_provider?.huawei ||
      active?.suggested_models?.huawei ||
      active?.catalog?.huawei ||
      HUAWEI_MODELS
    );
  }, [active]);

  const openaiModels = useMemo(() => {
    const suggested =
      active?.models_for_provider?.openai ||
      active?.suggested_models?.openai ||
      active?.catalog?.openai ||
      OPENAI_FALLBACK;
    const merged = [...suggested];
    for (const m of remoteModels) {
      if (!merged.includes(m)) merged.push(m);
    }
    return merged;
  }, [active, remoteModels]);

  const modelOptions = provider === "openai" ? openaiModels : huaweiModels;

  const syncFormFromActive = (data: Settings) => {
    const p = (data.conversation_provider || "huawei").toLowerCase() === "openai" ? "openai" : "huawei";
    setProvider(p);
    setModel(data.conversation_model || (p === "openai" ? OPENAI_FALLBACK[0] : HUAWEI_MODELS[0]));
    setTemperature(Number(data.temperature ?? 0));
    setMaxTokens(Number(data.max_tokens ?? 700));
    setTimeoutSec(Number(data.timeout_seconds ?? 45));
    setBaseUrl(data.openai_base_url || "https://api.openai.com/v1");
    setOrganization(data.openai_organization || "");
    setProject(data.openai_project || "");
    setOpenaiKey("");
    setReplaceKey(false);
  };

  const refreshActive = useCallback(async (alsoSyncForm = false) => {
    const data = (await apiClient.getLotteryAIConversationSettings()) as Settings;
    setActive(data);
    if (alsoSyncForm) syncFormFromActive(data);
    return data;
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    refreshActive(true)
      .catch((err) => setError(friendlyError(err, "No se pudo cargar la configuración")))
      .finally(() => setLoading(false));
  }, [refreshActive]);

  const selectProvider = (next: "huawei" | "openai") => {
    if (next === provider) return;
    setProvider(next);
    setProbe(null);
    setError(null);
    setSuccess(null);
    if (next === "huawei") {
      setRemoteModels([]);
      modelsFetchedFor.current = "";
      const first = huaweiModels[0] || HUAWEI_MODELS[0];
      setModel(first);
    } else {
      const first = openaiModels[0] || OPENAI_FALLBACK[0];
      // Drop Huawei model stuck in the field
      if (huaweiModels.includes(model) || /deepseek/i.test(model)) {
        setModel(first);
      } else if (!openaiModels.includes(model) && !OPENAI_FALLBACK.includes(model)) {
        setModel(first);
      }
    }
  };

  const draft = () => {
    const body: Record<string, unknown> = {
      conversation_provider: provider,
      conversation_model: model,
      temperature,
      max_tokens: maxTokens,
      timeout_seconds: timeout,
      openai_base_url: baseUrl,
      openai_organization: organization || null,
      openai_project: project || null,
    };
    if (provider === "openai" && openaiKey.trim()) {
      body.openai_api_key = openaiKey.trim();
    }
    return body;
  };

  const fetchOpenAIModels = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (provider !== "openai") return;
      const hasKey = Boolean(openaiKey.trim()) || Boolean(active?.openai_key_configured);
      if (!hasKey) {
        if (!opts?.silent) {
          setError("Introduce o guarda una API Key de OpenAI para consultar modelos.");
        }
        return;
      }
      const fingerprint = `${active?.openai_key_configured ? "db" : "form"}:${baseUrl}:${Boolean(openaiKey.trim())}`;
      if (opts?.silent && modelsFetchedFor.current === fingerprint && remoteModels.length > 0) {
        return;
      }
      setModelsLoading(true);
      if (!opts?.silent) setBusy("models");
      setError(null);
      try {
        const body: Record<string, unknown> = {
          conversation_provider: "openai",
          conversation_model: model,
          openai_base_url: baseUrl,
          openai_organization: organization || null,
          openai_project: project || null,
        };
        if (openaiKey.trim()) body.openai_api_key = openaiKey.trim();
        const res = (await apiClient.postLotteryAIOpenAIModels(body)) as {
          models?: string[];
        };
        const list = res.models || [];
        setRemoteModels(list);
        modelsFetchedFor.current = fingerprint;
        if (list.length && (/deepseek/i.test(model) || !model)) {
          setModel(list[0]);
        }
      } catch (err) {
        if (!opts?.silent) {
          setError(friendlyError(err, "No se pudieron listar los modelos de OpenAI"));
        }
      } finally {
        setModelsLoading(false);
        if (!opts?.silent) setBusy(null);
      }
    },
    [
      provider,
      openaiKey,
      active?.openai_key_configured,
      baseUrl,
      model,
      organization,
      project,
      remoteModels.length,
    ],
  );

  // Auto-load OpenAI models once when switching to OpenAI (if key available).
  useEffect(() => {
    if (provider !== "openai") return;
    if (!active?.openai_key_configured && !openaiKey.trim()) return;
    void fetchOpenAIModels({ silent: true });
    // Only re-run on provider / key availability changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider, active?.openai_key_configured]);

  // Keep model coherent with selected provider catalog.
  useEffect(() => {
    if (provider === "huawei" && /gpt-|o1|o3|chatgpt/i.test(model)) {
      setModel(huaweiModels[0] || HUAWEI_MODELS[0]);
    }
    if (provider === "openai" && /deepseek/i.test(model)) {
      setModel(openaiModels[0] || OPENAI_FALLBACK[0]);
    }
  }, [provider, model, huaweiModels, openaiModels]);

  const runTest = async () => {
    setBusy("test");
    setError(null);
    setSuccess(null);
    setProbe(null);
    try {
      const res = (await apiClient.postLotteryAIConversationSettingsTest(draft())) as Probe;
      setProbe(res);
      // Refresh Estado (activo) without resetting the form draft.
      await refreshActive(false);
      if (res.ok) {
        setSuccess(
          `Prueba OK con ${res.provider} / ${res.model}. El proveedor activo no cambia hasta «Guardar y activar».`,
        );
      } else {
        setError(
          (res.errors || []).join("; ") ||
            "La prueba falló. Revisa proveedor, modelo y credenciales del formulario.",
        );
      }
    } catch (err) {
      setError(friendlyError(err, "Prueba de conexión falló"));
    } finally {
      setBusy(null);
    }
  };

  const save = async () => {
    setBusy("save");
    setError(null);
    setSuccess(null);
    try {
      const res = await apiClient.putLotteryAIConversationSettings(draft());
      const saved = (res as { settings?: Settings; probe?: Probe }).settings;
      const p = (res as { probe?: Probe }).probe;
      if (p) setProbe(p);
      if (saved) {
        setActive(saved);
        syncFormFromActive(saved);
      } else {
        await refreshActive(true);
      }
      setSuccess(
        `Guardado y activado: ${saved?.conversation_provider || provider} / ${saved?.conversation_model || model}. El chat usará este proveedor de inmediato.`,
      );
    } catch (err) {
      setError(
        friendlyError(
          err,
          "No se guardó. La prueba de conexión debe pasar con la configuración del formulario.",
        ),
      );
    } finally {
      setBusy(null);
    }
  };

  const deleteCredential = async () => {
    if (!window.confirm("¿Eliminar la API Key de OpenAI guardada? Si OpenAI está activo, se volverá a Huawei.")) {
      return;
    }
    setBusy("delete");
    setError(null);
    setSuccess(null);
    try {
      const data = (await apiClient.deleteLotteryAIOpenAICredential()) as Settings;
      setActive(data);
      syncFormFromActive(data);
      setProbe(null);
      setRemoteModels([]);
      modelsFetchedFor.current = "";
      setSuccess("Credencial OpenAI eliminada. Solo queda la máscara previa en historial de auditoría si aplica.");
    } catch (err) {
      setError(friendlyError(err, "No se pudo eliminar la credencial"));
    } finally {
      setBusy(null);
    }
  };

  const dirty =
    active &&
    (provider !== (active.conversation_provider || "huawei") ||
      model !== (active.conversation_model || "") ||
      Boolean(openaiKey.trim()) ||
      replaceKey);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Configuración IA</h2>
          <p className="text-sm text-muted-foreground">
            Elige Huawei u OpenAI para el chat de Lottery IA. La API Key de OpenAI se guarda cifrada y nunca se
            vuelve a mostrar completa.
          </p>
        </div>
        {active ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Activo ahora:</span>
            <ProviderBadge provider={active.conversation_provider} />
            <span className="font-mono text-xs">{active.conversation_model}</span>
          </div>
        ) : null}
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      ) : null}
      {success ? (
        <div className="rounded-md border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-800 dark:text-green-200">
          {success}
        </div>
      ) : null}
      {loading ? <p className="text-sm text-muted-foreground">Cargando configuración…</p> : null}

      {!loading && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
            <CardTitle className="text-sm">Proveedor conversacional</CardTitle>
            {dirty ? (
              <span className="rounded-md bg-amber-500/15 px-2 py-0.5 text-xs text-amber-800 dark:text-amber-200">
                Cambios sin activar
              </span>
            ) : (
              <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                Formulario = activo
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              {([
                { id: "huawei" as const, title: "Huawei", desc: "DeepSeek vía ModelArts" },
                { id: "openai" as const, title: "OpenAI", desc: "GPT (API Key cifrada)" },
              ]).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => selectProvider(opt.id)}
                  className={`min-w-[10rem] rounded-lg border px-3 py-2 text-left transition-colors ${
                    provider === opt.id
                      ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <ProviderBadge provider={opt.id} />
                    <span className="text-sm font-medium">{opt.title}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{opt.desc}</p>
                </button>
              ))}
            </div>

            {provider === "openai" && (
              <div className="space-y-3 rounded-lg border border-border/80 bg-muted/20 p-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium">API Key</span>
                  <StatusPill
                    ok={Boolean(active?.openai_key_configured)}
                    label={active?.openai_key_configured ? "Configurada" : "No configurada"}
                  />
                  {active?.openai_key_mask ? (
                    <code className="rounded bg-background px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                      {active.openai_key_mask}
                    </code>
                  ) : null}
                </div>

                {(replaceKey || !active?.openai_key_configured) && (
                  <label className="block space-y-1 text-sm">
                    <span className="font-medium">
                      {active?.openai_key_configured ? "Nueva API Key" : "Pegar API Key"}
                    </span>
                    <input
                      type="password"
                      autoComplete="off"
                      spellCheck={false}
                      className="w-full max-w-xl rounded border bg-background px-3 py-2 font-mono text-sm"
                      value={openaiKey}
                      placeholder="sk-…"
                      onChange={(e) => setOpenaiKey(e.target.value)}
                    />
                    <span className="text-xs text-muted-foreground">
                      Se cifra al guardar. Después solo verás una máscara (ej. sk-••••1234).
                    </span>
                  </label>
                )}

                {active?.openai_key_configured && !replaceKey && (
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => setReplaceKey(true)}>
                      Reemplazar clave
                    </Button>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      disabled={busy !== null}
                      onClick={() => void deleteCredential()}
                    >
                      {busy === "delete" ? "Eliminando…" : "Eliminar clave"}
                    </Button>
                  </div>
                )}

                <label className="block space-y-1 text-sm">
                  <span className="font-medium">Base URL</span>
                  <input
                    className="w-full max-w-xl rounded border bg-background px-3 py-2 text-sm"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                  />
                </label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block space-y-1 text-sm">
                    <span className="font-medium">Organización (opcional)</span>
                    <input
                      className="w-full rounded border bg-background px-3 py-2 text-sm"
                      value={organization}
                      onChange={(e) => setOrganization(e.target.value)}
                    />
                  </label>
                  <label className="block space-y-1 text-sm">
                    <span className="font-medium">Proyecto (opcional)</span>
                    <input
                      className="w-full rounded border bg-background px-3 py-2 text-sm"
                      value={project}
                      onChange={(e) => setProject(e.target.value)}
                    />
                  </label>
                </div>
              </div>
            )}

            <label className="block space-y-1 text-sm">
              <span className="font-medium">Modelo</span>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="w-full max-w-md rounded border bg-background px-3 py-2 text-sm"
                  value={modelOptions.includes(model) ? model : modelOptions[0] || model}
                  onChange={(e) => setModel(e.target.value)}
                >
                  {!modelOptions.includes(model) && model ? (
                    <option value={model}>{model} (actual)</option>
                  ) : null}
                  {modelOptions.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                {provider === "openai" && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={busy !== null || modelsLoading}
                    onClick={() => void fetchOpenAIModels()}
                  >
                    {modelsLoading || busy === "models" ? "Consultando…" : "Actualizar lista"}
                  </Button>
                )}
              </div>
              <span className="text-xs text-muted-foreground">
                {provider === "openai"
                  ? modelsLoading
                    ? "Cargando modelos OpenAI…"
                    : remoteModels.length
                      ? `${remoteModels.length} modelos OpenAI disponibles (sin modelos Huawei).`
                      : "Lista sugerida OpenAI. Con API Key se consultan automáticamente los modelos reales."
                  : "Solo modelos Huawei / DeepSeek."}
              </span>
            </label>

            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Temperature</span>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  max={2}
                  className="w-full rounded border bg-background px-3 py-2 text-sm"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                />
              </label>
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Max tokens</span>
                <input
                  type="number"
                  min={64}
                  max={8192}
                  className="w-full rounded border bg-background px-3 py-2 text-sm"
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
                  className="w-full rounded border bg-background px-3 py-2 text-sm"
                  value={timeout}
                  onChange={(e) => setTimeoutSec(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void runTest()} disabled={busy !== null}>
                {busy === "test" ? "Probando…" : "Probar conexión"}
              </Button>
              <Button onClick={() => void save()} disabled={busy !== null}>
                {busy === "save" ? "Guardando…" : "Guardar y activar"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              «Probar conexión» usa exactamente este formulario (no el proveedor activo). «Guardar y activar»
              cambia el chat en caliente, sin reiniciar servicios.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
          <CardTitle className="text-sm">Estado (configuración activa)</CardTitle>
          <ProviderBadge provider={active?.conversation_provider} />
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-2">
          <MetricLine label="Provider activo" value={active?.active_provider || active?.conversation_provider} />
          <MetricLine label="Modelo activo" value={active?.active_model || active?.conversation_model} />
          <MetricLine label="credential_source" value={active?.credential_source ?? "—"} />
          <MetricLine
            label="key_configured"
            value={
              active?.key_configured || active?.openai_key_configured
                ? `true (${active?.openai_key_mask || "••••"})`
                : "false"
            }
          />
          <MetricLine label="Última prueba" value={active?.last_test_at ?? "—"} />
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Resultado última prueba:</span>
            <StatusPill ok={active?.last_test_ok} />
          </div>
          <MetricLine label="Latencia" value={active?.last_test_latency_ms != null ? `${active.last_test_latency_ms} ms` : "—"} />
          <MetricLine label="Modelo en última prueba" value={active?.last_test_model ?? "—"} />
          <div className="sm:col-span-2">
            <MetricLine label="Error última prueba" value={active?.last_test_error ?? "—"} empty="Ninguno" />
          </div>
        </CardContent>
      </Card>

      {probe && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
            <CardTitle className="text-sm">Resultado de prueba (formulario)</CardTitle>
            <StatusPill ok={Boolean(probe.ok)} label={probe.status || (probe.ok ? "ok" : "failed")} />
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Proveedor:</span>
              <ProviderBadge provider={probe.provider} />
            </div>
            <MetricLine label="Modelo" value={probe.model} />
            <MetricLine label="Latencia" value={probe.latency_ms != null ? `${probe.latency_ms} ms` : "—"} />
            <MetricLine label="Tiempo total" value={probe.total_ms != null ? `${probe.total_ms} ms` : "—"} />
            <MetricLine label="Schema válido" value={probe.schema_valid ? "Sí" : "No"} />
            <MetricLine label="credential_source" value={probe.credential_source} />
            <MetricLine label="Probado desde" value={probe.tested_from || "form"} />
            <MetricLine
              label="Activo (sin cambiar)"
              value={`${probe.active_provider || "—"} / ${probe.active_model || "—"}`}
            />
            <div className="sm:col-span-2 space-y-1 text-sm">
              <div className="font-medium">Respuesta</div>
              <pre className="max-h-48 overflow-auto rounded border bg-muted/40 p-2 text-xs whitespace-pre-wrap">
                {probe.message_received || "—"}
              </pre>
            </div>
            {(probe.errors?.length ?? 0) > 0 && (
              <div className="sm:col-span-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {(probe.errors || []).join("; ")}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { Eye, History, RefreshCw, Save, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

type HermesConfig = Awaited<ReturnType<typeof apiClient.getHermesConfig>>;
type HermesStatus = Awaited<ReturnType<typeof apiClient.getHermesStatus>>;

const PROMPT_TABS: { key: string; label: string }[] = [
  { key: "global", label: "System global" },
  { key: "copilot", label: "Copiloto" },
  { key: "dgcp", label: "DGCP" },
  { key: "tenders", label: "Licitaciones" },
  { key: "rfq", label: "Cotizaciones" },
  { key: "odoo", label: "Odoo/ERP" },
  { key: "documents", label: "Documentos" },
  { key: "suppliers", label: "Proveedores" },
  { key: "forms", label: "Formularios" },
];

export function HermesAIConfigPanel() {
  const [status, setStatus] = useState<HermesStatus | null>(null);
  const [config, setConfig] = useState<HermesConfig | null>(null);
  const [activeKey, setActiveKey] = useState("global");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [st, cfg] = await Promise.all([
        apiClient.getHermesStatus(),
        apiClient.getHermesConfig(),
      ]);
      setStatus(st);
      setConfig(cfg);
      setDraft(cfg.prompts ?? {});
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar configuración IA");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const content = draft[activeKey] ?? "";
      const cfg = await apiClient.saveHermesPrompt(activeKey, content);
      setConfig(cfg);
      setDraft(cfg.prompts ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  const restore = async (index: number) => {
    try {
      const cfg = await apiClient.restoreHermesPrompt(activeKey, index);
      setConfig(cfg);
      setDraft(cfg.prompts ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al restaurar");
    }
  };

  const doPreview = async () => {
    const content = draft[activeKey] ?? "";
    const res = await apiClient.previewHermesPrompt(activeKey, content);
    setPreview(res.preview);
  };

  const testModel = async (question = "¿Quién eres?") => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await apiClient.testHermesModel(question);
      const active = res.active_model ? ` · activo: ${res.active_model}` : "";
      const fb = res.fallback_active ? " · FALLBACK ACTIVO" : "";
      setTestResult(
        res.success
          ? `✓ ${res.message.slice(0, 200)} (${res.latency_ms} ms · config: ${res.configured_model ?? res.model}${active}${fb})`
          : `✗ ${res.message}`,
      );
      await load();
    } catch (e) {
      setTestResult(e instanceof Error ? e.message : "Prueba fallida");
    } finally {
      setTesting(false);
    }
  };

  const testPrompt = async () => {
    setTesting(true);
    try {
      const res = await apiClient.testHermesPrompt({
        key: activeKey,
        content: draft[activeKey],
        question: "¿Quién eres?",
      });
      setTestResult(`Respuesta: ${res.answer} (${res.latency_ms ?? "—"} ms)`);
    } catch (e) {
      setTestResult(e instanceof Error ? e.message : "Error");
    } finally {
      setTesting(false);
    }
  };

  const versions = (config?.prompt_version_history?.[activeKey] ?? []) as {
    content: string;
    saved_at: string;
  }[];

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Modelo activo — Huawei ModelArts</CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
              <RefreshCw className={`mr-1 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Actualizar
            </Button>
            <Button size="sm" onClick={() => void testModel()} disabled={testing}>
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              {testing ? "Probando…" : "Probar DeepSeek V4 Flash"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Stat label="Provider" value={status?.provider_label ?? status?.provider ?? "—"} />
          <Stat label="Modelo configurado" value={status?.configured_model ?? status?.model ?? config?.model ?? "—"} />
          <Stat
            label="Modelo activo real"
            value={status?.active_model || "—"}
            highlight={Boolean(status?.active_model && status.active_model.toLowerCase().includes("v4"))}
          />
          <Stat
            label="Fallback activo"
            value={status?.fallback_active ? "Sí" : "No"}
            warn={Boolean(status?.fallback_active)}
          />
          <Stat label="Estado" value={status?.status ?? "—"} />
          <Stat label="Endpoint" value={status?.endpoint ?? status?.api_url ?? "—"} />
          <Stat label="API Key" value={status?.api_key_configured ? (status.api_key_masked ?? "Configurada") : "No configurada"} />
          <Stat label="Latencia (probe)" value={status ? `${status.latency_ms} ms` : "—"} />
          <Stat label="Última prueba" value={status?.last_probe_at ? new Date(status.last_probe_at).toLocaleString("es-DO") : "—"} />
          <Stat label="Último error" value={status?.last_error ?? status?.error ?? "Ninguno"} />
          <Stat label="Hermes interno" value={status?.service_url ?? "—"} />
          <Stat label="Copiloto" value={status?.copilot_primary ? "Hermes principal" : "Legacy"} />
          {status?.last_probe_sample && (
            <p className="col-span-full rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs">
              Muestra probe: {status.last_probe_sample}
            </p>
          )}
          {testResult && (
            <p className="col-span-full rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs">{testResult}</p>
          )}
          <div className="col-span-full flex flex-wrap gap-2 pt-1">
            {["¿Quién eres?", "¿Qué puedes hacer?", "Hola"].map((q) => (
              <Button key={q} variant="outline" size="sm" disabled={testing} onClick={() => void testModel(q)}>
                {q}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">System Prompts por módulo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-1 border-b border-border pb-2">
            {PROMPT_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => { setActiveKey(tab.key); setPreview(null); }}
                className={`rounded-md px-2.5 py-1 text-xs ${activeKey === tab.key ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <p className="text-xs text-muted-foreground">
            Variables: {"{{usuario_actual}}"}, {"{{empresa_actual}}"}, {"{{modulo_actual}}"}, {"{{fecha_actual}}"}, {"{{zona_horaria}}"}, {"{{contexto_conversacion}}"}, {"{{fuentes_disponibles}}"}, {"{{permisos_usuario}}"}
          </p>

          <textarea
            className="min-h-[320px] w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
            value={draft[activeKey] ?? config?.default_prompts?.[activeKey] ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, [activeKey]: e.target.value }))}
          />

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void save()} disabled={saving}>
              <Save className="mr-1 h-3.5 w-3.5" />
              {saving ? "Guardando…" : "Guardar"}
            </Button>
            <Button variant="outline" onClick={() => void doPreview()}>
              <Eye className="mr-1 h-3.5 w-3.5" />
              Vista previa
            </Button>
            <Button variant="outline" onClick={() => void testPrompt()} disabled={testing}>
              Probar prompt
            </Button>
          </div>

          {preview && (
            <pre className="max-h-48 overflow-auto rounded-lg bg-muted/40 p-3 text-xs whitespace-pre-wrap">{preview}</pre>
          )}

          {versions.length > 0 && (
            <div className="space-y-2">
              <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                <History className="h-3.5 w-3.5" /> Historial de versiones
              </p>
              <ul className="space-y-1 text-xs">
                {versions.map((v, i) => (
                  <li key={i} className="flex items-center justify-between gap-2 rounded border border-border px-2 py-1">
                    <span className="text-muted-foreground">{new Date(v.saved_at).toLocaleString("es-DO")}</span>
                    <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => void restore(i)}>
                      Restaurar
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
  warn,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  warn?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={`truncate font-medium ${highlight ? "text-emerald-600" : ""} ${warn ? "text-amber-600" : ""}`}
        title={value}
      >
        {value}
      </p>
    </div>
  );
}

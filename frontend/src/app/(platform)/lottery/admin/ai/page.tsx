"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type AlertRow = Record<string, unknown>;

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-amber-500"}`}
      aria-label={ok ? "ok" : "atención"}
    />
  );
}

export default function LotteryAIDashboardPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState("active");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = filter === "active" ? undefined : filter;
      const [dash, alertRes] = await Promise.all([
        apiClient.getLotteryAIAdminDashboard(),
        apiClient.getLotteryAIAlerts({ status, limit: 100 }).catch(() => ({
          items: [] as unknown[],
          counts: {},
          open_alerts_count: 0,
        })),
      ]);
      setData(dash);
      setAlerts(((alertRes as { items: AlertRow[] }).items ?? []) as AlertRow[]);
      setCounts(((alertRes as { counts?: Record<string, number> }).counts ?? {}) as Record<string, number>);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCount = useMemo(
    () => Number(data?.open_alerts_count ?? counts.open ?? 0) + Number(counts.reopened ?? 0),
    [data, counts],
  );

  async function act(id: string, action: "acknowledge" | "resolve" | "reopen" | "silence") {
    setBusy(id + action);
    try {
      if (action === "acknowledge") await apiClient.postLotteryAIAlertAcknowledge(id);
      if (action === "resolve") await apiClient.postLotteryAIAlertResolve(id, { note: "resolved_from_ui" });
      if (action === "reopen") await apiClient.postLotteryAIAlertReopen(id);
      if (action === "silence") {
        const until = new Date(Date.now() + 24 * 3600 * 1000).toISOString();
        await apiClient.postLotteryAIAlertSilence(id, { until, reason: "silenced_24h_from_ui" });
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Acción de alerta falló");
    } finally {
      setBusy(null);
    }
  }

  async function runDetector() {
    setBusy("detector");
    try {
      await apiClient.postLotteryAIAlertDetectorRunNow();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Detector falló");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <p className="text-sm text-muted-foreground">Cargando…</p>;
  if (error) return <p className="text-sm text-destructive">{error}</p>;

  const d = data ?? {};
  const metrics = (d.metrics ?? {}) as Record<string, unknown>;
  const conv = (d.conversational_metrics ?? {}) as Record<string, unknown>;
  const prompt = (d.prompt_active ?? {}) as Record<string, unknown>;
  const hermes = (d.hermes ?? {}) as Record<string, unknown>;
  const health = String(d.health_label ?? d.health_semaphore ?? d.health ?? "Sin datos suficientes");
  const healthOk = String(d.health_semaphore ?? d.health) === "saludable" || String(d.health) === "ok";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Dashboard</h2>
          <p className="text-sm text-muted-foreground">Estado real del agente Lottery IA</p>
        </div>
        <Button type="button" variant="outline" size="sm" disabled={busy === "detector"} onClick={() => void runDetector()}>
          {busy === "detector" ? "Ejecutando…" : "Ejecutar detector"}
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Proveedor / Modelo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <MetricLine label="Proveedor" value={d.provider_display ?? d.provider ?? d.provider_active} />
            <MetricLine label="Modelo" value={d.model_display ?? d.model ?? d.model_active} />
            <MetricLine label="Configurado" value={d.model_configured} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Prompt activo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <MetricLine label="Nombre" value={prompt.display ?? prompt.name ?? d.active_prompt} />
            <MetricLine label="Versión" value={prompt.version ?? d.prompt_version} />
            <MetricLine label="Estado" value={prompt.status} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Salud</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-sm">
            <StatusDot ok={healthOk} />
            <span>{health}</span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{openCount} alertas abiertas</span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Memoria</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <MetricLine label="Backend" value={d.memory_backend ?? d.memory_active} />
            <MetricLine label="Sesiones" value={d.memory_sessions ?? d.sessions_total} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Hermes</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{String(hermes.summary ?? "No utilizado como orquestador.")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Métricas 7d</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <MetricLine label="Consultas" value={metrics.queries_display ?? metrics.total_queries} />
            <MetricLine label="OK rate" value={metrics.resolved_rate} />
            <MetricLine label="Latencia media" value={metrics.latency_display ?? metrics.latency_ms_avg ?? metrics.avg_latency_ms} />
            <MetricLine label="p95" value={metrics.latency_ms_p95 != null ? `${metrics.latency_ms_p95} ms` : null} />
            <MetricLine label="Fallback" value={metrics.fallback_display ?? metrics.fallback_rate} />
            <MetricLine label="Tokens" value={metrics.tokens_total} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Calidad conversacional</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <MetricLine label="Context reuse" value={conv.context_reuse_rate} />
            <MetricLine label="Aclaración innecesaria" value={conv.unnecessary_clarification_rate} />
            <MetricLine label="Domain reject" value={conv.domain_rejection_accuracy} />
            <MetricLine label="Renderer clean" value={conv.renderer_clean_rate} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Último éxito / fallback</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <MetricLine label="Éxito" value={d.last_success_at} />
            <MetricLine label="Fallback" value={d.last_fallback_at} />
            <MetricLine label="Config publicada" value={d.last_config_publish} />
            <MetricLine label="Versión config" value={d.config_version} />
          </CardContent>
        </Card>
      </div>

      <div id="alerts" className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {["active", "open", "acknowledged", "silenced", "resolved", "reopened"].map((s) => (
            <Button key={s} type="button" size="sm" variant={filter === s ? "default" : "outline"} onClick={() => setFilter(s)}>
              {s}
              {counts[s] != null ? ` (${counts[s]})` : ""}
            </Button>
          ))}
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Alertas</CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin alertas en este filtro.</p>
            ) : (
              <ul className="space-y-3">
                {alerts.map((alert, i) => (
                  <li key={String(alert.id ?? i)} className="rounded-lg border border-border/60 p-3 text-sm">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">
                          {String(alert.severity ?? "info").toUpperCase()} · {String(alert.code ?? "")}
                        </p>
                        <p>{String(alert.title ?? alert.message ?? "")}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {String(alert.component ?? "")} · ocurrencias {String(alert.occurrence_count ?? 1)}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Button type="button" size="sm" variant="outline" disabled={!!busy} onClick={() => void act(String(alert.id), "acknowledge")}>
                          Reconocer
                        </Button>
                        <Button type="button" size="sm" variant="outline" disabled={!!busy} onClick={() => void act(String(alert.id), "resolve")}>
                          Resolver
                        </Button>
                        <Button type="button" size="sm" variant="ghost" disabled={!!busy} onClick={() => void act(String(alert.id), "reopen")}>
                          Reabrir
                        </Button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

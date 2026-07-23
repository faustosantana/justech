"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type AlertRow = Record<string, unknown>;

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-amber-500"}`}
      aria-label={ok ? "activo" : "atención"}
    />
  );
}

export default function LotteryAIDashboardPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState<string>("active");
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
  const health = String(d.health_semaphore ?? "—");
  const healthOk = health === "saludable";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Dashboard</h2>
          <p className="text-sm text-muted-foreground">Estado del agente IA de Lottery</p>
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
          <CardContent className="text-sm">
            <p className="font-medium">{String(d.provider_active ?? d.provider_configured ?? "—")}</p>
            <p className="text-muted-foreground">{String(d.model_active ?? d.model_configured ?? "—")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Prompt activo</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{String(prompt.name ?? "—")}</p>
            <p className="text-xs text-muted-foreground">v{String(prompt.version ?? "—")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Salud / Alertas abiertas</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-sm">
            <StatusDot ok={healthOk} />
            <span>{health}</span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{openCount} abiertas</span>
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
          <CardContent className="space-y-1 text-sm">
            <p>Consultas: {String(metrics.total_queries ?? "—")}</p>
            <p>OK rate: {String(metrics.resolved_rate ?? "—")}</p>
            <p>Fallback: {String(metrics.fallback_rate ?? "—")}</p>
            <p>p95: {String(metrics.latency_ms_p95 ?? "—")} ms</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Calidad conversacional</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>Context reuse: {String(conv.context_reuse_rate ?? "—")}</p>
            <p>Aclaración innecesaria: {String(conv.unnecessary_clarification_rate ?? "—")}</p>
            <p>Domain reject: {String(conv.domain_rejection_accuracy ?? "—")}</p>
            <p>Renderer clean: {String(conv.renderer_clean_rate ?? "—")}</p>
          </CardContent>
        </Card>
      </div>

      <div id="alerts" className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {["active", "open", "acknowledged", "silenced", "resolved", "reopened"].map((s) => (
            <Button
              key={s}
              type="button"
              size="sm"
              variant={filter === s ? "default" : "outline"}
              onClick={() => setFilter(s)}
            >
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
                          {String(alert.severity ?? "info").toUpperCase()} · {String(alert.code ?? "—")}
                        </p>
                        <p>{String(alert.title ?? alert.message ?? "")}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          status={String(alert.status)} · component={String(alert.component ?? "—")} ·
                          occ={String(alert.occurrence_count ?? 1)} · metric={String(alert.metric_name ?? "—")}=
                          {String(alert.metric_value ?? "—")} / thr={String(alert.threshold_value ?? "—")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          first={String(alert.first_detected_at ?? "—")} · last=
                          {String(alert.last_detected_at ?? "—")} · prompt=
                          {String(alert.prompt_version ?? "—")} · model={String(alert.model_name ?? "—")}
                        </p>
                        {alert.recommendation ? (
                          <p className="mt-1 text-xs">Rec: {String(alert.recommendation)}</p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={!!busy}
                          onClick={() => void act(String(alert.id), "acknowledge")}
                        >
                          Reconocer
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={!!busy}
                          onClick={() => void act(String(alert.id), "silence")}
                        >
                          Silenciar 24h
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={!!busy}
                          onClick={() => void act(String(alert.id), "resolve")}
                        >
                          Resolver
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          disabled={!!busy}
                          onClick={() => void act(String(alert.id), "reopen")}
                        >
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

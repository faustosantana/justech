"use client";

import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
      aria-label={ok ? "activo" : "inactivo"}
    />
  );
}

export default function LotteryAIDashboardPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [alerts, setAlerts] = useState<unknown[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, alertRes] = await Promise.all([
        apiClient.getLotteryAIAdminDashboard(),
        apiClient.getLotteryAIAlerts().catch(() => ({ items: [] as unknown[] })),
      ]);
      setData(dash);
      setAlerts((alertRes as { items: unknown[] }).items ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando…</p>;
  if (error) return <p className="text-sm text-destructive">{error}</p>;

  const d = data ?? {};
  const metrics = (d.metrics ?? {}) as Record<string, unknown>;
  const hermesOk = d.hermes_status === "active" || d.hermes_status === "ok";
  const healthOk = d.health === "healthy" || d.health === "ok";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Dashboard</h2>
        <p className="text-sm text-muted-foreground">Estado del agente IA de Lottery</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Proveedor / Modelo</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="font-medium">{String(d.provider ?? "—")}</p>
            <p className="text-muted-foreground">{String(d.model ?? "—")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Prompt activo</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{String(d.active_prompt ?? "—")}</p>
            <p className="text-xs text-muted-foreground">v{String(d.prompt_version ?? "—")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Memoria</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{String(d.memory_backend ?? "—")}</p>
            <p className="text-xs text-muted-foreground">
              {String(d.memory_sessions ?? "—")} sesiones
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Estado Hermes</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-sm">
            <StatusDot ok={hermesOk} />
            <span>{String(d.hermes_status ?? "desconocido")}</span>
            <span className="text-xs text-muted-foreground">(no es orquestador)</span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Salud general</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-sm">
            <StatusDot ok={healthOk} />
            <span>{String(d.health ?? "—")}</span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Métricas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>Consultas: {String(metrics.total_queries ?? "—")}</p>
            <p>Latencia media: {String(metrics.avg_latency_ms ?? "—")} ms</p>
            <p>Fallbacks: {String(metrics.fallback_count ?? "—")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Último éxito / Fallback</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>Éxito: {String(d.last_success_at ?? "—")}</p>
            <p>Fallback: {String(d.last_fallback_at ?? "—")}</p>
          </CardContent>
        </Card>
      </div>

      <div id="alerts">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Alertas</CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin alertas activas.</p>
            ) : (
              <ul className="space-y-2">
                {alerts.map((a, i) => {
                  const alert = a as Record<string, unknown>;
                  return (
                    <li key={String(alert.id ?? i)} className="rounded-lg border border-border/60 p-2 text-sm">
                      <span className="font-medium">{String(alert.level ?? "info").toUpperCase()}</span>{" "}
                      — {String(alert.message ?? alert.description ?? JSON.stringify(a))}
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

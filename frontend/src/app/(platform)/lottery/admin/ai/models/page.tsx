"use client";

import { useCallback, useEffect, useState } from "react";

import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIModelsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [probe, setProbe] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [probing, setProbing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiClient.getLotteryAIModels());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar modelos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runProbe = async () => {
    setProbing(true);
    setProbe(null);
    setError(null);
    try {
      const res = await apiClient.postLotteryAIModelsProbe();
      setProbe(res);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Prueba de conexión falló");
    } finally {
      setProbing(false);
    }
  };

  const providers = data ? ((data.providers ?? []) as Record<string, unknown>[]) : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Modelos</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void runProbe()} disabled={probing || loading}>
            {probing ? "Probando…" : "Probar conexión"}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Configuración activa</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            <MetricLine label="Proveedor activo" value={data.provider ?? data.active_provider} />
            <MetricLine label="Modelo activo" value={data.model ?? data.active_model} />
            <MetricLine label="Provider requested" value={data.provider_requested} />
            <MetricLine label="Provider used" value={data.provider_used} />
            <MetricLine label="Model requested" value={data.model_requested} />
            <MetricLine label="Model used" value={data.model_used} />
            <MetricLine label="Último éxito" value={data.last_success_at} />
            <MetricLine label="Último error" value={data.last_error ?? data.last_error_at} />
            <MetricLine
              label="Latencia p50"
              value={data.latency_ms_p50 != null ? `${data.latency_ms_p50} ms` : null}
            />
            <MetricLine
              label="Latencia p95"
              value={data.latency_ms_p95 != null ? `${data.latency_ms_p95} ms` : null}
            />
            <MetricLine label="Tokens" value={data.tokens_display ?? data.tokens_total} />
            <MetricLine label="Costo estimado" value={data.cost_display} />
            <MetricLine label="Fallback" value={data.fallback_enabled ? "habilitado" : "deshabilitado"} />
            <MetricLine label="Health" value={data.health} />
            <MetricLine label="Temperature" value={data.temperature} />
            <MetricLine label="Max tokens" value={data.max_tokens} />
          </CardContent>
        </Card>
      )}

      {probe && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resultado de prueba de conexión</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
            <MetricLine label="OK" value={probe.ok ? "PASS" : "FAIL"} />
            <MetricLine label="Latencia" value={probe.latency_ms != null ? `${probe.latency_ms} ms` : null} />
            <MetricLine label="Modelo usado" value={probe.model_used} />
            <MetricLine label="Fallback" value={probe.fallback ? "sí" : "no"} />
            <MetricLine label="Tokens in" value={probe.tokens_in} />
            <MetricLine label="Tokens out" value={probe.tokens_out} />
            <MetricLine label="Respuesta" value={probe.response_preview} />
            <MetricLine label="Error" value={probe.error} empty="Ninguno" />
          </CardContent>
        </Card>
      )}

      {providers.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {providers.map((prov, i) => {
            const healthy = prov.status === "healthy" || prov.status === "ok";
            return (
              <Card key={String(prov.name ?? i)}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <span className={`inline-block h-2 w-2 rounded-full ${healthy ? "bg-green-500" : "bg-amber-500"}`} />
                    {String(prov.name ?? "Huawei ModelArts")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  <MetricLine label="Estado" value={prov.status} />
                  <MetricLine label="Modelo" value={prov.model} />
                  <MetricLine label="Latencia" value={prov.latency_ms != null ? `${prov.latency_ms} ms` : null} />
                  <MetricLine label="Último check" value={prov.last_check_at} />
                  <MetricLine label="Error" value={prov.error} empty="Ninguno" />
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

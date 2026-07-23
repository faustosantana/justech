"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIModelsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

  const providers = data
    ? ((data.providers ?? [data]) as Record<string, unknown>[])
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Modelos</h2>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {data && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-sm">Configuración activa</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
            <p>Proveedor: {String(data.provider ?? data.active_provider ?? "—")}</p>
            <p>Modelo: {String(data.model ?? data.active_model ?? "—")}</p>
            <p>Fallback: {String(data.fallback_model ?? "—")}</p>
            <p>Temperature: {String(data.temperature ?? "—")}</p>
            <p>Max tokens: {String(data.max_tokens ?? "—")}</p>
            <p>Timeout: {String(data.timeout_seconds ?? data.timeout ?? "—")} s</p>
          </CardContent>
        </Card>
      )}

      {providers.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {providers.map((prov, i) => {
            const healthy = prov.status === "healthy" || prov.status === "ok";
            return (
              <Card key={String(prov.name ?? prov.provider ?? i)}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${healthy ? "bg-green-500" : "bg-red-500"}`}
                    />
                    {String(prov.name ?? prov.provider ?? `Proveedor ${i + 1}`)}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  <p>Estado: {String(prov.status ?? "—")}</p>
                  <p>Modelo: {String(prov.model ?? "—")}</p>
                  <p>Latencia: {String(prov.latency_ms ?? "—")} ms</p>
                  <p>Último check: {String(prov.last_check_at ?? prov.checked_at ?? "—")}</p>
                  {prov.error && (
                    <p className="text-xs text-destructive">Error: {String(prov.error)}</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

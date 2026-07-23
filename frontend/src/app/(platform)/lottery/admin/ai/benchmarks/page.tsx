"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIBenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<unknown[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIBenchmarks();
      setBenchmarks(res.items ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar benchmarks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (id: string) => {
    setBusyId(id);
    setMsg(null);
    try {
      const res = await apiClient.postLotteryAIBenchmarkRun(id);
      setMsg(`Benchmark "${id}" ejecutado — ${String((res as Record<string, unknown>).status ?? "ok")}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Error al ejecutar benchmark "${id}"`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Benchmarks</h2>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Suite de benchmarks</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {benchmarks.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Sin benchmarks registrados.</p>
          )}
          {benchmarks.map((b) => {
            const bench = b as Record<string, unknown>;
            const id = String(bench.id ?? "");
            const isBusy = busyId === id;
            return (
              <div
                key={id}
                className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {String(bench.name ?? bench.label ?? id)}
                  </p>
                  {bench.description && (
                    <p className="text-xs text-muted-foreground">{String(bench.description)}</p>
                  )}
                  <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    {bench.last_score !== undefined && (
                      <span>Score: {String(bench.last_score)}</span>
                    )}
                    {bench.last_run_at && <span>Último: {String(bench.last_run_at)}</span>}
                    {bench.status && <span>Estado: {String(bench.status)}</span>}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void run(id)}
                  disabled={isBusy || loading}
                  className="shrink-0"
                >
                  {isBusy ? "Ejecutando…" : "Ejecutar"}
                </Button>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

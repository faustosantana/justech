"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIBenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<unknown[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [suiteBusy, setSuiteBusy] = useState<"300" | "compare" | null>(null);

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

  const run300 = async () => {
    setSuiteBusy("300");
    setError(null);
    setSummary(null);
    try {
      const res = await apiClient.postLotteryAIBenchmarkRun300();
      const r = res as Record<string, unknown>;
      const total = r.total ?? r.cases ?? "—";
      const passRate = r.pass_rate ?? r.score ?? "—";
      const p0 = r.p0 ?? r.p0_count ?? "—";
      const p1 = r.p1 ?? r.p1_count ?? "—";
      const blocked = r.publish_blocked;
      setSummary(
        `Suite 300: total=${String(total)} pass_rate=${String(passRate)} p0=${String(p0)} p1=${String(p1)}` +
          (blocked !== undefined ? ` publish_blocked=${String(blocked)}` : ""),
      );
      setMsg("Suite 300 ejecutada");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al ejecutar suite 300");
    } finally {
      setSuiteBusy(null);
    }
  };

  const compareV2V3 = async () => {
    setSuiteBusy("compare");
    setError(null);
    setSummary(null);
    try {
      const res = await apiClient.postLotteryAIBenchmarkCompareV2V3();
      const r = res as Record<string, unknown>;
      const gate = (r.v3_activation_gate ?? r.gate ?? r) as Record<string, unknown>;
      const activate = gate.activate_v3 ?? r.activate_v3;
      const reason = gate.reason ?? r.reason ?? "";
      const v2 = (r.v2 ?? {}) as Record<string, unknown>;
      const v3 = (r.v3 ?? {}) as Record<string, unknown>;
      setSummary(
        `Comparar v2 vs v3: activate_v3=${String(activate)} ` +
          `v2_pass=${String(v2.pass_rate ?? gate.v2_pass_rate ?? "—")} ` +
          `v3_pass=${String(v3.pass_rate ?? gate.v3_pass_rate ?? "—")} ` +
          `v3_p0=${String(v3.p0 ?? gate.v3_p0 ?? "—")} v3_p1=${String(v3.p1 ?? gate.v3_p1 ?? "—")}` +
          (reason ? ` — ${String(reason)}` : ""),
      );
      setMsg("Comparación v2 vs v3 completada");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al comparar v2 vs v3");
    } finally {
      setSuiteBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Benchmarks</h2>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void run300()}
            disabled={loading || suiteBusy !== null}
          >
            {suiteBusy === "300" ? "Ejecutando…" : "Ejecutar suite 300"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void compareV2V3()}
            disabled={loading || suiteBusy !== null}
          >
            {suiteBusy === "compare" ? "Comparando…" : "Comparar v2 vs v3"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            Actualizar
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resumen</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-xs whitespace-pre-wrap">{summary}</p>
          </CardContent>
        </Card>
      )}
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
                  disabled={isBusy || loading || suiteBusy !== null}
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

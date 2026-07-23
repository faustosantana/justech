"use client";

import { useCallback, useEffect, useState } from "react";

import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAISafetyPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiClient.getLotteryAISafety());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar políticas de seguridad");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runTests = async () => {
    if (!window.confirm("¿Ejecutar pruebas de seguridad?")) return;
    setRunning(true);
    setMsg(null);
    setTestResult(null);
    try {
      const res = await apiClient.postLotteryAISafetyRunTests();
      setTestResult(res);
      setMsg("Pruebas completadas");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al ejecutar pruebas");
    } finally {
      setRunning(false);
    }
  };

  const controls = data ? ((data.controls ?? data.rules ?? []) as Record<string, unknown>[]) : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Seguridad</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void runTests()} disabled={running || loading}>
            {running ? "Ejecutando…" : "Probar"}
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        Protecciones críticas bloqueadas. Las plantillas de tono no pueden desactivarlas.
      </p>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resumen</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            <MetricLine label="Modo" value={data.mode ?? data.safety_mode} />
            <MetricLine label="Nivel" value={data.level} />
            <MetricLine label="Críticas bloqueadas" value={data.critical_locked ? "sí" : "no"} />
            <MetricLine label="Última revisión" value={data.last_reviewed_at} />
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {controls.map((c, i) => (
          <Card key={String(c.key ?? i)}>
            <CardHeader className="py-3">
              <CardTitle className="flex items-center justify-between text-sm">
                <span>{String(c.label ?? c.name ?? `Control ${i + 1}`)}</span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                  {String(c.state ?? (c.active ? "ACTIVO" : "INACTIVO"))}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="text-muted-foreground">{String(c.description ?? c.impact ?? "")}</p>
              <MetricLine label="Clasificación" value={c.classification} />
              <MetricLine label="Bloqueado" value={c.locked ? "sí" : "no"} />
            </CardContent>
          </Card>
        ))}
      </div>

      {testResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resultado de pruebas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              Aprobadas:{" "}
              <span className="font-medium text-green-600">
                {String(testResult.passed ?? testResult.pass_count ?? 0)}
              </span>
            </p>
            <p>
              Fallidas:{" "}
              <span className="font-medium text-red-600">
                {String(testResult.failed ?? testResult.fail_count ?? 0)}
              </span>
            </p>
            <p>Resultado global: {testResult.all_pass ? "PASS" : "FAIL"}</p>
            <ul className="space-y-1 text-xs">
              {((testResult.results ?? []) as Record<string, unknown>[]).map((r, i) => (
                <li key={i} className="rounded border border-border/40 px-2 py-1">
                  {r.pass ? "PASS" : "FAIL"} — {String(r.q)} → expect {String(r.expect)} / got {String(r.got)}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

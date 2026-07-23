"use client";

import { useCallback, useEffect, useState } from "react";

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
    if (!window.confirm("¿Ejecutar pruebas de seguridad? Esto puede tardar varios segundos.")) return;
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

  const policies = data
    ? ((data.policies ?? data.rules ?? []) as Record<string, unknown>[])
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Seguridad</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void runTests()} disabled={running || loading}>
            {running ? "Ejecutando…" : "Ejecutar pruebas"}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Configuración de seguridad</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
            <p>Modo: {String(data.mode ?? data.safety_mode ?? "—")}</p>
            <p>Nivel: {String(data.level ?? data.safety_level ?? "—")}</p>
            <p>Filtro de contenido: {String(data.content_filter ?? data.content_filter_enabled ?? "—")}</p>
            <p>PII guard: {String(data.pii_guard ?? data.pii_detection ?? "—")}</p>
            <p>Max reintentos: {String(data.max_retries ?? "—")}</p>
            <p>Última revisión: {String(data.last_reviewed_at ?? "—")}</p>
          </CardContent>
        </Card>
      )}

      {policies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Políticas activas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {policies.map((policy, i) => (
              <div
                key={String(policy.id ?? policy.name ?? i)}
                className="rounded-lg border border-border/60 px-3 py-2 text-sm"
              >
                <p className="font-medium">{String(policy.name ?? policy.rule ?? `Política ${i + 1}`)}</p>
                {policy.description && (
                  <p className="text-xs text-muted-foreground">{String(policy.description)}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Estado: {String(policy.status ?? policy.enabled ?? "—")}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {testResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resultado de pruebas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              Aprobadas:{" "}
              <span className="font-medium text-green-600">
                {String(testResult.passed ?? testResult.pass_count ?? "—")}
              </span>
            </p>
            <p>
              Fallidas:{" "}
              <span className="font-medium text-red-600">
                {String(testResult.failed ?? testResult.fail_count ?? "—")}
              </span>
            </p>
            <p>Duración: {String(testResult.duration_ms ?? testResult.elapsed_ms ?? "—")} ms</p>
            {testResult.summary && (
              <pre className="overflow-auto rounded bg-muted/30 p-2 text-xs">
                {JSON.stringify(testResult.summary, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

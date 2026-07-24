"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function PromptBenchmarkPage() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.postLotteryControlCenterBenchmark();
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Benchmark falló");
    } finally {
      setBusy(false);
    }
  };

  const cases = (result?.cases || []) as Record<string, unknown>[];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Benchmark · Control Center</h1>
      <p className="text-sm text-muted-foreground">
        Gates: P0=0 y P1=0 para aprobar borrador. No publica ni activa.
      </p>
      <Button type="button" disabled={busy} onClick={() => void run()}>
        {busy ? "Ejecutando…" : "Ejecutar benchmark"}
      </Button>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {result ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Resultado · can_approve={String(result.can_approve)} · P0={String(result.p0_failures)} ·
              P1={String(result.p1_failures)}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {cases.map((c) => (
              <div key={String(c.id)} className="flex justify-between rounded border px-2 py-1 text-sm">
                <span>
                  [{String(c.priority)}] {String(c.name)}
                </span>
                <span className={c.pass ? "text-green-700" : "text-destructive"}>
                  {c.pass ? "PASS" : "FAIL"} {c.detail ? `· ${String(c.detail)}` : ""}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import { HistoricalAnalyzerForm } from "@/components/lottery/control-center/historical-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function ComparadorPage() {
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"candidates" | "confirmers" | "combinations" | "lotteries">(
    "candidates",
  );
  const [items, setItems] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    void apiClient
      .getLotteryNumericRelationsLotteries()
      .then((lots) => setCatalog((lots.items || []).filter((c) => c?.id)))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Error loterías"));
  }, []);

  const onSubmit = useCallback(
    async (body: Record<string, unknown>) => {
      setBusy(true);
      setError(null);
      try {
        const res = await apiClient.postLotteryNrHistoryCompare({
          ...body,
          compare_mode: mode,
        });
        setItems((res.items || []) as Record<string, unknown>[]);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Comparación falló");
        setItems([]);
      } finally {
        setBusy(false);
      }
    },
    [mode],
  );

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Comparador Histórico</h1>
      <p className="text-sm text-muted-foreground">
        Compara candidatos, confirmadores, combinaciones o loterías. Toda cifra incluye soporte.
      </p>
      <HistoricalAnalyzerForm
        catalog={catalog}
        title="Comparar"
        submitLabel="Comparar"
        onSubmit={onSubmit}
        busy={busy}
        error={error}
        extra={
          <fieldset className="text-xs">
            <legend className="mb-1 font-medium">Modo de comparación</legend>
            <div className="flex flex-wrap gap-3">
              {(["candidates", "confirmers", "combinations", "lotteries"] as const).map((m) => (
                <label key={m} className="flex items-center gap-1">
                  <input type="radio" checked={mode === m} onChange={() => setMode(m)} />
                  {m}
                </label>
              ))}
            </div>
          </fieldset>
        }
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resultados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          {items.map((it, idx) => (
            <div key={idx} className="rounded border p-2">
              <pre className="whitespace-pre-wrap">{JSON.stringify(it, null, 2)}</pre>
            </div>
          ))}
          {items.length === 0 ? <p className="text-muted-foreground">Sin resultados aún.</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}

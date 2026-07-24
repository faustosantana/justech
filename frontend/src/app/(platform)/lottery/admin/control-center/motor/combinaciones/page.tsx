"use client";

import { useCallback, useEffect, useState } from "react";

import {
  HistoricalAnalyzerForm,
  RateCell,
} from "@/components/lottery/control-center/historical-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function CombinacionesPage() {
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matrix, setMatrix] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    void apiClient
      .getLotteryNumericRelationsLotteries()
      .then((lots) => setCatalog((lots.items || []).filter((c) => c?.id)))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Error loterías"));
  }, []);

  const onSubmit = useCallback(async (body: Record<string, unknown>) => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.postLotteryNrHistoryMatrix(body);
      setMatrix((res.matrix || null) as Record<string, unknown> | null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Matriz falló");
      setMatrix(null);
    } finally {
      setBusy(false);
    }
  }, []);

  const cells = (matrix?.cells || []) as Record<string, unknown>[];
  const rows = (matrix?.rows_candidates || []) as number[];
  const cols = (matrix?.columns_confirmers || []) as number[];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Matriz de Combinaciones · Candidato × Confirmador</h1>
      <p className="text-sm text-muted-foreground">
        Cada celda muestra eventos, tasas (numerador/denominador/muestra) y ciclo mediano.
      </p>
      <HistoricalAnalyzerForm
        catalog={catalog}
        title="Calcular matriz"
        submitLabel="Generar matriz"
        onSubmit={onSubmit}
        busy={busy}
        error={error}
      />
      {matrix ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Matriz</CardTitle>
          </CardHeader>
          <CardContent className="overflow-auto">
            <table className="min-w-full border text-xs">
              <thead>
                <tr>
                  <th className="border p-1">C \\ V</th>
                  {cols.map((v) => (
                    <th key={v} className="border p-1">
                      {v}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c}>
                    <th className="border p-1">{c}</th>
                    {cols.map((v) => {
                      const cell = cells.find((x) => x.candidate === c && x.confirmer === v);
                      return (
                        <td key={`${c}-${v}`} className="border p-1 align-top">
                          {cell ? (
                            <div className="space-y-1">
                              <div>ev={String(cell.event_count)}</div>
                              <RateCell rate={cell.response_rate_next_draw as Record<string, unknown>} />
                              <div>med={String(cell.median_cycle ?? "—")}</div>
                            </div>
                          ) : (
                            "—"
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

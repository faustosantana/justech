"use client";

import { useCallback, useEffect, useState } from "react";

import {
  HistoricalAnalyzerForm,
  RateCell,
} from "@/components/lottery/control-center/historical-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function HistoricoPage() {
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

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
      const res = await apiClient.postLotteryNrHistoryConditions(body);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Análisis histórico falló");
      setResult(null);
    } finally {
      setBusy(false);
    }
  }, []);

  const stats = (result?.statistics || {}) as Record<string, unknown>;
  const aliases = (stats.aliases || {}) as Record<string, Record<string, unknown>>;
  const cycles = (stats.cycles || {}) as Record<string, unknown>;
  const combos = (result?.combination_events || []) as Record<string, unknown>[];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Analizador Histórico · T1 ↔ T2</h1>
      <p className="text-sm text-muted-foreground">
        Condiciones relacionales, tasas por horizonte, ciclos y evidencia por draw_id. No es
        probabilidad de ganar.
      </p>
      <HistoricalAnalyzerForm
        catalog={catalog}
        title="Buscar condiciones históricas"
        submitLabel="Analizar histórico"
        onSubmit={onSubmit}
        busy={busy}
        error={error}
      />

      {result ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resumen</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div>Versión metodología: {String(result.methodology_version)}</div>
              <div>Anclas examinadas: {String(result.anchors_examined)}</div>
              <div>Eventos atómicos: {String(result.atomic_event_count)}</div>
              <div>Eventos combinación: {String(result.combination_event_count)}</div>
              <div className="grid gap-2 md:grid-cols-3">
                <div>
                  <div className="font-medium">Tasa próximo sorteo</div>
                  <RateCell rate={aliases.response_rate_next_draw} />
                </div>
                <div>
                  <div className="font-medium">Tasa dentro de 3</div>
                  <RateCell rate={aliases.response_rate_within_3} />
                </div>
                <div>
                  <div className="font-medium">Tasa dentro de 10</div>
                  <RateCell rate={aliases.response_rate_within_10} />
                </div>
              </div>
              <div>
                Ciclo mediano: {String(cycles.median ?? "—")} · censurados:{" "}
                {String(cycles.events_censored ?? "—")} · con respuesta:{" "}
                {String(cycles.events_with_response ?? "—")}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Combinaciones (muestra)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              {combos.slice(0, 20).map((c) => (
                <div key={String(c.event_id)} className="rounded border p-2">
                  N={String(c.observed_number)} → C={String(c.candidate)} → {"{"}
                  {String(c.confirmers_key)}
                  {"}"} · score {String(c.score_raw)} · ancla {String((c.anchor as Record<string, unknown>)?.draw_id)}
                </div>
              ))}
              {combos.length === 0 ? <p className="text-muted-foreground">Sin combinaciones.</p> : null}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

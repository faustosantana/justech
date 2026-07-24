"use client";

import { useCallback, useEffect, useState } from "react";

import {
  HistoricalAnalyzerForm,
  RateCell,
} from "@/components/lottery/control-center/historical-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function PatronPage() {
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [confirmersSet, setConfirmersSet] = useState("");

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
        if (!body.candidate) throw new Error("Detalle de patrón requiere candidato T1");
        const payload = { ...body };
        if (confirmersSet.trim()) {
          payload.confirmers = confirmersSet
            .split(/[,\s]+/)
            .map((x) => Number(x))
            .filter((x) => Number.isInteger(x) && x >= 1 && x <= 100);
          delete payload.confirmer;
        } else if (!body.confirmer) {
          throw new Error("Indica confirmador V o conjunto V (ej. 6,9,11)");
        }
        const res = await apiClient.postLotteryNrHistoryPatternDetail(payload);
        setResult(res);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Error");
        setResult(null);
      } finally {
        setBusy(false);
      }
    },
    [confirmersSet],
  );

  const pattern = (result?.pattern || null) as Record<string, unknown> | null;
  const evidence = (result?.evidence || []) as Record<string, unknown>[];
  const stats = (pattern?.statistics || {}) as Record<string, unknown>;
  const aliases = (stats.aliases || {}) as Record<string, Record<string, unknown>>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Detalle de Patrón</h1>
      <p className="text-sm text-muted-foreground">
        Atómico N→C→V o combinación N→C→{"{V}"}. Muestra tasas, ciclos, censura y evidencia expandible.
      </p>
      <HistoricalAnalyzerForm
        catalog={catalog}
        title="Consultar patrón"
        submitLabel="Cargar detalle"
        onSubmit={onSubmit}
        busy={busy}
        error={error}
        extra={
          <label className="block text-xs">
            Conjunto de confirmadores (opcional, ej. 6,9,11) — prioriza sobre V simple
            <input
              className="mt-1 w-full rounded border px-2 py-1"
              value={confirmersSet}
              onChange={(e) => setConfirmersSet(e.target.value)}
              placeholder="6,9,11"
            />
          </label>
        }
      />
      {pattern ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{String(pattern.pattern_key)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Eventos: {String(pattern.event_count)} · {String(pattern.sample_tier)}</div>
            {pattern.sample_warning ? (
              <div className="text-amber-700 text-xs">{String(pattern.sample_warning)}</div>
            ) : null}
            <div className="grid gap-2 md:grid-cols-3">
              <div>
                <div className="font-medium">Próximo</div>
                <RateCell rate={aliases.response_rate_next_draw} />
              </div>
              <div>
                <div className="font-medium">Dentro 3</div>
                <RateCell rate={aliases.response_rate_within_3} />
              </div>
              <div>
                <div className="font-medium">Dentro 5</div>
                <RateCell rate={aliases.response_rate_within_5} />
              </div>
            </div>
            <div>Por año: {JSON.stringify(pattern.by_year || {})}</div>
          </CardContent>
        </Card>
      ) : null}
      {evidence.length ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Evidencia ({evidence.length})</CardTitle>
          </CardHeader>
          <CardContent className="max-h-96 space-y-2 overflow-auto text-xs">
            {evidence.map((e) => (
              <details key={String(e.event_id)} className="rounded border p-2">
                <summary>
                  {String(e.event_id)} · ancla{" "}
                  {String((e.anchor as Record<string, unknown>)?.draw_id)}
                </summary>
                <pre className="mt-2 whitespace-pre-wrap">{JSON.stringify(e, null, 2)}</pre>
              </details>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

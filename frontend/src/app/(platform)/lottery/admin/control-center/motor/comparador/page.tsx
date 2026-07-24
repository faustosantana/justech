"use client";

import { useCallback, useEffect, useState } from "react";

import { HistoricalAnalyzerForm } from "@/components/lottery/control-center/historical-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { COMPARE_MODE_LABELS, labelNrField } from "@/components/lottery/control-center/nr-labels";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { lotteryDisplayName } from "@/lib/lottery-display-names";

function formatValue(key: string, value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") {
    if (key === "lottery_id" || key.endsWith("_lottery_id")) {
      return lotteryDisplayName(value, value);
    }
    return labelNrField(value) !== value ? labelNrField(value) : value;
  }
  if (Array.isArray(value)) {
    return value.map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v))).join(", ");
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${labelNrField(k)}: ${formatValue(k, v)}`)
      .join(" · ");
  }
  return String(value);
}

function ResultCard({ item }: { item: Record<string, unknown> }) {
  const entries = Object.entries(item).filter(([k]) => !k.startsWith("_"));
  return (
    <div className="rounded border p-3 text-sm">
      <dl className="grid gap-1 sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key} className="min-w-0">
            <dt className="text-xs font-medium text-muted-foreground">{labelNrField(key)}</dt>
            <dd className="break-words">{formatValue(key, value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

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
      <h1 className="text-xl font-semibold">Comparador histórico</h1>
      <p className="text-sm text-muted-foreground">
        Compare candidatos, confirmadores, combinaciones o loterías sobre el universo activo. Toda
        cifra incluye soporte.
      </p>
      <HistoricalAnalyzerForm
        catalog={catalog}
        title="Comparar"
        submitLabel="Comparar"
        onSubmit={onSubmit}
        busy={busy}
        error={error}
        extra={
          <fieldset className="text-sm">
            <legend className="mb-1 font-medium">Modo de comparación</legend>
            <div className="flex flex-wrap gap-3">
              {(["candidates", "confirmers", "combinations", "lotteries"] as const).map((m) => (
                <label key={m} className="flex items-center gap-1 text-xs">
                  <input type="radio" checked={mode === m} onChange={() => setMode(m)} />
                  {COMPARE_MODE_LABELS[m]}
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
        <CardContent className="space-y-2">
          {items.map((it, idx) => (
            <ResultCard key={idx} item={it} />
          ))}
          {items.length === 0 ? <p className="text-muted-foreground text-sm">Sin resultados aún.</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}

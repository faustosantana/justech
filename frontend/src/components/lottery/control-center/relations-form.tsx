"use client";

import { useState } from "react";

import { NrDisclaimer } from "@/components/lottery/control-center/disclaimer";
import { TraceExpand } from "@/components/lottery/control-center/trace-expand";
import type { LotOption, MatchRow, RankRow } from "@/components/lottery/control-center/motor-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type Props = {
  catalog: LotOption[];
  mode?: "relations" | "prediction";
  onResult?: (result: Record<string, unknown>) => void;
};

export function RelationsAnalyzeForm({ catalog, mode = "relations", onResult }: Props) {
  const [selectedLots, setSelectedLots] = useState<string[]>([]);
  const [observed, setObserved] = useState("");
  const [occMode, setOccMode] = useState<"5" | "10" | "20" | "all" | "">("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [expandedRank, setExpandedRank] = useState<number | null>(null);

  const toggleLot = (id: string) => {
    setSelectedLots((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const run = async () => {
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      const n = Number(observed);
      if (!Number.isInteger(n) || n < 1 || n > 100) {
        throw new Error("El número observado debe estar entre 1 y 100");
      }
      if (selectedLots.length < 1) {
        throw new Error("Selecciona al menos una lotería (no se inventan)");
      }
      if (!occMode) {
        throw new Error("Selecciona cantidad: 5, 10, 20 o todas (sin default oculto)");
      }
      const body =
        occMode === "all"
          ? {
              observed_number: n,
              lottery_ids: selectedLots,
              occurrence_mode: "all" as const,
              occurrence_k: null,
            }
          : {
              observed_number: n,
              lottery_ids: selectedLots,
              occurrence_mode: "last_k" as const,
              occurrence_k: Number(occMode),
            };

      const res =
        mode === "prediction"
          ? await apiClient.postLotteryPredictionNumericRelations(body)
          : await apiClient.postLotteryNumericRelationsAnalyze(body);
      setResult(res);
      onResult?.(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Análisis falló");
    } finally {
      setAnalyzing(false);
    }
  };

  const ranking = (result?.ranking || result?.candidates || []) as RankRow[];
  const zeroScore = (result?.companions_score_zero || ranking.filter((r) => (r.score || 0) === 0)) as RankRow[];
  const meta = (result?.metadata || result?.analysis_metadata || {}) as Record<string, unknown>;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {mode === "prediction" ? "Predicción por Relaciones Numéricas" : "Analizar relaciones"}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Huawei interpreta; el motor calcula. Sin default oculto de cantidad.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <label className="text-sm">
              Número observado N
              <Input
                className="mt-1 w-28"
                value={observed}
                onChange={(e) => setObserved(e.target.value)}
                placeholder="1–100"
              />
            </label>
            <fieldset className="text-sm">
              <legend className="mb-1">Cantidad de ocurrencias</legend>
              <div className="flex flex-wrap gap-3">
                {(["5", "10", "20", "all"] as const).map((k) => (
                  <label key={k} className="flex items-center gap-1">
                    <input
                      type="radio"
                      name="occ"
                      checked={occMode === k}
                      onChange={() => setOccMode(k)}
                    />
                    {k === "all" ? "todas" : k}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
          <div>
            <div className="mb-1 text-sm font-medium">Loterías (una o varias)</div>
            <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto rounded border p-2">
              {catalog.map((l) => (
                <label key={l.id} className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    checked={selectedLots.includes(l.id)}
                    onChange={() => toggleLot(l.id)}
                  />
                  {l.name}
                </label>
              ))}
              {catalog.length === 0 ? (
                <span className="text-xs text-muted-foreground">Sin loterías cargadas</span>
              ) : null}
            </div>
          </div>
          <Button type="button" disabled={analyzing} onClick={() => void run()}>
            {analyzing
              ? "Analizando…"
              : mode === "prediction"
                ? "Ejecutar predicción"
                : "Analizar relaciones"}
          </Button>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {result ? (
        <>
          <NrDisclaimer />
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resultado</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div>Número observado: {String(result.observed_number ?? "—")}</div>
              <div>
                Compañeros de Tabla 1:{" "}
                {Array.isArray(result.direct_companions)
                  ? (result.direct_companions as number[]).join(", ")
                  : "—"}
              </div>
              <div>
                Loterías:{" "}
                {Array.isArray(result.lottery_names)
                  ? (result.lottery_names as string[]).join(", ")
                  : "—"}
              </div>
              <div>
                Sorteos analizados:{" "}
                {String(result.occurrences_used ?? result.occurrences_found ?? "—")}
              </div>
              <details className="text-xs text-muted-foreground">
                <summary className="cursor-pointer">Ver evidencia técnica</summary>
                <p className="mt-1">
                  Código madre (técnico): {String(result.mother_code ?? "—")}
                </p>
                <p>Metadata dedupe: {JSON.stringify(meta).slice(0, 240)}…</p>
              </details>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Ranking</CardTitle>
              <Button type="button" size="sm" variant="outline" onClick={() => setShowJson((v) => !v)}>
                {showJson ? "Ocultar JSON" : "Ver JSON"}
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {ranking.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin candidatos (score 0 o sin data).</p>
              ) : null}
              {ranking.map((r) => (
                <div key={r.number} className="rounded border p-3">
                  <button
                    type="button"
                    className="flex w-full flex-wrap justify-between gap-2 text-left text-sm font-medium"
                    onClick={() => setExpandedRank((cur) => (cur === r.number ? null : r.number))}
                  >
                    <span>
                      Compañero #{r.number} fortalecido · fuerza {r.score ?? 0} · confirmadores{" "}
                      {(r.matched_neighbors || r.neighbors || []).join(", ") || "ninguno"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {expandedRank === r.number ? "▲" : "▼"} traza
                    </span>
                  </button>
                  {expandedRank === r.number ? (
                    <div className="mt-2 space-y-2">
                      <div className="text-xs text-muted-foreground">
                        Código T2 {r.table2_code} · grupo {(r.table2_group || []).join(", ")} · matches{" "}
                        {(r.matches || []).length}
                      </div>
                      {(r.matches || []).map((m: MatchRow, idx: number) => (
                        <TraceExpand key={`${r.number}-${idx}`} match={m} />
                      ))}
                      {(r.matches || []).length === 0 ? (
                        <p className="text-xs italic text-muted-foreground">
                          Score 0 — sin vecinos coincidentes. {r.trace}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
              <div>
                <div className="mb-1 text-sm font-medium">Compañeros score 0</div>
                <p className="text-xs text-muted-foreground">
                  {zeroScore.map((z) => z.number).join(", ") || "—"}
                </p>
              </div>
              {showJson ? (
                <pre className="max-h-96 overflow-auto rounded bg-muted p-2 text-[10px]">
                  {JSON.stringify(result, null, 2)}
                </pre>
              ) : null}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

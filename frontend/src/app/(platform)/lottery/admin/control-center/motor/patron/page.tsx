"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import {
  HistoricalAnalyzerForm,
  RateCell,
} from "@/components/lottery/control-center/historical-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { canAccessLotteryAdmin } from "@/lib/lottery";
import { getUserRole } from "@/lib/auth";

export default function PatronPage() {
  const search = useSearchParams();
  const isAdmin = canAccessLotteryAdmin(getUserRole());
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    void apiClient
      .getLotteryNumericRelationsLotteries()
      .then((lots) => setCatalog((lots.items || []).filter((c) => c?.id)))
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "No se pudieron cargar las loterías"),
      );
  }, []);

  const onSubmit = useCallback(async (body: Record<string, unknown>) => {
    setBusy(true);
    setError(null);
    try {
      if (!body.candidate) {
        setError(null);
        throw new Error("Seleccione un compañero de Tabla 1.");
      }
      if (!body.confirmer && !body.confirmers) {
        throw new Error("Seleccione un número de confirmación.");
      }
      const res = await apiClient.postLotteryNrHistoryPatternDetail(body);
      setResult(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "No fue posible cargar el patrón.",
      );
      setResult(null);
    } finally {
      setBusy(false);
    }
  }, []);

  const pattern = (result?.pattern || null) as Record<string, unknown> | null;
  const evidence = (result?.evidence || []) as Record<string, unknown>[];
  const stats = (pattern?.statistics || {}) as Record<string, unknown>;
  const aliases = (stats.aliases || {}) as Record<string, Record<string, unknown>>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-blue-900">Consultar patrón</h1>
          <p className="text-sm text-muted-foreground">
            Revise cómo se comporta un número frente a su compañero de Tabla 1, la confirmación de
            Tabla 2 y el histórico.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/lottery/patrones">Volver a Patrones</Link>
        </Button>
      </div>

      <HistoricalAnalyzerForm
        catalog={catalog}
        title="Consultar patrón"
        submitLabel="Cargar detalle"
        onSubmit={onSubmit}
        busy={busy}
        error={error}
        requireCandidate
        requireConfirmer
        initialObserved={search.get("number") || search.get("observed") || ""}
        initialCandidate={search.get("candidate") || search.get("with") || ""}
        initialConfirmer={search.get("confirmer") || ""}
      />

      {pattern ? (
        <Card className="border-blue-100">
          <CardHeader>
            <CardTitle className="text-base text-blue-900">Resultado del patrón</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>
              Casos revisados: {String(pattern.event_count ?? "—")}
              {pattern.sample_warning ? (
                <span className="ml-2 text-amber-700">{String(pattern.sample_warning)}</span>
              ) : null}
            </div>
            <div className="grid gap-2 md:grid-cols-3">
              <div>
                <div className="font-medium">Próximo sorteo</div>
                <RateCell rate={aliases.response_rate_next_draw} />
              </div>
              <div>
                <div className="font-medium">Ventana corta</div>
                <RateCell rate={aliases.response_rate_short_window} />
              </div>
              <div>
                <div className="font-medium">Ventana amplia</div>
                <RateCell rate={aliases.response_rate_long_window} />
              </div>
            </div>
            {evidence.length > 0 && (
              <div className="pt-2">
                <p className="mb-1 font-medium">Evidencia reciente</p>
                <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
                  {evidence.slice(0, 8).map((ev, i) => (
                    <li key={i}>{String(ev.summary || ev.texto || ev.headline || "Caso histórico")}</li>
                  ))}
                </ul>
              </div>
            )}
            {isAdmin && (
              <details className="pt-2">
                <summary className="cursor-pointer text-xs font-medium text-slate-700">
                  Detalle técnico (administración)
                </summary>
                <pre className="mt-2 max-h-60 overflow-auto rounded bg-slate-50 p-2 text-[11px]">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </details>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import { RelationsAnalyzeForm } from "@/components/lottery/control-center/relations-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { ApiError, apiClient } from "@/lib/api";

export default function PrediccionRunPage() {
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const lots = await apiClient.getLotteryNumericRelationsLotteries();
      setCatalog((lots.items || []).filter((c) => c?.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar loterías");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Predicción · Relaciones Numéricas</h1>
      <p className="text-sm text-muted-foreground">
        Presentación del ranking histórico. No es una fórmula predictiva nueva ni garantía de
        acierto.
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <RelationsAnalyzeForm catalog={catalog} mode="prediction" />
    </div>
  );
}

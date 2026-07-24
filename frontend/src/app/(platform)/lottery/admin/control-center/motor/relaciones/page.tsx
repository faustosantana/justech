"use client";

import { useCallback, useEffect, useState } from "react";

import { RelationsAnalyzeForm } from "@/components/lottery/control-center/relations-form";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { ApiError, apiClient } from "@/lib/api";

export default function RelacionesPage() {
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
      <h1 className="text-xl font-semibold">Motor Matemático · Relaciones</h1>
      <p className="text-sm text-muted-foreground">
        Ejecución manual del motor histórico. Expandir ranking para ver trazas por punto.
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <RelationsAnalyzeForm catalog={catalog} mode="relations" />
    </div>
  );
}

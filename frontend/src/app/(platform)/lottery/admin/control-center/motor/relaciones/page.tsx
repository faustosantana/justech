"use client";

import { useCallback, useEffect, useState } from "react";

import { RelationsAnalyzeForm } from "@/components/lottery/control-center/relations-form";
import { MotorToolIntro } from "@/components/lottery/control-center/motor-tool-intro";
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
      <MotorToolIntro
        title="Relaciones numéricas"
        description="Número observado → Compañero (Tabla 1) → Confirmador (Tabla 2). La fuerza pertenece al compañero; el modelo técnico N→C→V queda en evidencia avanzada."
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <RelationsAnalyzeForm catalog={catalog} mode="relations" />
    </div>
  );
}

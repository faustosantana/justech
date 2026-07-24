"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type Motor = {
  key: string;
  name: string;
  description?: string;
  status: string;
  implemented?: boolean;
  version?: string | null;
  priority?: number;
  weight?: number | null;
  health?: string;
  last_run_at?: string | null;
  docs?: string | null;
  can_activate?: boolean;
  can_execute?: boolean;
  can_weight?: boolean;
};

export default function PrediccionesMotorsPage() {
  const [items, setItems] = useState<Motor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await apiClient.getLotteryPredictionMotors();
      setItems((res.items || []) as Motor[]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar motores");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (m: Motor) => {
    setMsg(null);
    setError(null);
    if (!m.implemented) {
      setError(`«${m.name}» es NO IMPLEMENTADO: no se puede activar ni ejecutar.`);
      return;
    }
    try {
      await apiClient.patchLotteryPredictionMotor(m.key, {
        enabled: m.status !== "ACTIVO",
      });
      setMsg(`${m.name}: ${m.status === "ACTIVO" ? "INACTIVO" : "ACTIVO"}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Predicciones · Motores</h1>
      <p className="text-sm text-muted-foreground">
        Solo motores implementados pueden activarse. Desactivados no se ejecutan en chat ni jobs.
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {msg ? <p className="text-sm text-green-700">{msg}</p> : null}
      <div className="space-y-3">
        {items.map((m) => (
          <Card key={m.key}>
            <CardHeader className="flex flex-row items-start justify-between gap-2">
              <div>
                <CardTitle className="text-base">{m.name}</CardTitle>
                <p className="text-xs text-muted-foreground">{m.description}</p>
              </div>
              <span className="rounded border px-2 py-0.5 text-xs font-medium">{m.status}</span>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="grid gap-1 md:grid-cols-2">
                <div>Versión: {m.version || "—"}</div>
                <div>Prioridad: {m.priority ?? "—"}</div>
                <div>Peso: {m.can_weight ? m.weight ?? "—" : "n/a"}</div>
                <div>Salud: {m.health || "—"}</div>
                <div>Última ejecución: {m.last_run_at || "—"}</div>
                <div>Docs: {m.docs || "—"}</div>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!m.implemented}
                onClick={() => void toggle(m)}
              >
                {!m.implemented
                  ? "No implementado"
                  : m.status === "ACTIVO"
                    ? "Desactivar"
                    : "Activar"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

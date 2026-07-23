"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

const SLOT_COUNT = 7;

export default function LotteryAIDefaultsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [slots, setSlots] = useState<string[]>(Array(SLOT_COUNT).fill(""));
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [thresholdsJson, setThresholdsJson] = useState("{}");
  const [thresholdsMeta, setThresholdsMeta] = useState<string>("defaults");
  const [thresholdsBusy, setThresholdsBusy] = useState(false);

  const loadThresholds = useCallback(async () => {
    try {
      const res = await apiClient.getLotteryAIAlertThresholds();
      const active = (res.active ?? res.defaults ?? {}) as Record<string, unknown>;
      setThresholdsJson(JSON.stringify(active, null, 2));
      setThresholdsMeta(String(res.version_label ?? "defaults"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar umbrales de alerta");
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIDefaults();
      setData(res);
      const raw = (res.defaults ?? res.lotteries ?? res.slots ?? []) as unknown[];
      const filled = Array(SLOT_COUNT)
        .fill("")
        .map((_, i) => String(raw[i] ?? ""));
      setSlots(filled);
      await loadThresholds();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar loterías predeterminadas");
    } finally {
      setLoading(false);
    }
  }, [loadThresholds]);

  useEffect(() => {
    void load();
  }, [load]);

  const setSlot = (index: number, value: string) => {
    setSlots((prev) => prev.map((s, i) => (i === index ? value : s)));
  };

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const payload: Record<string, unknown> = {
        ...(data ?? {}),
        defaults: slots.map((s) => s.trim()).filter(Boolean),
      };
      await apiClient.putLotteryAIDefaults(payload);
      setMsg("Loterías predeterminadas guardadas");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  const saveThresholds = async () => {
    setThresholdsBusy(true);
    setMsg(null);
    setError(null);
    try {
      const parsed = JSON.parse(thresholdsJson) as Record<string, unknown>;
      const res = await apiClient.putLotteryAIAlertThresholds({ payload: parsed });
      setThresholdsMeta(String(res.version_label ?? "saved"));
      if (res.active) {
        setThresholdsJson(JSON.stringify(res.active, null, 2));
      }
      setMsg("Umbrales de alerta guardados");
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("JSON de umbrales inválido");
      } else {
        setError(err instanceof ApiError ? err.message : "Error al guardar umbrales");
      }
    } finally {
      setThresholdsBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Loterías predeterminadas</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || busy}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void save()} disabled={busy || loading}>
            Guardar
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        Configure las {SLOT_COUNT} loterías predeterminadas (por tenant) que el agente IA usa en
        consultas sin contexto explícito.
      </p>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Slots de loterías (1–{SLOT_COUNT})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {slots.map((slot, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="w-6 shrink-0 text-right text-sm font-medium text-muted-foreground">
                {i + 1}
              </span>
              <Input
                placeholder={`Slug o ID de lotería ${i + 1}`}
                value={slot}
                onChange={(e) => setSlot(i, e.target.value)}
                className="font-mono text-sm"
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {data?.tenant_overrides !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Overrides por tenant</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="overflow-auto rounded text-xs">
              {JSON.stringify(data.tenant_overrides, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-sm">Umbrales de alerta (JSON)</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">versión: {thresholdsMeta}</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void loadThresholds()}
              disabled={thresholdsBusy || loading}
            >
              Recargar
            </Button>
            <Button size="sm" onClick={() => void saveThresholds()} disabled={thresholdsBusy || loading}>
              {thresholdsBusy ? "Guardando…" : "Guardar umbrales"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <textarea
            className="min-h-[220px] w-full rounded-md border border-border bg-background p-3 font-mono text-xs"
            value={thresholdsJson}
            onChange={(e) => setThresholdsJson(e.target.value)}
            spellCheck={false}
          />
        </CardContent>
      </Card>
    </div>
  );
}

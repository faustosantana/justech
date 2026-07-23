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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar loterías predeterminadas");
    } finally {
      setLoading(false);
    }
  }, []);

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
    </div>
  );
}

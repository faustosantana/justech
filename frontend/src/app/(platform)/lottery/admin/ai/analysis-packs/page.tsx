"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIAnalysisPacksPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [packs, setPacks] = useState<Record<string, unknown>[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIAnalysisPacks();
      setData(res);
      const items = (res.packs ?? res.items ?? (Array.isArray(res) ? res : [])) as Record<string, unknown>[];
      setPacks(items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar paquetes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const togglePack = (packId: string, currentEnabled: boolean) => {
    setPacks((prev) =>
      prev.map((p) =>
        String(p.id ?? p.name) === packId ? { ...p, enabled: !currentEnabled } : p,
      ),
    );
  };

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const payload = data ? { ...data, packs } : { packs };
      await apiClient.putLotteryAIAnalysisPacks(payload as Record<string, unknown>);
      setMsg("Paquetes actualizados");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar paquetes");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Paquetes de análisis</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || busy}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void save()} disabled={busy || loading}>
            Guardar cambios
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Paquetes disponibles</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {packs.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Sin paquetes registrados.</p>
          )}
          {packs.map((pack) => {
            const packId = String(pack.id ?? pack.name ?? "");
            const enabled = Boolean(pack.enabled ?? pack.is_enabled);
            return (
              <div
                key={packId}
                className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">
                    {String(pack.label ?? pack.name ?? packId)}
                  </p>
                  {pack.description && (
                    <p className="text-xs text-muted-foreground">{String(pack.description)}</p>
                  )}
                  {pack.tools_count !== undefined && (
                    <p className="text-xs text-muted-foreground">
                      {String(pack.tools_count)} tools
                    </p>
                  )}
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={() => togglePack(packId, enabled)}
                    aria-label={`${enabled ? "Desactivar" : "Activar"} ${packId}`}
                  />
                  <span>{enabled ? "Activo" : "Inactivo"}</span>
                </label>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import { useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIAnalysisPacksPage() {
  const { developerMode } = useLotteryAIDevMode();
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
      const items = (res.packs ?? res.items ?? []) as Record<string, unknown>[];
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

  const togglePack = (packKey: string, currentEnabled: boolean) => {
    setPacks((prev) =>
      prev.map((p) => (String(p.pack_key) === packKey ? { ...p, enabled: !currentEnabled } : p)),
    );
  };

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.putLotteryAIAnalysisPacks({
        packs: packs.map((p) => ({
          pack_key: p.pack_key,
          enabled: p.enabled,
          config: p.config,
          display_name: p.display_name ?? p.name,
        })),
      });
      setMsg("Paquetes actualizados");
      await load();
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

      <div className="grid gap-3 md:grid-cols-2">
        {packs.map((pack) => {
          const packKey = String(pack.pack_key ?? "");
          const title = String(pack.display_name ?? pack.name ?? pack.label ?? packKey);
          const enabled = Boolean(pack.enabled);
          return (
            <Card key={packKey || String(pack.id)}>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">{title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p className="text-muted-foreground">{String(pack.description ?? "")}</p>
                <MetricLine label="Intención" value={pack.intent} />
                <MetricLine
                  label="Tools"
                  value={Array.isArray(pack.tools) ? (pack.tools as string[]).length : pack.tools_count}
                />
                <MetricLine label="Profundidad" value={pack.depth} />
                <MetricLine label="Max insights" value={pack.max_insights} />
                <MetricLine label="Estado" value={pack.status ?? (enabled ? "activo" : "inactivo")} />
                <MetricLine label="Última modificación" value={pack.updated_at} />
                {developerMode ? (
                  <p className="font-mono text-[10px] text-muted-foreground">
                    {packKey} · {String(pack.id)}
                  </p>
                ) : null}
                <label className="mt-2 flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={() => togglePack(packKey, enabled)}
                  />
                  <span>{enabled ? "Activo" : "Inactivo"}</span>
                </label>
              </CardContent>
            </Card>
          );
        })}
      </div>
      {packs.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground">Sin paquetes. Se sembrarán al abrir el Centro IA.</p>
      )}
    </div>
  );
}

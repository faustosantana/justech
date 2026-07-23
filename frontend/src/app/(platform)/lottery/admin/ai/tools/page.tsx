"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIToolsPage() {
  const [tools, setTools] = useState<unknown[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyName, setBusyName] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAITools();
      setTools(res.items ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar tools");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (name: string, currentEnabled: boolean) => {
    setBusyName(name);
    setMsg(null);
    try {
      await apiClient.patchLotteryAITool(name, { enabled: !currentEnabled });
      setMsg(`Tool "${name}" ${!currentEnabled ? "activada" : "desactivada"}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Error al actualizar tool "${name}"`);
    } finally {
      setBusyName(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Tools</h2>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Catálogo de tools</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {tools.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Sin tools registradas.</p>
          )}
          {tools.map((t) => {
            const tool = t as Record<string, unknown>;
            const name = String(tool.name ?? tool.tool_name ?? "");
            const enabled = Boolean(tool.enabled ?? tool.is_enabled);
            const isBusy = busyName === name;
            return (
              <div
                key={name}
                className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">{name}</p>
                  {tool.description && (
                    <p className="text-xs text-muted-foreground">{String(tool.description)}</p>
                  )}
                  {tool.category && (
                    <p className="text-xs text-muted-foreground">Categoría: {String(tool.category)}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant={enabled ? "outline" : "ghost"}
                  onClick={() => void toggle(name, enabled)}
                  disabled={isBusy}
                  className="shrink-0"
                >
                  {isBusy ? "…" : enabled ? "Desactivar" : "Activar"}
                </Button>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import { useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIToolsPage() {
  const { developerMode } = useLotteryAIDevMode();
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

  const toggle = async (name: string, currentEnabled: boolean, critical: boolean, label: string) => {
    if (currentEnabled && critical) {
      if (
        !window.confirm(
          `«${label}» es crítica para la configuración activa. Desactivarla puede romper consultas. ¿Continuar? Se registrará en auditoría.`,
        )
      ) {
        return;
      }
    } else if (!window.confirm(`¿${currentEnabled ? "Desactivar" : "Activar"} «${label}»?`)) {
      return;
    }
    setBusyName(name);
    setMsg(null);
    try {
      await apiClient.patchLotteryAITool(name, {
        enabled: !currentEnabled,
        ...(currentEnabled && critical ? { confirm_critical_disable: true } : {}),
      });
      setMsg(`Tool «${label}» ${!currentEnabled ? "activada" : "desactivada"}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Error al actualizar «${label}»`);
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

      <div className="grid gap-3 md:grid-cols-2">
        {tools.map((t) => {
          const tool = t as Record<string, unknown>;
          const name = String(tool.name ?? tool.tool_name ?? "");
          const label = String(tool.label ?? tool.display_name ?? name);
          const enabled = Boolean(tool.enabled ?? tool.is_enabled);
          const isBusy = busyName === name;
          return (
            <Card key={name}>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">{label}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-muted-foreground">{String(tool.description ?? "Sin descripción")}</p>
                {tool.examples ? (
                  <p className="text-xs text-muted-foreground">Ejemplos: {String(tool.examples)}</p>
                ) : null}
                {developerMode ? (
                  <p className="font-mono text-[10px] text-muted-foreground">{name}</p>
                ) : null}
                <div className="flex items-center justify-between">
                  <span className="text-xs">{enabled ? "Activa" : "Inactiva"}{tool.critical ? " · crítica" : ""}</span>
                  <Button
                    size="sm"
                    variant={enabled ? "outline" : "ghost"}
                    onClick={() => void toggle(name, enabled, Boolean(tool.critical), label)}
                    disabled={isBusy}
                  >
                    {isBusy ? "…" : enabled ? "Desactivar" : "Activar"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
      {tools.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground">Sin tools registradas. Ejecute ensure_seeded / recargue.</p>
      )}
    </div>
  );
}

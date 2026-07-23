"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIVersionsPage() {
  const [versions, setVersions] = useState<unknown[]>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIVersions();
      setVersions(res.items ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar versiones");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const publish = async (id: string) => {
    if (!window.confirm(`¿Publicar versión "${id}"?`)) return;
    setBusyId(id);
    setMsg(null);
    try {
      await apiClient.postLotteryAIVersionPublish(id);
      setMsg(`Versión "${id}" publicada`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al publicar");
    } finally {
      setBusyId(null);
    }
  };

  const rollback = async (id: string) => {
    if (!window.confirm(`¿Revertir a la versión "${id}"?`)) return;
    setBusyId(id);
    setMsg(null);
    try {
      await apiClient.postLotteryAIVersionRollback(id);
      setMsg(`Revertido a versión "${id}"`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al revertir");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Versiones</h2>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Historial de versiones</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {versions.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">Sin versiones.</p>
            )}
            {versions.map((v) => {
              const ver = v as Record<string, unknown>;
              const id = String(ver.id ?? "");
              const isActive = ver.status === "active" || ver.is_active;
              const isSelected = selected && String(selected.id) === id;
              const isBusy = busyId === id;
              return (
                <div
                  key={id}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 ${
                    isSelected ? "border-primary bg-primary/5" : "border-border/60"
                  }`}
                >
                  <button
                    type="button"
                    className="min-w-0 text-left"
                    onClick={() => setSelected(ver)}
                  >
                    <p className="text-sm font-medium">
                      v{String(ver.version ?? ver.tag ?? id)}
                      {isActive && (
                        <span className="ml-1.5 rounded bg-green-100 px-1 py-0.5 text-xs text-green-700">
                          activa
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {String(ver.status ?? "—")} · {String(ver.created_at ?? "—")}
                    </p>
                  </button>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => void publish(id)}
                      disabled={isBusy || isActive === true}
                    >
                      {isBusy ? "…" : "Publicar"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void rollback(id)}
                      disabled={isBusy}
                    >
                      Revertir
                    </Button>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Detalle de versión</CardTitle>
          </CardHeader>
          <CardContent>
            {!selected ? (
              <p className="text-sm text-muted-foreground">Selecciona una versión para comparar.</p>
            ) : (
              <pre className="overflow-auto rounded text-xs">
                {JSON.stringify(selected, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

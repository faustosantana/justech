"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAISessionsPage() {
  const [sessions, setSessions] = useState<unknown[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAISessions({ limit: 50 });
      setSessions(res.items ?? []);
      setTotal(res.total ?? 0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar sesiones");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Sesiones</h2>
          {total > 0 && (
            <p className="text-xs text-muted-foreground">{total} sesiones totales</p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Sesiones recientes (admin)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {sessions.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Sin sesiones.</p>
          )}
          {sessions.map((s) => {
            const session = s as Record<string, unknown>;
            const id = String(session.id ?? "");
            return (
              <div
                key={id}
                className="rounded-lg border border-border/60 px-3 py-2 font-mono text-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium">{id}</p>
                    {session.user_id && (
                      <p className="text-muted-foreground">Usuario: {String(session.user_id)}</p>
                    )}
                    {session.tenant_id && (
                      <p className="text-muted-foreground">Tenant: {String(session.tenant_id)}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-right text-muted-foreground">
                    {session.message_count !== undefined && (
                      <p>{String(session.message_count)} mensajes</p>
                    )}
                    <p>{String(session.last_message_at ?? session.updated_at ?? session.created_at ?? "—")}</p>
                    <p>
                      {String(session.status ?? session.state ?? "—")}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

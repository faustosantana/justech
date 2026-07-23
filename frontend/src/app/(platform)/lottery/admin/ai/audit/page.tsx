"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

const PAGE_SIZE = 50;

export default function LotteryAIAuditPage() {
  const [entries, setEntries] = useState<unknown[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (off = 0) => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.getLotteryAIAudit({ limit: PAGE_SIZE, offset: off });
        setEntries(res.items ?? []);
        setTotal(res.total ?? 0);
        setOffset(off);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Error al cargar auditoría");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void load(0);
  }, [load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Auditoría</h2>
          {total > 0 && (
            <p className="text-xs text-muted-foreground">{total} entradas totales</p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => void load(offset)} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Registro de auditoría</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {entries.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Sin entradas de auditoría.</p>
          )}
          {entries.map((e, i) => {
            const entry = e as Record<string, unknown>;
            const id = String(entry.id ?? i);
            return (
              <div
                key={id}
                className="grid grid-cols-[auto_1fr] gap-x-3 rounded-lg border border-border/60 px-3 py-2 font-mono text-xs"
              >
                <span className="text-muted-foreground">
                  {String(entry.timestamp ?? entry.created_at ?? "—")}
                </span>
                <div>
                  <span className="font-medium">{String(entry.action ?? entry.event ?? "—")}</span>
                  {entry.actor && (
                    <span className="ml-2 text-muted-foreground">por {String(entry.actor)}</span>
                  )}
                  {entry.resource && (
                    <span className="ml-2 text-muted-foreground">{String(entry.resource)}</span>
                  )}
                  {entry.details && (
                    <p className="mt-0.5 text-muted-foreground">
                      {typeof entry.details === "string"
                        ? entry.details
                        : JSON.stringify(entry.details)}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {(hasPrev || hasNext) && (
        <div className="flex justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void load(offset - PAGE_SIZE)}
            disabled={!hasPrev || loading}
          >
            Anterior
          </Button>
          <span className="text-xs text-muted-foreground">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void load(offset + PAGE_SIZE)}
            disabled={!hasNext || loading}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}

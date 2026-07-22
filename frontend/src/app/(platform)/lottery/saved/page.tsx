"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryModule, DISCLAIMER, type LotterySavedQuery } from "@/lib/lottery";

export default function LotterySavedQueriesPage() {
  const router = useRouter();
  const [items, setItems] = useState<LotterySavedQuery[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError("Sin permiso");
      return;
    }
    try {
      const res = await apiClient.listLotterySavedQueries();
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las consultas");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const remove = async (id: string) => {
    await apiClient.deleteLotterySavedQuery(id);
    await load();
  };

  const saveRename = async () => {
    if (!renameId || !renameValue.trim()) return;
    await apiClient.renameLotterySavedQuery(renameId, renameValue.trim());
    setRenameId(null);
    await load();
  };

  return (
    <AppShell title="Consultas guardadas" description="Reutiliza consultas históricas">
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Inicio
        </Link>
        <Link href="/lottery/favorites" className="text-primary underline">
          Favoritos
        </Link>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {items.length === 0 && !error && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Aún no hay consultas guardadas. Guárdalas desde el chat o las herramientas de consulta.
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {items.map((q) => (
          <Card key={q.id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{q.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {q.description && <p className="text-muted-foreground">{q.description}</p>}
              <p className="text-xs text-muted-foreground">
                Tipo: {q.query_type || "—"} · Ejecuciones: {q.run_count ?? 0}
                {q.last_run_at ? ` · Última: ${q.last_run_at}` : ""}
              </p>
              {renameId === q.id ? (
                <div className="flex flex-wrap gap-2">
                  <Input
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    aria-label="Nuevo nombre"
                  />
                  <Button size="sm" onClick={() => void saveRename()}>
                    Guardar
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setRenameId(null)}>
                    Cancelar
                  </Button>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setRenameId(q.id);
                      setRenameValue(q.name);
                    }}
                  >
                    Renombrar
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => void remove(q.id)}>
                    Eliminar
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">{DISCLAIMER}</p>
    </AppShell>
  );
}

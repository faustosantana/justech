"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { LotteryCatalogCard } from "@/lib/lottery";

function expedienteHref(number: string | number, lotteryIds: string[]) {
  const n = String(number).replace(/\D/g, "");
  if (!n) return "/lottery/admin/control-center/motor/historial-numero";
  const params = new URLSearchParams({
    number: n,
    auto: "1",
    featured: "1",
  });
  if (lotteryIds.length) params.set("lottery_ids", lotteryIds.join(","));
  return `/lottery/admin/control-center/motor/historial-numero?${params.toString()}`;
}

function NumberChip({
  value,
  lotteryIds,
}: {
  value: string;
  lotteryIds: string[];
}) {
  const href = expedienteHref(value, lotteryIds);
  return (
    <Link
      href={href}
      className="inline-flex flex-col items-center justify-center rounded-md border border-primary/30 bg-primary/5 px-2 py-1 text-primary transition hover:bg-primary/15"
      title={`Analizar este número: ${value}`}
      aria-label={`Analizar este número ${value}`}
    >
      <span className="font-mono text-base font-semibold">{value}</span>
      <span className="text-[10px] font-medium leading-tight">Analizar este número</span>
    </Link>
  );
}

export default function ControlCenterHubPage() {
  const [cards, setCards] = useState<LotteryCatalogCard[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryCatalog({
        featured_only: true,
        page: 1,
        page_size: 12,
      });
      setCards(res.items || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las destacadas");
      setCards([]);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const allFeaturedIds = useMemo(() => cards.map((c) => c.id), [cards]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Inteligencia numérica</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Resultados recientes de las siete loterías destacadas. Pulse cualquier número para abrir
          su expediente: condición, candidato fortalecido, confirmadores y qué ocurrió después.
        </p>
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {busy ? (
        <p className="text-sm text-muted-foreground">Cargando destacadas…</p>
      ) : cards.length === 0 ? (
        <Card>
          <CardContent className="space-y-3 pt-6 text-sm text-muted-foreground">
            <p>
              No hay loterías marcadas como destacadas. En DEV ejecute el seed canónico de siete
              loterías y vuelva a cargar.
            </p>
            <Button type="button" variant="outline" onClick={() => void load()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cards.map((card) => {
            const nums = (card.last_numbers || []).map(String);
            const scopeIds = [card.id];
            return (
              <Card key={card.id} className="overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{card.commercial_name || card.name}</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    {card.last_draw_date
                      ? `Último sorteo: ${card.last_draw_date}`
                      : "Sin fecha de último sorteo"}
                  </p>
                </CardHeader>
                <CardContent className="space-y-3">
                  {nums.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin números recientes.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {nums.map((n) => (
                        <NumberChip key={`${card.id}-${n}`} value={n} lotteryIds={scopeIds} />
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <Link
                      href={expedienteHref(nums[0] || "35", scopeIds)}
                      className="text-primary underline-offset-2 hover:underline"
                    >
                      Analizar este número
                    </Link>
                    <span className="text-muted-foreground">·</span>
                    <Link
                      href={expedienteHref(nums[0] || "35", allFeaturedIds)}
                      className="text-muted-foreground underline-offset-2 hover:underline"
                    >
                      Analizar en las 7 destacadas
                    </Link>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <p className="rounded-md border border-amber-200/80 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-50">
        Las señales muestran relaciones y respuestas históricas. No garantizan resultados futuros.
      </p>

      <section className="space-y-2 border-t pt-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Herramientas del motor
        </h2>
        <p className="text-sm text-muted-foreground">
          Disponibles después del análisis principal. No alteran fórmulas ni el histórico.
        </p>
        <div className="flex flex-wrap gap-2 text-sm">
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/historial-numero">
            Historial del Número
          </Link>
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/table1">
            Tabla 1
          </Link>
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/table2">
            Tabla 2
          </Link>
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/groups-table1">
            Agrupaciones T1
          </Link>
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/groups-table2">
            Agrupaciones T2
          </Link>
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/relaciones">
            Relaciones
          </Link>
          <Link className="rounded-md border px-3 py-1.5 hover:bg-muted" href="/lottery/admin/control-center/motor/auditoria">
            Auditoría
          </Link>
        </div>
      </section>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Brain, RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type Observation = Awaited<ReturnType<typeof apiClient.listObservations>>["items"][number];
type Brief = Record<string, unknown>;

export function InteligenciaComercialSection() {
  const [items, setItems] = useState<Observation[]>([]);
  const [selected, setSelected] = useState<Observation | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(true);
  const [enriching, setEnriching] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.listObservations({ limit: 80, status: "pending_review" });
      const all = await apiClient.listObservations({ limit: 80 });
      const merged = [...res.items];
      for (const it of all.items) {
        if (!merged.find((m) => m.id === it.id)) merged.push(it);
      }
      setItems(merged);
      const pick = selected && merged.find((m) => m.id === selected.id) ? selected : merged[0] ?? null;
      setSelected(pick);
    } finally {
      setLoading(false);
    }
  }, [selected]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selected) {
      setBrief(null);
      return;
    }
    setAnswer(null);
    const existing = selected.commercial_brief as Brief | null | undefined;
    if (existing) {
      setBrief(existing);
      return;
    }
    setEnriching(true);
    apiClient
      .getObservationIntelligence(selected.id)
      .then((res) => setBrief(res.brief))
      .finally(() => setEnriching(false));
  }, [selected]);

  const detected = (brief?.detected ?? {}) as Record<string, unknown>;
  const recommendations = (brief?.recommendations ?? []) as string[];

  const ask = async (q: string) => {
    if (!selected) return;
    const res = await apiClient.askObservation(selected.id, q);
    setAnswer(res.answer);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" asChild>
          <Link href="/apps/agentes-ia/agentes">Bandeja inteligente</Link>
        </Button>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={cn("mr-1 h-3.5 w-3.5", loading && "animate-spin")} />
          Actualizar
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm">Solicitudes detectadas</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[70vh] overflow-auto p-0">
            {items.map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => setSelected(row)}
                className={cn(
                  "w-full border-b border-border px-3 py-2 text-left text-xs hover:bg-muted/50",
                  selected?.id === row.id && "bg-primary/10",
                )}
              >
                <p className="truncate font-medium">{row.customer?.name || row.raw_from || "Contacto"}</p>
                <p className="truncate text-muted-foreground">{row.summary}</p>
              </button>
            ))}
            {!loading && items.length === 0 && (
              <p className="p-4 text-xs text-muted-foreground">Sin solicitudes pendientes.</p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {!selected && !loading && (
            <p className="text-sm text-muted-foreground">Seleccione una solicitud para ver el análisis.</p>
          )}
          {selected && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Brain className="h-4 w-4" />
                    Resumen detectado
                    {enriching && <span className="text-xs font-normal text-muted-foreground">Analizando…</span>}
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  <Stat label="Producto" value={String(detected.product ?? "—")} />
                  <Stat label="Cantidad" value={String(detected.quantity ?? "—")} />
                  <Stat label="Cliente" value={String(detected.customer ?? "—")} />
                  <Stat label="Canal" value={selected.channel} />
                </CardContent>
              </Card>
              {brief?.executive_summary && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Resumen ejecutivo</CardTitle></CardHeader>
                  <CardContent className="whitespace-pre-wrap text-sm text-muted-foreground">
                    {String(brief.executive_summary)}
                  </CardContent>
                </Card>
              )}
              {recommendations.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Recomendaciones</CardTitle></CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    {recommendations.map((r, i) => (
                      <p key={i}>· {r}</p>
                    ))}
                  </CardContent>
                </Card>
              )}
              <div className="flex flex-wrap gap-2">
                {["¿Ya le hemos vendido esto?", "¿A cuánto lo hemos vendido?", "¿Dónde lo compramos normalmente?"].map((q) => (
                  <Button key={q} variant="outline" size="sm" onClick={() => void ask(q)}>
                    <Sparkles className="mr-1 h-3.5 w-3.5" />
                    {q}
                  </Button>
                ))}
              </div>
              {answer && (
                <Card>
                  <CardContent className="py-4 text-sm whitespace-pre-wrap">{answer}</CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

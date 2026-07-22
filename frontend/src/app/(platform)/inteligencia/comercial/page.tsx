"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Brain,
  MessageCircle,
  RefreshCw,
  Search,
  Send,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type Observation = Awaited<ReturnType<typeof apiClient.listObservations>>["items"][number];
type Brief = Record<string, unknown>;

const QUICK_QUESTIONS = [
  "¿Ya le hemos vendido esto?",
  "¿A cuánto lo hemos vendido?",
  "¿Dónde lo compramos normalmente?",
];

export default function InteligenciaComercialPage() {
  const [items, setItems] = useState<Observation[]>([]);
  const [selected, setSelected] = useState<Observation | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(true);
  const [enriching, setEnriching] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);

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

  const loadBrief = useCallback(async (id: string, existing?: Brief | null) => {
    if (existing) {
      setBrief(existing);
      return;
    }
    setEnriching(true);
    try {
      const res = await apiClient.getObservationIntelligence(id);
      setBrief(res.brief);
    } finally {
      setEnriching(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selected) {
      setAnswer(null);
      void loadBrief(selected.id, selected.commercial_brief as Brief | null | undefined);
    } else {
      setBrief(null);
    }
  }, [selected, loadBrief]);

  const runAction = async (action: string) => {
    if (!selected) return;
    setActing(action);
    try {
      await apiClient.observationAction(selected.id, action);
      await load();
    } finally {
      setActing(null);
    }
  };

  const ask = async (q: string) => {
    if (!selected || !q.trim()) return;
    setQuestion(q);
    const res = await apiClient.askObservation(selected.id, q);
    setAnswer(res.answer);
  };

  const reviewContext = async (sources: string[]) => {
    if (!selected) return;
    setEnriching(true);
    try {
      const res = await apiClient.reviewObservationContext(selected.id, sources);
      setBrief(res.brief);
    } finally {
      setEnriching(false);
    }
  };

  const demo = async () => {
    setEnriching(true);
    try {
      const obs = await apiClient.ingestObservation({
        channel: "whatsapp",
        body: "Necesito cotización para 25 laptops Dell i5 16GB 512GB SSD para entrega urgente.",
        from_name: "Distribuidora El Catador",
        from_address: "+18095559999",
        analyze: true,
      });
      setSelected(obs);
      await load();
    } finally {
      setEnriching(false);
    }
  };

  const detected = (brief?.detected ?? {}) as Record<string, unknown>;
  const sales = (brief?.sales_history ?? {}) as Record<string, unknown>;
  const suppliers = (brief?.suppliers ?? []) as Record<string, unknown>[];
  const similar = (brief?.similar_requests ?? {}) as Record<string, unknown>;
  const recommendations = (brief?.recommendations ?? []) as string[];
  const drafts = (brief?.drafts ?? {}) as Record<string, string>;
  const contextSources = (brief?.context_sources_available ?? []) as { key: string; label: string; count: number }[];

  return (
    <AppShell hideHeaderTitle>
      <AdminPageHeader
        title="Inteligencia Comercial"
        description="Hermes analiza solicitudes automáticamente · Historial Odoo · Proveedores · Recomendaciones · Sin envíos automáticos"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/inteligencia/bandeja">Bandeja Inteligente</Link>
            </Button>
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
              <RefreshCw className={cn("mr-1 h-3.5 w-3.5", loading && "animate-spin")} />
              Actualizar
            </Button>
            <Button size="sm" onClick={() => void demo()} disabled={enriching}>
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              Demo RFQ
            </Button>
          </div>
        }
      />

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
                <p className="font-medium truncate">{row.customer?.name || row.raw_from || "Contacto"}</p>
                <p className="text-muted-foreground truncate">{row.summary}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {row.channel} · {Math.round(row.confidence * 100)}%
                </p>
              </button>
            ))}
            {!loading && items.length === 0 && (
              <p className="p-4 text-xs text-muted-foreground">Sin solicitudes. Use Demo RFQ o sincronice correos.</p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {!selected && !loading && (
            <p className="text-sm text-muted-foreground">Seleccione una solicitud para ver el análisis comercial.</p>
          )}

          {selected && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    Resumen detectado
                    {enriching && <span className="text-xs font-normal text-muted-foreground">Analizando…</span>}
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                  <Stat label="Producto" value={String(detected.product ?? "—")} />
                  <Stat label="Cantidad" value={String(detected.quantity ?? "—")} />
                  <Stat label="Categoría" value={String(detected.category ?? "—")} />
                  <Stat label="Confianza" value={`${Math.round((Number(detected.confidence) || selected.confidence) * 100)}%`} />
                  <Stat label="Cliente" value={String(detected.customer ?? "—")} />
                  <Stat label="Marca" value={String(detected.brand ?? "—")} />
                  <Stat label="Prioridad" value={String(detected.priority ?? "—")} />
                  <Stat label="Canal" value={selected.channel} />
                </CardContent>
              </Card>

              {brief?.executive_summary && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Resumen ejecutivo</CardTitle></CardHeader>
                  <CardContent className="text-sm whitespace-pre-wrap text-muted-foreground">
                    {String(brief.executive_summary)}
                  </CardContent>
                </Card>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader><CardTitle className="text-base">Historial comercial</CardTitle></CardHeader>
                  <CardContent className="text-sm space-y-2">
                    {sales.available === false ? (
                      <p className="text-muted-foreground text-xs">Odoo no disponible o sin permiso de ventas.</p>
                    ) : (
                      <>
                        <p className="text-xs">{String(sales.summary || "Consultando historial…")}</p>
                        {(sales.customers as Record<string, unknown>[] | undefined)?.map((c, i) => (
                          <div key={i} className="rounded border px-2 py-1 text-xs">
                            <p className="font-medium">{String(c.name ?? c.customer ?? "Cliente")}</p>
                          </div>
                        ))}
                        {sales.price_stats && (
                          <p className="text-xs text-muted-foreground">
                            Precio prom.: RD${String((sales.price_stats as Record<string, unknown>).avg ?? "—")}
                          </p>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader><CardTitle className="text-base">Proveedores relacionados</CardTitle></CardHeader>
                  <CardContent className="space-y-2 text-xs">
                    {suppliers.length === 0 && <p className="text-muted-foreground">Sin registros en listas de precios.</p>}
                    {suppliers.map((s, i) => (
                      <div key={i} className="flex justify-between gap-2 border-b border-border/50 pb-1">
                        <span className="font-medium">{String(s.name)}</span>
                        <span className="text-muted-foreground">
                          {s.last_price ? `RD$${s.last_price}` : s.last_seen ? String(s.last_seen) : "—"}
                        </span>
                      </div>
                    ))}
                    {brief?.price_average != null && (
                      <p className="pt-1 text-muted-foreground">Promedio listas: RD${String(brief.price_average)}</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {similar.observations_count != null && Number(similar.observations_count) > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Cotizaciones similares</CardTitle></CardHeader>
                  <CardContent className="text-sm text-muted-foreground">{String(similar.message)}</CardContent>
                </Card>
              )}

              {contextSources.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Contexto adicional disponible</CardTitle>
                    <p className="text-xs text-muted-foreground font-normal">
                      He encontrado información adicional que podría mejorar el análisis. No se lee automáticamente.
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <ul className="text-xs text-muted-foreground list-disc pl-4">
                      {contextSources.map((s) => (
                        <li key={s.key}>{s.label} ({s.count})</li>
                      ))}
                    </ul>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => void reviewContext(["all"])} disabled={enriching}>
                        Revisar todo
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => void reviewContext(["email"])} disabled={enriching}>
                        Revisar correos
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void loadBrief(selected.id, selected.commercial_brief as Brief)}>
                        Continuar sin revisar
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {recommendations.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Recomendaciones</CardTitle></CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-4 text-sm space-y-1">
                      {recommendations.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {(drafts.client_email || drafts.internal_note) && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Borradores (pendientes de aprobación)</CardTitle></CardHeader>
                  <CardContent className="space-y-3 text-xs">
                    {drafts.client_email && (
                      <div className="rounded bg-muted/40 p-2">
                        <p className="font-medium mb-1">Respuesta al cliente</p>
                        <pre className="whitespace-pre-wrap">{drafts.client_email}</pre>
                      </div>
                    )}
                    {drafts.internal_note && (
                      <div className="rounded bg-muted/40 p-2">
                        <p className="font-medium mb-1">Nota interna</p>
                        <pre className="whitespace-pre-wrap">{drafts.internal_note}</pre>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader><CardTitle className="text-base">Preguntar sobre esta solicitud</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-1">
                    {QUICK_QUESTIONS.map((q) => (
                      <Button key={q} size="sm" variant="outline" className="h-7 text-xs" onClick={() => void ask(q)}>
                        {q}
                      </Button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      className="flex-1 rounded border border-input px-2 py-1.5 text-sm"
                      placeholder="Ej: ¿Ya le hemos vendido esto?"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && void ask(question)}
                    />
                    <Button size="sm" onClick={() => void ask(question)}>
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                  {answer && (
                    <p className="rounded-lg border bg-muted/30 p-3 text-sm">
                      <MessageCircle className="inline h-4 w-4 mr-1" />
                      {answer}
                    </p>
                  )}
                </CardContent>
              </Card>

              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => void runAction("create_draft")} disabled={!!acting}>
                  Crear borrador
                </Button>
                <Button size="sm" variant="outline" onClick={() => void runAction("create_task")} disabled={!!acting}>
                  Crear tarea
                </Button>
                <Button size="sm" variant="outline" onClick={() => void runAction("create_supplier")} disabled={!!acting}>
                  Registrar proveedor
                </Button>
                <Button size="sm" variant="outline" onClick={() => void runAction("validate")} disabled={!!acting}>
                  Validar
                </Button>
                <Button size="sm" variant="ghost" onClick={() => selected && void loadBrief(selected.id)} disabled={enriching}>
                  <Search className="mr-1 h-3.5 w-3.5" />
                  Re-analizar
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium truncate" title={value}>{value}</p>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Dices,
  MessageSquare,
  RefreshCw,
  Star,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { SectionCard } from "@/components/ui/section-card";
import { Badge } from "@/components/ui/badge";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  canAccessLotteryModule,
  healthStatusLabel,
  type LotteryCatalogCard,
  type LotteryDashboardV3,
} from "@/lib/lottery";

function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("es-DO", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

function CatalogMiniCard({ card }: { card: LotteryCatalogCard }) {
  return (
    <Link
      href={`/lottery/lotteries/${card.slug}`}
      className="block rounded-xl border border-border/60 bg-card/80 p-3 transition hover:border-primary/30 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium leading-tight">{card.commercial_name || card.name}</p>
        {card.is_favorite && <Star className="h-3.5 w-3.5 shrink-0 fill-amber-400 text-amber-500" />}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {card.last_draw_date || "Sin fecha"} · {card.draw_count.toLocaleString()} sorteos
      </p>
      {card.last_numbers.length > 0 && (
        <p className="mt-2 font-mono text-sm tracking-wide">{card.last_numbers.join(" · ")}</p>
      )}
      <div className="mt-2">
        <Badge
          variant={
            card.health_status === "healthy"
              ? "success"
              : card.health_status === "error"
                ? "danger"
                : "muted"
          }
        >
          {healthStatusLabel(card.health_status)}
        </Badge>
      </div>
    </Link>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4 animate-pulse" role="status" aria-label="Cargando dashboard">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-muted/60" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="h-48 rounded-xl bg-muted/60" />
        <div className="h-48 rounded-xl bg-muted/60" />
      </div>
    </div>
  );
}

export default function LotteryPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dash, setDash] = useState<LotteryDashboardV3 | null>(null);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError("Sin permiso lottery.access");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getLotteryDashboardV3();
      setDash(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(id);
  }, [load]);

  const coverage = dash?.coverage ?? {};
  const syncSummary = dash?.sync_summary ?? {};

  return (
    <AppShell
      title="Resultados de Loterías"
      description="Centro de operaciones — Lottery 3.0"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button asChild variant="outline" size="sm">
          <Link href="/lottery/search">Consultar</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/lottery/lotteries">Catálogo</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/lottery/statistics">Estadísticas</Link>
        </Button>
        <Button variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
      </div>

      {loading && <DashboardSkeleton />}

      {error && (
        <Card className="border-destructive/40">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <p className="text-sm text-destructive">{error}</p>
            <Button size="sm" variant="outline" onClick={() => void load()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {!loading && dash && (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
            <MetricCard label="Loterías activas" value={dash.lotteries_active.toLocaleString()} tone="primary" href="/lottery/lotteries" />
            <MetricCard label="Visibles" value={dash.lotteries_visible.toLocaleString()} tone="muted" href="/lottery/lotteries" />
            <MetricCard label="Con sync" value={dash.lotteries_synced.toLocaleString()} tone="primary" />
            <MetricCard label="Resultados hoy" value={dash.results_today.toLocaleString()} tone="success" />
            <MetricCard label="Esperados hoy (visibles)" value={(dash.expected_today ?? 0).toLocaleString()} tone="muted" />
            <MetricCard
              label="Pendientes sync"
              value={(dash.pending_sync_enabled ?? dash.pending_results ?? 0).toLocaleString()}
              tone="warning"
              delta="solo sync_enabled"
            />
            <MetricCard
              label="Pendientes visibles"
              value={(dash.pending_visible ?? 0).toLocaleString()}
              tone="warning"
              delta="incluye sin sync"
            />
            <MetricCard label="Sorteos históricos" value={dash.draws_historical.toLocaleString()} tone="muted" />
            <MetricCard label="Números almacenados" value={dash.numbers_stored.toLocaleString()} tone="muted" />
            <MetricCard label="Última actualización" value={formatDateTime(dash.last_update_at)} tone="warning" />
            <MetricCard label="Última sync" value={formatDateTime(dash.last_sync_at)} tone="muted" />
            <MetricCard label="Próxima sync" value={formatDateTime(dash.next_sync_at)} tone="muted" />
            <MetricCard
              label="Worker"
              value={dash.worker_status?.worker_owns_ticks ? "standalone" : "in-API"}
              tone={dash.worker_status?.standalone_configured ? "success" : "warning"}
              delta={String(dash.worker_status?.scheduler_mode || "")}
            />
            <MetricCard
              label="Hoy local"
              value={dash.local_today || "—"}
              tone="muted"
              delta={dash.timezone || "America/Santo_Domingo"}
            />
            <MetricCard
              label="Fuentes saludables"
              value={dash.sources_healthy.toLocaleString()}
              tone="success"
              delta={`${dash.sources_error} con error`}
            />
            <MetricCard
              label="Fuentes con error"
              value={dash.sources_error.toLocaleString()}
              tone={dash.sources_error > 0 ? "danger" : "muted"}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              <SectionCard title="Últimos resultados" description="Sorteos más recientes por lotería visible" href="/lottery/lotteries" actionLabel="Ver catálogo">
                {dash.latest_results.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No hay resultados recientes.</p>
                ) : (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {dash.latest_results.map((item) => (
                      <Link
                        key={`${item.slug}-${item.date}`}
                        href={`/lottery/lotteries/${item.slug}`}
                        className="rounded-xl border border-border/60 p-3 transition hover:border-primary/30"
                      >
                        <p className="font-medium">{item.lottery}</p>
                        <p className="text-xs text-muted-foreground">{item.date || "—"}</p>
                        {item.numbers.length > 0 && (
                          <p className="mt-2 font-mono text-sm">{item.numbers.join(" · ")}</p>
                        )}
                      </Link>
                    ))}
                  </div>
                )}
              </SectionCard>

              <SectionCard
                title="Operación de sync"
                description="Ventanas inteligentes y corridas recientes (auto-refresh 60s)"
              >
                <div className="space-y-3 text-sm">
                  <div>
                    <p className="mb-1 font-medium">Próximas ventanas</p>
                    {(dash.next_sync_windows ?? []).length === 0 ? (
                      <p className="text-muted-foreground">Sin loterías sync en ventana activa.</p>
                    ) : (
                      <ul className="space-y-1 text-xs">
                        {(dash.next_sync_windows ?? []).slice(0, 8).map((w, i) => (
                          <li key={i} className="rounded border border-border/50 px-2 py-1 font-mono">
                            src:{String(w.source_id)} · {String(w.phase)} · cada {String(w.interval_minutes)}m ·{" "}
                            {String(w.reason)}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <p className="mb-1 font-medium">Últimas sincronizaciones</p>
                    {(dash.recent_sync_runs ?? []).length === 0 ? (
                      <p className="text-muted-foreground">Sin corridas recientes.</p>
                    ) : (
                      <ul className="space-y-1 text-xs">
                        {(dash.recent_sync_runs ?? []).slice(0, 5).map((r) => (
                          <li key={String(r.id)} className="rounded border border-border/50 px-2 py-1">
                            {String(r.started_at || "").slice(0, 19)} · {String(r.status)} ·{" "}
                            {r.dry_run ? "dry-run" : "write"} · new={String(r.records_new)} ins=
                            {String(r.records_inserted)} err={String(r.errors)}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  {(dash.circuit_breakers ?? []).length > 0 && (
                    <div>
                      <p className="mb-1 font-medium">Circuit breakers</p>
                      <ul className="space-y-1 text-xs">
                        {(dash.circuit_breakers ?? []).map((c, i) => (
                          <li key={i}>
                            {String(c.scope)}: {String(c.state)} {c.reason ? `(${String(c.reason)})` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </SectionCard>

              <div className="grid gap-4 md:grid-cols-2">
                <SectionCard title="Destacadas" href="/lottery/lotteries" actionLabel="Catálogo">
                  {dash.featured.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin loterías destacadas.</p>
                  ) : (
                    <div className="grid gap-2">
                      {dash.featured.map((c) => (
                        <CatalogMiniCard key={c.id} card={c} />
                      ))}
                    </div>
                  )}
                </SectionCard>

                <SectionCard title="Favoritas" href="/lottery/favorites" actionLabel="Ver todas">
                  {dash.favorites.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Marca favoritas desde el{" "}
                      <Link href="/lottery/lotteries" className="text-primary underline">
                        catálogo
                      </Link>
                      .
                    </p>
                  ) : (
                    <div className="grid gap-2">
                      {dash.favorites.map((c) => (
                        <CatalogMiniCard key={c.id} card={c} />
                      ))}
                    </div>
                  )}
                </SectionCard>
              </div>
            </div>

            <div className="space-y-4">
              <SectionCard title="Lotería IA" description="Consultas en lenguaje natural">
                <Button asChild className="w-full">
                  <Link href="/lottery/chat">
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Abrir chat
                  </Link>
                </Button>
              </SectionCard>

              <SectionCard title="Números más frecuentes" description="Histórico global">
                {dash.top_numbers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Sin datos de frecuencia.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {dash.top_numbers.map((n) => (
                      <li key={n.number} className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1.5 font-mono font-semibold">
                          <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />
                          {n.number}
                        </span>
                        <span className="text-muted-foreground">{n.count.toLocaleString()}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </SectionCard>

              <SectionCard title="Números menos frecuentes" description="Histórico global">
                {dash.bottom_numbers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Sin datos de frecuencia.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {dash.bottom_numbers.map((n) => (
                      <li key={n.number} className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1.5 font-mono font-semibold">
                          <TrendingDown className="h-3.5 w-3.5 text-amber-600" />
                          {n.number}
                        </span>
                        <span className="text-muted-foreground">{n.count.toLocaleString()}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </SectionCard>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <SectionCard title="Resumen de sincronización" description="Estado operativo de fuentes">
              <dl className="grid gap-2 text-sm">
                {"sync_enabled_global" in syncSummary && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Sync global</dt>
                    <dd>{String(syncSummary.sync_enabled_global)}</dd>
                  </div>
                )}
                {"lotteries_sync_enabled" in syncSummary && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Loterías con sync</dt>
                    <dd>{String(syncSummary.lotteries_sync_enabled)}</dd>
                  </div>
                )}
                {"lotteries_auto_write_enabled" in syncSummary && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Auto-escritura</dt>
                    <dd>{String(syncSummary.lotteries_auto_write_enabled)}</dd>
                  </div>
                )}
              </dl>
            </SectionCard>

            <SectionCard title="Cobertura histórica" description="Rango de datos importados">
              <dl className="grid gap-2 text-sm">
                {"first_draw_date" in coverage && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Primer sorteo</dt>
                    <dd>{String(coverage.first_draw_date ?? "—")}</dd>
                  </div>
                )}
                {"last_draw_date" in coverage && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Último sorteo</dt>
                    <dd>{String(coverage.last_draw_date ?? "—")}</dd>
                  </div>
                )}
                {"lotteries_total" in coverage && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-muted-foreground">Loterías totales</dt>
                    <dd>{String(coverage.lotteries_total)}</dd>
                  </div>
                )}
              </dl>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  {dash.sources_healthy} saludables
                </span>
                <span className="inline-flex items-center gap-1">
                  <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                  {dash.sources_error} con error
                </span>
                <span className="inline-flex items-center gap-1">
                  <Activity className="h-3.5 w-3.5" />
                  <BarChart3 className="h-3.5 w-3.5" />
                  {dash.draws_historical.toLocaleString()} sorteos
                </span>
              </div>
            </SectionCard>
          </div>

          {dash.recent_queries.length > 0 && (
            <SectionCard title="Consultas recientes">
              <ul className="space-y-2 text-sm">
                {dash.recent_queries.map((q, idx) => (
                  <li key={String(q.id ?? idx)} className="rounded-lg border border-border/50 px-3 py-2">
                    <p className="font-medium">{String(q.title ?? q.query_type ?? "Consulta")}</p>
                    {q.query_type != null && (
                      <p className="text-xs text-muted-foreground">{String(q.query_type)}</p>
                    )}
                  </li>
                ))}
              </ul>
            </SectionCard>
          )}

          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-xs text-muted-foreground">
            <Dices className="mb-1 inline h-3.5 w-3.5 text-amber-700" />{" "}
            {dash.disclaimer}
          </div>
        </div>
      )}
    </AppShell>
  );
}

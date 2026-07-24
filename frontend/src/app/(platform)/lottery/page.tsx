"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  ArrowRight,
  GitCompare,
  MessageSquare,
  Network,
  RefreshCw,
  Search,
  Sparkles,
  Table2,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { lotteryDisplayName } from "@/lib/lottery-display-names";
import {
  canAccessLotteryAdmin,
  canAccessLotteryModule,
  healthStatusLabel,
  type LotteryCatalogCard,
  type LotteryDashboardV3,
} from "@/lib/lottery";

const TOOLS = [
  {
    href: "/lottery/admin/control-center/motor/historial-numero",
    label: "Historial del Número",
    desc: "Expediente de apariciones, confirmaciones y seguimiento",
    icon: Search,
  },
  {
    href: "/lottery/admin/control-center/motor/comparador",
    label: "Comparador",
    desc: "Compare candidatos, confirmadores y loterías",
    icon: GitCompare,
  },
  {
    href: "/lottery/admin/control-center/motor/table1",
    label: "Tabla 1",
    desc: "Compañeros del motor matemático",
    icon: Table2,
  },
  {
    href: "/lottery/admin/control-center/motor/table2",
    label: "Tabla 2",
    desc: "Confirmadores del motor matemático",
    icon: Table2,
  },
  {
    href: "/lottery/admin/control-center/motor/agrupaciones",
    label: "Agrupaciones",
    desc: "Grupos T1 y T2 en una sola vista",
    icon: Network,
  },
  {
    href: "/lottery/admin/control-center/motor/relaciones",
    label: "Relaciones",
    desc: "Mapa número → compañero → confirmador",
    icon: Sparkles,
  },
] as const;

function formatDate(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString("es-DO", { dateStyle: "medium" });
  } catch {
    return value;
  }
}

function expedienteHref(number: string, lotteryIds: string[]) {
  const n = String(number).replace(/\D/g, "");
  if (!n) return "/lottery/admin/control-center/motor/historial-numero";
  const params = new URLSearchParams({ number: n, auto: "1", featured: "1" });
  if (lotteryIds.length) params.set("lottery_ids", lotteryIds.join(","));
  return `/lottery/admin/control-center/motor/historial-numero?${params.toString()}`;
}

function ActiveLotteryCard({
  card,
  lotteryIds,
}: {
  card: LotteryCatalogCard;
  lotteryIds: string[];
}) {
  const title = lotteryDisplayName(card.id, card.commercial_name || card.name);
  return (
    <Card className="border-primary/20 bg-gradient-to-b from-primary/5 to-transparent">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-start justify-between gap-2 text-base">
          <span>{title}</span>
          <Badge variant={card.is_sync_enabled ? "success" : "muted"}>
            {card.is_sync_enabled ? "Sync auto" : "Análisis"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          Último sorteo: <span className="text-foreground">{formatDate(card.last_draw_date)}</span>
        </p>
        {card.last_numbers.length > 0 ? (
          <p className="font-mono text-lg tracking-wide">{card.last_numbers.join(" · ")}</p>
        ) : (
          <p className="text-muted-foreground">Sin resultado reciente</p>
        )}
        <p className="text-xs text-muted-foreground">
          {card.draw_count.toLocaleString()} sorteos · {healthStatusLabel(card.health_status)}
        </p>
        <Button asChild size="sm" className="w-full">
          <Link href={expedienteHref(card.last_numbers[0] || "50", lotteryIds)}>
            Abrir expediente
            <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export default function LotteryPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dash, setDash] = useState<LotteryDashboardV3 | null>(null);
  const [quickNumber, setQuickNumber] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError("Sin permiso para Lottery IA Control Center");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const access = await apiClient.getPlatformAccess().catch(() => null);
      setIsAdmin(canAccessLotteryAdmin(getUserRole(), access?.permissions ?? []));
      const data = await apiClient.getLotteryDashboardV3();
      setDash(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar Lottery IA Control Center");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(t);
  }, [load]);

  const seven = useMemo(() => dash?.featured ?? [], [dash]);
  const lotteryIds = useMemo(() => seven.map((c) => c.id), [seven]);

  const openQuick = () => {
    const n = quickNumber.replace(/\D/g, "");
    if (!n) return;
    router.push(expedienteHref(n, lotteryIds));
  };

  return (
    <AppShell
      title="Lottery IA Control Center"
      description="Una sola plataforma de inteligencia sobre las siete loterías activas."
    >
      <div className="mb-6 rounded-2xl border border-primary/25 bg-gradient-to-br from-primary/10 via-background to-background p-5 md:p-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              JAIOS · Lottery IA
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight md:text-3xl">
              Lottery IA Control Center
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground md:text-base">
              Historial, comparador, tablas y relaciones en un solo menú. Análisis exclusivo sobre
              las siete loterías activas; el inventario histórico permanece en archivo.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}

      {dash ? (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Loterías activas" value={String(dash.lotteries_active)} tone="primary" />
          <MetricCard label="Visibles" value={String(dash.lotteries_visible)} tone="primary" />
          <MetricCard label="Esperados hoy" value={String(dash.expected_today ?? 0)} tone="muted" />
          <MetricCard label="Pendientes visibles" value={String(dash.pending_visible ?? 0)} tone="muted" />
        </div>
      ) : null}

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Herramientas de inteligencia</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {TOOLS.map((tool) => {
            const Icon = tool.icon;
            return (
              <Link
                key={tool.href}
                href={tool.href}
                className="rounded-xl border bg-card p-4 transition hover:border-primary/40 hover:bg-muted/40"
              >
                <div className="mb-2 flex items-center gap-2 font-medium">
                  <Icon className="h-4 w-4 text-primary" />
                  {tool.label}
                </div>
                <p className="text-sm text-muted-foreground">{tool.desc}</p>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="mb-8">
        <div className="mb-3 flex items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">Las siete loterías activas</h2>
            <p className="text-sm text-muted-foreground">Universo exclusivo de análisis.</p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/lottery/lotteries">Ver catálogo</Link>
          </Button>
        </div>
        {loading && !dash ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {seven.map((card) => (
              <ActiveLotteryCard key={card.id} card={card} lotteryIds={lotteryIds} />
            ))}
          </div>
        )}
        {!loading && seven.length !== 7 ? (
          <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
            Se esperaban 7 loterías destacadas; hay {seven.length}. Revise Administración → Catálogo
            admin.
          </p>
        ) : null}
      </section>

      <section className="mb-8">
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4" />
              Análisis rápido de número
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="quick-n">
                Número (1–100)
              </label>
              <Input
                id="quick-n"
                inputMode="numeric"
                placeholder="ej. 50"
                value={quickNumber}
                onChange={(e) => setQuickNumber(e.target.value)}
                className="w-32"
              />
            </div>
            <Button onClick={openQuick}>Abrir expediente</Button>
            <Button asChild variant="outline">
              <Link href="/lottery/chat">
                <MessageSquare className="mr-1.5 h-4 w-4" />
                Copiloto
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Resultados recientes</h2>
        <div className="grid gap-2">
          {(dash?.latest_results || []).slice(0, 7).map((row, idx) => (
            <div
              key={`${row.slug}-${idx}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
            >
              <div>
                <span className="font-medium">
                  {lotteryDisplayName(undefined, row.lottery)}
                </span>
                <span className="ml-2 text-muted-foreground">{row.date || "—"}</span>
              </div>
              <span className="font-mono">{(row.numbers || []).join(" · ") || "—"}</span>
            </div>
          ))}
          {!loading && !(dash?.latest_results || []).length ? (
            <p className="text-sm text-muted-foreground">Sin resultados recientes de las siete activas.</p>
          ) : null}
        </div>
      </section>

      {isAdmin ? (
        <section className="rounded-xl border border-dashed p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="flex items-center gap-2 text-sm font-medium">
                <Activity className="h-4 w-4" />
                Administración
              </p>
              <p className="text-xs text-muted-foreground">
                Sync, archivo histórico y Prompt Studio (fuera de la experiencia ordinaria).
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button asChild size="sm" variant="outline">
                <Link href="/lottery/admin/sync">Sync</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/lottery/admin/lotteries">Catálogo admin</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/lottery/admin/lotteries/archivo-historico">Archivo</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/lottery/admin/control-center/prompt-studio">Prompt Studio</Link>
              </Button>
            </div>
          </div>
        </section>
      ) : null}
    </AppShell>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Dices, MessageSquare, Search, Star } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  canAccessLotteryModule,
  DISCLAIMER,
  type LotteryDashboard,
  type LotteryPreferences,
} from "@/lib/lottery";

export default function LotteryPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dash, setDash] = useState<LotteryDashboard | null>(null);
  const [prefs, setPrefs] = useState<LotteryPreferences | null>(null);
  const [quickLottery, setQuickLottery] = useState("Real");
  const [quickDate, setQuickDate] = useState("2022-03-15");
  const [showOnboarding, setShowOnboarding] = useState(false);

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
    try {
      const [d, p] = await Promise.all([
        apiClient.getLotteryDashboard(),
        apiClient.getLotteryPreferences().catch(() => null),
      ]);
      setDash(d);
      if (p) {
        setPrefs(p);
        setShowOnboarding(!p.onboarding_completed && !p.disclaimer_acknowledged);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const finishOnboarding = async () => {
    await apiClient.patchLotteryPreferences({
      onboarding_completed: true,
      disclaimer_acknowledged: true,
    });
    setShowOnboarding(false);
  };

  return (
    <AppShell title="Resultados de Loterías" description="Dashboard histórico y Lotería IA">
      {loading && <p className="text-sm text-muted-foreground" role="status">Cargando…</p>}
      {error && (
        <Card className="border-destructive/40">
          <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {showOnboarding && (
        <Card className="mb-4 border-primary/30" role="dialog" aria-label="Onboarding Lotería IA">
          <CardHeader>
            <CardTitle className="text-base">Bienvenido a Lotería IA</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <ol className="list-decimal space-y-1 pl-5">
              <li>Consulta resultados históricos verificables.</li>
              <li>
                Marca favoritas en el{" "}
                <Link href="/lottery/lotteries" className="text-primary underline">
                  catálogo
                </Link>
                .
              </li>
              <li>Distingue <strong>días calendario</strong> de <strong>sorteos</strong> siguientes.</li>
              <li>Las estadísticas muestran frecuencia histórica, no predicciones.</li>
              <li>No se realizan predicciones ni recomendaciones de apuestas.</li>
            </ol>
            <p>{DISCLAIMER}</p>
            <div className="flex gap-2 pt-2">
              <Button onClick={() => void finishOnboarding()}>Entendido</Button>
              <Button variant="outline" onClick={() => void finishOnboarding()}>
                Omitir
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {dash && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Cobertura histórica</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <p>
                  <strong>{dash.lotteries_count}</strong> loterías · <strong>{dash.draws_count.toLocaleString()}</strong>{" "}
                  sorteos
                </p>
                <p className="text-muted-foreground">
                  {dash.first_draw_date || "—"} → {dash.last_draw_date || "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Estado del módulo</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <p>Módulo: {dash.module_enabled ? "activo" : "deshabilitado"}</p>
                <p>Sync: {dash.sync_enabled ? "activo" : "apagado"}</p>
                {dash.note && <p className="text-muted-foreground">{dash.note}</p>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <MessageSquare className="h-4 w-4" /> Lotería IA
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button asChild className="w-full">
                  <Link href="/lottery/chat">Abrir chat</Link>
                </Button>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Search className="h-4 w-4" /> Buscador rápido
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Input
                aria-label="Lotería"
                value={quickLottery}
                onChange={(e) => setQuickLottery(e.target.value)}
                className="max-w-[160px]"
                placeholder="Lotería"
              />
              <Input
                aria-label="Fecha"
                type="date"
                value={quickDate}
                onChange={(e) => setQuickDate(e.target.value)}
                className="max-w-[160px]"
              />
              <Button asChild>
                <Link href={`/lottery/search?lottery=${encodeURIComponent(quickLottery)}&date=${quickDate}`}>
                  Consultar
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/lottery/lotteries">Catálogo</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/lottery/compare">Comparar</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/lottery/statistics">Estadísticas</Link>
              </Button>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Star className="h-4 w-4" /> Favoritas
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {dash.favorites.length === 0 && (
                  <p className="text-muted-foreground">Sin favoritos. Márcalos desde el catálogo.</p>
                )}
                {dash.favorites.map((f) => (
                  <Link
                    key={f.id}
                    className="flex items-center gap-2 text-primary hover:underline"
                    href={`/lottery/lotteries/${f.slug}`}
                  >
                    <Dices className="h-3.5 w-3.5" />
                    {f.name}
                  </Link>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Consultas recientes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {dash.recent_queries.length === 0 && (
                  <p className="text-muted-foreground">Aún no hay consultas recientes.</p>
                )}
                {dash.recent_queries.map((q) => (
                  <div key={q.id}>
                    <p className="font-medium">{q.title}</p>
                    <p className="text-xs text-muted-foreground">{q.query_type}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {dash.saved_queries.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Consultas guardadas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                {dash.saved_queries.map((s) => (
                  <p key={s.id}>
                    {s.name}
                    {s.query_type ? ` · ${s.query_type}` : ""}
                  </p>
                ))}
              </CardContent>
            </Card>
          )}

          <p className="text-xs text-muted-foreground">{dash.disclaimer || DISCLAIMER}</p>
          {prefs?.preferred_export_format && (
            <p className="text-[10px] text-muted-foreground">
              Formato de exportación preferido: {prefs.preferred_export_format}
            </p>
          )}
        </div>
      )}
    </AppShell>
  );
}

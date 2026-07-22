"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Star } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  canAccessLotteryModule,
  DISCLAIMER,
  type LotteryDetail,
} from "@/lib/lottery";

export default function LotteryDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [data, setData] = useState<LotteryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);

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
      setData(await apiClient.getLotteryDetail(params.slug));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar");
    }
  }, [params.slug, router]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleFav = async () => {
    if (!data) return;
    if (data.is_favorite) {
      await apiClient.removeLotteryFavorite(data.lottery.id);
    } else {
      await apiClient.addLotteryFavorite(data.lottery.id);
    }
    await load();
  };

  const exportCsv = async () => {
    if (!data) return;
    setExportMsg(null);
    try {
      const last = data.lottery.last_draw_date || "2022-03-15";
      const exp = await apiClient.createLotteryExport({
        query_type: "by_date",
        query_parameters: { lottery: data.lottery.name, date: last },
        format: "csv",
        title: `${data.lottery.slug}-${last}`,
      });
      setExportMsg(`Export listo: ${exp.filename} (${exp.size} bytes)`);
    } catch (err) {
      setExportMsg(err instanceof ApiError ? err.message : "Export falló");
    }
  };

  return (
    <AppShell title={data?.lottery.name || "Detalle"} description="Cobertura y últimos sorteos">
      <div className="mb-3 flex flex-wrap gap-2">
        <Button asChild variant="outline">
          <Link href="/lottery/lotteries">Catálogo</Link>
        </Button>
        {data && (
          <>
            <Button variant="outline" onClick={() => void toggleFav()} aria-label="Favorito">
              <Star className={`mr-1 h-4 w-4 ${data.is_favorite ? "fill-amber-500 text-amber-500" : ""}`} />
              Favorito
            </Button>
            <Button asChild>
              <Link href={`/lottery/search?lottery=${encodeURIComponent(data.lottery.name)}`}>
                Consultar
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/lottery/chat">Chat</Link>
            </Button>
            <Button variant="secondary" onClick={() => void exportCsv()}>
              Exportar CSV
            </Button>
            <Button asChild variant="outline">
              <Link href={`/lottery/print?lottery=${encodeURIComponent(data.lottery.name)}&date=${data.lottery.last_draw_date || ""}`}>
                Imprimir
              </Link>
            </Button>
          </>
        )}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {exportMsg && <p className="mb-2 text-sm text-muted-foreground">{exportMsg}</p>}
      {data && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{data.lottery.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p>
                Cobertura: {data.lottery.first_draw_date || "—"} → {data.lottery.last_draw_date || "—"}
              </p>
              <p>Sorteos: {data.lottery.draw_count.toLocaleString()}</p>
              {data.aliases.length > 0 && (
                <p className="text-muted-foreground">Aliases: {data.aliases.join(", ")}</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Últimos resultados</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.recent_draws.map((d) => (
                <div key={d.id} className="rounded border p-2">
                  <p className="text-xs text-muted-foreground">
                    {d.draw_date}
                    {d.source_reference ? ` · ref ${d.source_reference}` : ""}
                  </p>
                  <p className="font-mono text-xl tracking-wide">
                    {d.numbers.map((n) => n.number_raw || n.number_value).join("  ")}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
          <p className="text-xs text-muted-foreground">{DISCLAIMER}</p>
        </div>
      )}
    </AppShell>
  );
}

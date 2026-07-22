"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { LotteryExportActions } from "@/components/lottery/lottery-export-actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  canAccessLotteryModule,
  DISCLAIMER,
  type CalendarWindowResponse,
  type DateQueryResponse,
  type DrawResult,
  type DrawsWindowResponse,
  type LotteryLottery,
} from "@/lib/lottery";

function DrawCard({ draw }: { draw: DrawResult }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {draw.draw_date}
          {draw.draw_time ? ` · ${draw.draw_time}` : ""} · {draw.game_name}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3">
        {draw.numbers.map((n) => (
          <div key={`${n.position}-${n.number_type}`} className="text-center">
            <p className="text-[10px] uppercase text-muted-foreground">{n.position_label}</p>
            <p className="font-mono text-2xl font-semibold tracking-tight">{n.number_value}</p>
            {n.number_type !== "principal" && (
              <p className="text-[10px] text-muted-foreground">{n.number_type}</p>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function LotterySearchPage() {
  const router = useRouter();
  const [lotteries, setLotteries] = useState<LotteryLottery[]>([]);
  const [lottery, setLottery] = useState("Real");
  const [date, setDate] = useState("2022-03-15");
  const [days, setDays] = useState(7);
  const [count, setCount] = useState(7);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [byDate, setByDate] = useState<DateQueryResponse | null>(null);
  const [followingDays, setFollowingDays] = useState<CalendarWindowResponse | null>(null);
  const [followingDraws, setFollowingDraws] = useState<DrawsWindowResponse | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) return;
    apiClient
      .getLotteryLotteries(100, 0)
      .then((r) => setLotteries(r.items.filter((x) => !x.is_aggregate)))
      .catch(() => undefined);
  }, [router]);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [d, fd, fdr] = await Promise.all([
        apiClient.getLotteryByDate({ lottery, date }),
        apiClient.getLotteryFollowingDays({ lottery, date, days }),
        apiClient.getLotteryFollowingDraws({ lottery, date, count }),
      ]);
      setByDate(d);
      setFollowingDays(fd);
      setFollowingDraws(fdr);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al consultar");
    } finally {
      setLoading(false);
    }
  }, [lottery, date, days, count]);

  return (
    <AppShell title="Consulta histórica" description="Resultados de Loterías — datos reales">
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Inicio
        </Link>
        <Link href="/lottery/compare" className="text-primary underline">
          Comparar
        </Link>
        <Link href="/lottery/statistics" className="text-primary underline">
          Estadísticas
        </Link>
      </div>

      <Card className="mb-4">
        <CardContent className="grid gap-3 pt-6 md:grid-cols-4">
          <label className="text-sm">
            Lotería
            <select
              className="mt-1 w-full rounded-md border bg-background px-2 py-2"
              value={lottery}
              onChange={(e) => setLottery(e.target.value)}
            >
              <option value="Real">Real</option>
              <option value="Loteka">Loteka</option>
              <option value="Leidsa">Leidsa</option>
              <option value="Nacional Noche">Nacional Noche</option>
              <option value="New York Día">New York Día</option>
              <option value="New York Noche">New York Noche</option>
              {lotteries.slice(0, 40).map((l) => (
                <option key={l.id} value={l.name}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Fecha
            <Input type="date" className="mt-1" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label className="text-sm">
            Días calendario
            <Input
              type="number"
              className="mt-1"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            />
          </label>
          <label className="text-sm">
            Sorteos siguientes
            <Input
              type="number"
              className="mt-1"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </label>
        </CardContent>
        <CardContent className="space-y-3">
          <Button onClick={() => void run()} disabled={loading}>
            {loading ? "Consultando…" : "Consultar"}
          </Button>
          <LotteryExportActions
            queryType="by_date"
            queryParameters={{ lottery, date }}
            title={`resultados-${lottery}-${date}`}
            printHref={`/lottery/print?lottery=${encodeURIComponent(lottery)}&date=${date}`}
            disabled={loading}
          />
          <p className="text-xs text-muted-foreground">
            Compartir requiere permiso <code>lottery.share</code> (no incluido en Lottery Client por
            defecto). Usa la API <code>POST /lottery/shares</code> o el admin interno.
          </p>
        </CardContent>
      </Card>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {byDate && (
        <section className="mb-6 space-y-3">
          <h2 className="text-lg font-semibold">
            Fecha exacta — {byDate.meta.resolved_lottery?.name} · {byDate.date}
          </h2>
          {byDate.total === 0 ? (
            <p className="text-sm text-muted-foreground">Sin sorteos en esa fecha.</p>
          ) : (
            byDate.draws.map((d) => <DrawCard key={d.id} draw={d} />)
          )}
        </section>
      )}

      {followingDays && (
        <section className="mb-6 space-y-3">
          <h2 className="text-lg font-semibold">
            {followingDays.days_requested} días calendario ({followingDays.calendar_from} →{" "}
            {followingDays.calendar_to})
          </h2>
          <p className="text-xs text-muted-foreground">
            Con sorteo: {followingDays.days_with_draws.length} · Sin sorteo:{" "}
            {followingDays.days_without_draws.length} · Total draws: {followingDays.total_draws}
          </p>
          {followingDays.draws.map((d) => (
            <DrawCard key={d.id} draw={d} />
          ))}
        </section>
      )}

      {followingDraws && (
        <section className="mb-6 space-y-3">
          <h2 className="text-lg font-semibold">
            {followingDraws.count_requested} sorteos siguientes (no son días calendario)
          </h2>
          {followingDraws.draws.map((d) => (
            <DrawCard key={d.id} draw={d} />
          ))}
        </section>
      )}

      <p className="text-xs text-muted-foreground">{DISCLAIMER}</p>
    </AppShell>
  );
}

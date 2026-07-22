"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { LotteryExportActions } from "@/components/lottery/lottery-export-actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { DISCLAIMER, type FrequencyResponse } from "@/lib/lottery";

export default function LotteryStatisticsPage() {
  const router = useRouter();
  const [lottery, setLottery] = useState("Real");
  const [from, setFrom] = useState("2022-01-01");
  const [to, setTo] = useState("2022-12-31");
  const [result, setResult] = useState<FrequencyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryFrequencies({
        lottery,
        from,
        to,
        limit: 20,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al consultar estadísticas");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="Estadísticas históricas" description="Frecuencias — sin predicción">
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <Link href="/lottery/search" className="text-primary underline">
          Consulta
        </Link>
        <Link href="/lottery/compare" className="text-primary underline">
          Comparar
        </Link>
      </div>

      <Card className="mb-4">
        <CardContent className="grid gap-3 pt-6 md:grid-cols-4">
          <label className="text-sm">
            Lotería
            <Input className="mt-1" value={lottery} onChange={(e) => setLottery(e.target.value)} placeholder="Lotería" />
          </label>
          <label className="text-sm">
            Desde
            <Input className="mt-1" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="text-sm">
            Hasta
            <Input className="mt-1" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
          <Button onClick={() => void run()} disabled={loading}>
            {loading ? "Calculando…" : "Frecuencias"}
          </Button>
        </CardContent>
        <CardContent>
          <LotteryExportActions
            queryType="frequencies"
            queryParameters={{ lottery, from, to, limit: 20 }}
            title={`frecuencias-${lottery}-${from}-a-${to}`}
            printHref={`/lottery/print?lottery=${encodeURIComponent(lottery)}&from=${from}&to=${to}`}
            disabled={loading}
          />
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Observaciones: {result.total_observations} · {result.from_date} → {result.to_date}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2">Número</th>
                  <th>Cantidad</th>
                  <th>%</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.number} className="border-b border-border/50">
                    <td className="py-2 font-mono text-lg">{item.number}</td>
                    <td>{item.count}</td>
                    <td>{item.percentage.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <p className="mt-4 text-xs text-muted-foreground">{DISCLAIMER}</p>
    </AppShell>
  );
}

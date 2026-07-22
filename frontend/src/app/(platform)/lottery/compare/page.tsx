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
import { DISCLAIMER, type ComparisonResponse } from "@/lib/lottery";

const OPTIONS = [
  "Real",
  "Loteka",
  "Leidsa",
  "Nacional Noche",
  "New York Día",
  "New York Noche",
];

export default function LotteryComparePage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>(["Real", "Nacional Noche"]);
  const [from, setFrom] = useState("2022-03-01");
  const [to, setTo] = useState("2022-03-31");
  const [mode, setMode] = useState("repeated_numbers");
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function toggle(name: string) {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name],
    );
  }

  async function run() {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.compareLotteries({
        lotteries: selected,
        from,
        to,
        mode,
        limit: 30,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al comparar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="Comparar loterías" description="Coincidencias e intersecciones históricas">
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <Link href="/lottery/search" className="text-primary underline">
          Consulta
        </Link>
        <Link href="/lottery/statistics" className="text-primary underline">
          Estadísticas
        </Link>
      </div>

      <Card className="mb-4">
        <CardContent className="space-y-4 pt-6">
          <div className="flex flex-wrap gap-2">
            {OPTIONS.map((name) => (
              <button
                key={name}
                type="button"
                onClick={() => toggle(name)}
                className={`rounded-full border px-3 py-1 text-sm ${
                  selected.includes(name) ? "bg-primary text-primary-foreground" : ""
                }`}
              >
                {name}
              </button>
            ))}
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="text-sm">
              Desde
              <Input type="date" className="mt-1" value={from} onChange={(e) => setFrom(e.target.value)} />
            </label>
            <label className="text-sm">
              Hasta
              <Input type="date" className="mt-1" value={to} onChange={(e) => setTo(e.target.value)} />
            </label>
            <label className="text-sm">
              Modo
              <select
              className="mt-1 w-full rounded-md border bg-background px-2 py-2 text-sm"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              aria-label="Modo de comparación"
            >
              <option value="repeated_numbers">Números repetidos</option>
              <option value="same_date">Mismo día</option>
              <option value="intersections">Intersección</option>
              <option value="frequencies">Frecuencias</option>
              <option value="timeline">Línea de tiempo</option>
            </select>
            </label>
          </div>
          <Button onClick={() => void run()} disabled={loading || selected.length < 2}>
            {loading ? "Comparando…" : "Comparar"}
          </Button>
          <LotteryExportActions
            queryType="compare"
            queryParameters={{ lotteries: selected, from, to, mode, limit: 30 }}
            title={`comparacion-${selected.join("-")}-${from}-a-${to}`}
            printHref={`/lottery/print?mode=compare&from=${from}&to=${to}`}
            disabled={loading || selected.length < 2}
          />
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {result.mode} · {result.from_date} → {result.to_date}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre tabIndex={0} className="max-h-[480px] overflow-auto rounded-md bg-muted p-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <p className="mt-4 text-xs text-muted-foreground">{DISCLAIMER}</p>
    </AppShell>
  );
}

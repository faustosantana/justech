"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type ObsRow = { lottery_name: string; number: string };

const PRESETS: Array<{
  label: string;
  date: string;
  rows: ObsRow[];
  manual: string;
}> = [
  {
    label: "Caso 1 — 21-Jun-2026",
    date: "2026-06-21",
    rows: [
      { lottery_name: "Gana Mas", number: "41" },
      { lottery_name: "Loteria Nacional", number: "41" },
      { lottery_name: "Quiniela Leidsa", number: "70" },
    ],
    manual: "29",
  },
  {
    label: "Caso 2 — 21-Jun-2026",
    date: "2026-06-21",
    rows: [
      { lottery_name: "Loteria Nacional", number: "41" },
      { lottery_name: "Quiniela Loteka", number: "62" },
    ],
    manual: "75",
  },
  {
    label: "Caso 3 — 21-Jun-2026",
    date: "2026-06-21",
    rows: [
      { lottery_name: "Quiniela Real", number: "49" },
      { lottery_name: "Loteria Nacional", number: "44" },
      { lottery_name: "Quiniela Leidsa", number: "70" },
    ],
    manual: "35",
  },
  {
    label: "Caso 4 — 23-Jun-2026",
    date: "2026-06-23",
    rows: [
      { lottery_name: "Loteria Nacional", number: "35" },
      { lottery_name: "Quiniela Loteka", number: "14" },
    ],
    manual: "54",
  },
  {
    label: "Caso 5 — 22-Jul-2026",
    date: "2026-07-22",
    rows: [
      { lottery_name: "New York 2:30", number: "35" },
      { lottery_name: "Loteria Nacional", number: "14" },
    ],
    manual: "54",
  },
];

export default function MotorValidationLabPage() {
  const [date, setDate] = useState("2026-06-23");
  const [manual, setManual] = useState("54");
  const [rows, setRows] = useState<ObsRow[]>([
    { lottery_name: "Loteria Nacional", number: "35" },
    { lottery_name: "Quiniela Loteka", number: "14" },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const coincidence = useMemo(() => {
    const c = result?.coincidence;
    return typeof c === "string" ? c : null;
  }, [result]);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const observations = rows
        .map((r) => ({
          lottery_name: r.lottery_name.trim() || undefined,
          number: Number(r.number),
        }))
        .filter((r) => Number.isFinite(r.number) && r.number >= 1 && r.number <= 100);
      const body = {
        observations,
        manual_fuerte: manual ? Number(manual) : null,
        date: date || null,
      };
      const res = await apiClient.postLotteryNumericRelationsValidationLab(body);
      setResult(res);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "No se pudo ejecutar el laboratorio");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Motor Validation Lab</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Modo auditoría: reconstruye Tabla 1, Tabla 2, compañeros, vecinos, cruces e
          intersecciones. No modifica el Motor NR ni crea reglas nuevas.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Casos manuales (presets)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <Button
              key={p.label}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setDate(p.date);
                setRows(p.rows);
                setManual(p.manual);
                setResult(null);
              }}
            >
              {p.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Entrada</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              Fecha
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="mt-1" />
            </label>
            <label className="text-sm">
              Fuerte manual (opcional)
              <Input value={manual} onChange={(e) => setManual(e.target.value)} className="mt-1" />
            </label>
          </div>
          {rows.map((row, idx) => (
            <div key={idx} className="grid gap-2 sm:grid-cols-2">
              <Input
                placeholder="Lotería"
                value={row.lottery_name}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], lottery_name: e.target.value };
                  setRows(next);
                }}
              />
              <Input
                placeholder="Número observado"
                value={row.number}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], number: e.target.value };
                  setRows(next);
                }}
              />
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setRows([...rows, { lottery_name: "", number: "" }])}>
              Añadir observación
            </Button>
            <Button type="button" onClick={() => void run()} disabled={busy}>
              {busy ? "Calculando…" : "Reconstruir análisis"}
            </Button>
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {result ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Resultado — Coinciden: {coincidence ?? "—"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded border p-3">
                <p className="text-xs text-muted-foreground">Fuerte manual</p>
                <p className="text-lg font-semibold">{String(result.manual_fuerte ?? "—")}</p>
              </div>
              <div className="rounded border p-3">
                <p className="text-xs text-muted-foreground">Resultado forma-motor (F)</p>
                <p className="text-lg font-semibold">{JSON.stringify(result.motor_shaped_result)}</p>
              </div>
              <div className="rounded border p-3">
                <p className="text-xs text-muted-foreground">Metodología</p>
                <p className="font-medium">{String(result.methodology_version)}</p>
              </div>
            </div>

            <div>
              <h3 className="mb-2 font-medium">Ranking matemático (evidencia)</h3>
              <pre className="overflow-auto rounded bg-muted/40 p-3 text-xs">
                {JSON.stringify(result.mathematical_ranking, null, 2)}
              </pre>
            </div>
            <div>
              <h3 className="mb-2 font-medium">Tabla 1 / Tabla 2 por número</h3>
              <pre className="overflow-auto rounded bg-muted/40 p-3 text-xs">
                {JSON.stringify(result.tables_per_number, null, 2)}
              </pre>
            </div>
            <div>
              <h3 className="mb-2 font-medium">Cruces e intersecciones</h3>
              <pre className="overflow-auto rounded bg-muted/40 p-3 text-xs">
                {JSON.stringify(result.crosses_and_intersections, null, 2)}
              </pre>
            </div>
            {result.explanation ? (
              <div>
                <h3 className="mb-2 font-medium">Explicación</h3>
                <pre className="overflow-auto rounded bg-muted/40 p-3 text-xs">
                  {JSON.stringify(result.explanation, null, 2)}
                </pre>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

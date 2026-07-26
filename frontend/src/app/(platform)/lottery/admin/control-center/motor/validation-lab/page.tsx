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
    label: "Caso 2 — 21-Jun-2026 (T2 directa)",
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

  const manualStatus = useMemo(() => {
    const m = result?.manual_status;
    return m && typeof m === "object" ? (m as Record<string, unknown>) : null;
  }, [result]);

  const fuerteOficial = useMemo(() => {
    const f = result?.fuerte_oficial;
    return f && typeof f === "object" ? (f as Record<string, unknown>) : null;
  }, [result]);

  const senalT2 = useMemo(() => {
    const s = result?.senal_t2_directa;
    return s && typeof s === "object" ? (s as Record<string, unknown>) : null;
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
      const res = await apiClient.postLotteryNumericRelationsValidationLab({
        observations,
        manual_fuerte: manual ? Number(manual) : null,
        date: date || null,
      });
      setResult(res);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "No se pudo ejecutar el laboratorio");
    } finally {
      setBusy(false);
    }
  };

  const classification = String(manualStatus?.classification ?? "—");
  const isOfficial = classification === "FUERTE_OFICIAL";
  const isT2 = classification === "DIRECT_T2_NEIGHBOR_SIGNAL";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Motor Validation Lab</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Auditoría explicativa. Distingue <strong>Fuerte oficial</strong> (T1×T2) de{" "}
          <strong>Señal T2 directa</strong> (no oficial). No modifica el Motor NR.
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
              Resultado manual
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
        <>
          <div className="grid gap-3 md:grid-cols-2">
            <Card className={isOfficial ? "border-emerald-600/50" : ""}>
              <CardHeader>
                <CardTitle className="text-base">Fuerte oficial</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-xs text-muted-foreground">
                  Geometría: Tabla 1 candidato × Tabla 2 confirmador
                </p>
                <p>
                  Candidatos fortalecidos:{" "}
                  <span className="font-semibold">{JSON.stringify(fuerteOficial?.candidates ?? [])}</span>
                </p>
                <p>
                  Resultado motor:{" "}
                  <span className="font-semibold">{JSON.stringify(fuerteOficial?.result ?? "—")}</span>
                </p>
                {isOfficial ? (
                  <p className="rounded bg-emerald-500/10 px-2 py-1 text-emerald-800 dark:text-emerald-200">
                    El resultado manual coincide con un fuerte oficial.
                  </p>
                ) : (
                  <p className="text-muted-foreground">
                    Sin candidato fortalecido igual al manual (o vacío).
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className={isT2 ? "border-amber-600/50" : ""}>
              <CardHeader>
                <CardTitle className="text-base">Señal T2 directa</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-xs text-muted-foreground">
                  Clasificación: DIRECT_T2_NEIGHBOR_SIGNAL — no es fuerte oficial
                </p>
                <p>
                  Vecinos T2 de observados:{" "}
                  <span className="font-semibold">{JSON.stringify(senalT2?.all_direct_neighbors ?? [])}</span>
                </p>
                <p>
                  Solo secundarios (no oficiales):{" "}
                  <span className="font-semibold">{JSON.stringify(senalT2?.secondary_only_not_official ?? [])}</span>
                </p>
                {isT2 ? (
                  <p className="rounded bg-amber-500/10 px-2 py-1 text-amber-900 dark:text-amber-100">
                    Estado: Señal T2 directa, no fuerte oficial. Relación:{" "}
                    {JSON.stringify(manualStatus?.direct_t2_edges_for_manual)}
                  </p>
                ) : (
                  <p className="text-muted-foreground">El manual no está clasificado solo como señal T2.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Comparación — {String(manualStatus?.label_es ?? result.coincidence ?? "—")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded border p-3">
                  <p className="text-xs text-muted-foreground">Resultado manual</p>
                  <p className="text-lg font-semibold">{String(result.manual_fuerte ?? "—")}</p>
                </div>
                <div className="rounded border p-3">
                  <p className="text-xs text-muted-foreground">Clasificación</p>
                  <p className="font-semibold">{classification}</p>
                </div>
                <div className="rounded border p-3">
                  <p className="text-xs text-muted-foreground">Metodología</p>
                  <p className="font-medium">{String(result.methodology_version)}</p>
                </div>
              </div>
              {result.explanation ? (
                <pre className="overflow-auto rounded bg-muted/40 p-3 text-xs">
                  {JSON.stringify(result.explanation, null, 2)}
                </pre>
              ) : null}
              <details>
                <summary className="cursor-pointer text-sm font-medium">Detalle técnico completo</summary>
                <pre className="mt-2 overflow-auto rounded bg-muted/40 p-3 text-xs">
                  {JSON.stringify(
                    {
                      tables_per_number: result.tables_per_number,
                      crosses_and_intersections: result.crosses_and_intersections,
                      mathematical_ranking: result.mathematical_ranking,
                      senal_t2_directa: result.senal_t2_directa,
                      fuerte_oficial: result.fuerte_oficial,
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type CaseRow = Record<string, unknown>;

export default function MotorHistoricalAuditPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [minCases] = useState(10);
  const [verdictFilter, setVerdictFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditId, setAuditId] = useState<string | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [selected, setSelected] = useState<CaseRow | null>(null);
  const [fourYear, setFourYear] = useState<Record<string, unknown> | null>(null);

  const metrics = useMemo(() => {
    const pop = (summary?.population_metrics as Record<string, unknown>) || {};
    const sample = (summary?.sample_metrics as Record<string, unknown>) || {};
    const base = (summary?.random_baselines as Record<string, unknown>) || {};
    const off = (base.official_t1_x_t2 as Record<string, unknown>) || {};
    return { pop, sample, base, off };
  }, [summary]);

  const run = async (forceRerun = false) => {
    setBusy(true);
    setError(null);
    setSelected(null);
    try {
      const res = await apiClient.postLotteryNumericRelationsHistoricalAudit({
        use_precomputed: !forceRerun,
        force_rerun: forceRerun,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        min_cases: minCases,
        include_hits_and_fails: true,
      });
      const id = String(res.audit_id);
      setAuditId(id);
      setSummary((res.summary as Record<string, unknown>) || null);
      const casesRes = await apiClient.getLotteryNumericRelationsHistoricalAuditCases(id, {
        page: 1,
        page_size: 50,
        verdict: verdictFilter || undefined,
      });
      setCases((casesRes.cases as CaseRow[]) || []);
    } catch (err) {
      setSummary(null);
      setCases([]);
      setError(err instanceof ApiError ? err.message : "No se pudo ejecutar la auditoría");
    } finally {
      setBusy(false);
    }
  };

  const loadFourYear = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryNumericRelationsFourYearAuditSummary();
      setFourYear((res.summary as Record<string, unknown>) || res);
    } catch (err) {
      setFourYear(null);
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la auditoría de 4 años");
    } finally {
      setBusy(false);
    }
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ auditId, summary, cases }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `historical-audit-${auditId || "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const nd = metrics.off;
  const lift = metrics.base.lift_official_vs_random_same_k;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Historical Manual Logic Audit</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Valida la lógica manual T1×T2 sobre el histórico FEATURED_SEVEN. Solo lectura. No es garantía
          predictiva. No modifica el motor ni las tablas.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parámetros</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="text-sm">
              Desde
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="mt-1" />
            </label>
            <label className="text-sm">
              Hasta
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="mt-1" />
            </label>
            <label className="text-sm">
              Filtro veredicto
              <Input
                placeholder="ACIERTO_EXACTO / FALLO / …"
                value={verdictFilter}
                onChange={(e) => setVerdictFilter(e.target.value)}
                className="mt-1"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void run(false)} disabled={busy}>
              {busy ? "Ejecutando…" : "Cargar auditoría (evidencia)"}
            </Button>
            <Button type="button" variant="outline" onClick={() => void run(true)} disabled={busy}>
              Re-ejecutar en DEV
            </Button>
            <Button type="button" variant="outline" onClick={exportJson} disabled={!cases.length}>
              Exportar JSON
            </Button>
            <Button type="button" variant="secondary" onClick={() => void loadFourYear()} disabled={busy}>
              Cargar auditoría 4 años
            </Button>
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {auditId ? (
            <p className="text-xs text-muted-foreground">
              audit_id / trace_id: {auditId}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {fourYear ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Auditoría 4 años (no predictiva)</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <div>
              Rango: {String((fourYear.actual_range as Record<string, unknown> | undefined)?.from ?? "—")} →{" "}
              {String((fourYear.actual_range as Record<string, unknown> | undefined)?.to ?? "—")}
            </div>
            <div>Fechas: {String(fourYear.dates_analyzed_ge2_obs ?? "—")}</div>
            <div>
              Veredicto estadístico:{" "}
              {String((fourYear.verdicts as Record<string, unknown> | undefined)?.veredicto_estadistico ?? "—")}
            </div>
            <div>
              Lift same-k:{" "}
              {String(
                (
                  ((fourYear.aggregates as Record<string, unknown> | undefined)?.baselines_w3 as
                    | Record<string, unknown>
                    | undefined) || {}
                ).lift_official_vs_random_same_k ?? "—",
              )}
            </div>
            <div className="sm:col-span-2 text-muted-foreground">
              J-11A:{" "}
              {Array.isArray((fourYear.verdicts as Record<string, unknown> | undefined)?.decision_j11a)
                ? ((fourYear.verdicts as Record<string, unknown>).decision_j11a as string[]).join(" · ")
                : "—"}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {summary ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resumen (no predictivo)</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>Fechas analizadas: {String(summary.dates_analyzed ?? "—")}</div>
            <div>Casos con fuerte: {String((metrics.pop as { cases_with_fuerte?: number }).cases_with_fuerte ?? "—")}</div>
            <div>
              Hit next-day: {String(nd.hits ?? "—")}/{String(nd.denominator ?? "—")} (
              {String(nd.hit_rate ?? "—")})
            </div>
            <div>Lift vs random-k: {String(lift ?? "—")}</div>
            <div>Veredicto lógica: {String(summary.logic_verdict ?? "—")}</div>
            <div>Gate J-11A: {String(summary.j11a_gate ?? "—")}</div>
            <div>Muestra: {String((summary.sample_case_ids as unknown[])?.length ?? cases.length)}</div>
            <div>FEATURED_SEVEN: {String(summary.featured_seven ?? "—")}</div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Casos (≥10)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {cases.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin casos. Ejecute la auditoría.</p>
          ) : (
            <ul className="divide-y rounded-md border">
              {cases.map((c) => (
                <li key={String(c.id)}>
                  <button
                    type="button"
                    className="flex w-full items-start justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-muted/50"
                    onClick={() => setSelected(c)}
                  >
                    <span>
                      <span className="font-medium">{String(c.id)}</span>{" "}
                      <span className="text-muted-foreground">{String(c.date)}</span>{" "}
                      <span>{String(c.label ?? "")}</span>
                    </span>
                    <span className="shrink-0 text-xs">{String(c.verdict)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {selected ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Detalle {String(selected.id)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>{String(selected.explanation ?? "")}</p>
            <pre className="max-h-[420px] overflow-auto rounded-md bg-muted p-3 text-xs">
              {JSON.stringify(selected, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
